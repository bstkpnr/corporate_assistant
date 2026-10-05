"""Bastet'in REST API'si (FastAPI).

Çalıştırmak için:  uvicorn src.api:app --reload
Tarayıcıda test:   http://127.0.0.1:8000/docs

Akış:
  POST /chat                      -> Bastet'e mesaj gönder
     cevap "completed" ise          -> reply alanında Bastet'in cevabı var
     cevap "approval_required" ise  -> pending_actions alanında onay bekleyen işlemler var
  POST /chat/{thread_id}/approval -> bekleyen işlemi onayla veya reddet
"""
import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.errors import GraphRecursionError
from langgraph.types import Command
from pydantic import BaseModel, Field

from src.auth import get_current_employee
from src.graph import build_graph
from src.logging_config import setup_logging
from src.rag import retrieve
from src.service import make_config, run_graph

from pathlib import Path

from fastapi.responses import FileResponse

from src.dashboard import get_dashboard

setup_logging()
logger = logging.getLogger("bastet.api")


# ---------- İstek ve cevap modelleri ----------

class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000, examples=["Kaç gün iznim kaldı?"])
    thread_id: str | None = Field(default=None, description="Boş bırakılırsa yeni konuşma başlar")


class ApprovalRequest(BaseModel):
    approved: bool


class ChatResponse(BaseModel):
    thread_id: str
    status: str = Field(description="completed veya approval_required")
    reply: str | None = None
    pending_actions: list[str] = []
    tool_calls: list[str] = []


# ---------- Uygulama durumu ----------
# Tüm konuşmalar aynı checkpointer'da tutulur. InMemorySaver sunucu yeniden
# başlayınca sıfırlanır; üretimde PostgresSaver gibi kalıcı bir çözüm kullanılır.
checkpointer = InMemorySaver()
graphs: dict[str, object] = {}       # çalışan başına bir graf (araçlar kimliğe bağlı)
thread_owners: dict[str, str] = {}   # thread_id -> sahibi olan çalışan


def get_graph(employee_id: str):
    if employee_id not in graphs:
        graphs[employee_id] = build_graph(employee_id, checkpointer=checkpointer)
    return graphs[employee_id]


@asynccontextmanager
async def lifespan(app: FastAPI):
    retrieve("ısınma")  # embedding modelini ve vektör veritabanını önceden yükle
    logger.info("Bastet API hazır")
    yield


app = FastAPI(
    title="Bastet - Kurumsal Çalışan Asistanı API",
    description="Mitogent Teknoloji çalışanları için RAG ve tool calling destekli AI asistanı.",
    version="0.5.0",
    lifespan=lifespan,
)


# ---------- Her isteği loglayan ara katman ----------

@app.middleware("http")
async def log_requests(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    start = time.perf_counter()
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    logger.info("request", extra={
        "request_id": request_id,
        "method": request.method,
        "path": request.url.path,
        "status_code": response.status_code,
        "duration_ms": round((time.perf_counter() - start) * 1000),
    })
    return response


# ---------- Yardımcılar ----------

def execute(employee: dict, thread_id: str, graph_input) -> ChatResponse:
    """Grafı hata yönetimi ve loglamayla birlikte çalıştırır."""
    graph = get_graph(employee["id"])
    config = make_config(thread_id)
    try:
        result = run_graph(graph, graph_input, config)
    except GraphRecursionError:
        raise HTTPException(422, "İstek çok fazla adım gerektirdi; lütfen daha küçük adımlara bölün.")
    except Exception:
        logger.exception("graph_error", extra={"employee_id": employee["id"], "thread_id": thread_id})
        raise HTTPException(503, "Asistan şu an yanıt veremiyor, lütfen biraz sonra tekrar deneyin.")

    logger.info("chat_turn", extra={
        "employee_id": employee["id"],
        "thread_id": thread_id,
        "status": result["status"],
        "tool_calls": result["tool_calls"],
    })
    return ChatResponse(thread_id=thread_id, **result)


def check_thread(thread_id: str, employee: dict) -> None:
    """Konuşma bu çalışana mı ait? Değilse varlığını bile belli etme (404)."""
    if thread_owners.get(thread_id) != employee["id"]:
        raise HTTPException(404, "Konuşma bulunamadı.")


def has_pending_approval(employee: dict, thread_id: str) -> bool:
    state = get_graph(employee["id"]).get_state({"configurable": {"thread_id": thread_id}})
    return bool(state.interrupts)


# ---------- Endpoint'ler ----------

@app.get("/health", tags=["Sistem"])
def health():
    """Servisin ayakta olup olmadığını kontrol eder (load balancer, Docker vb. için)."""
    return {"status": "ok"}


@app.get("/me", tags=["Kullanıcı"])
def me(employee: dict = Depends(get_current_employee)):
    """Token'a göre oturum açmış çalışanı döndürür."""
    return {"id": employee["id"], "name": employee["name"], "title": employee["title"]}


@app.post("/chat", response_model=ChatResponse, tags=["Sohbet"])
def chat(request: ChatRequest, employee: dict = Depends(get_current_employee)):
    """Bastet'e mesaj gönderir. thread_id verilirse mevcut konuşmaya devam eder."""
    if request.thread_id is None:
        thread_id = str(uuid.uuid4())
        thread_owners[thread_id] = employee["id"]
    else:
        thread_id = request.thread_id
        check_thread(thread_id, employee)
        if has_pending_approval(employee, thread_id):
            raise HTTPException(409, "Bu konuşmada onay bekleyen bir işlem var. Önce onaylayın veya reddedin.")

    return execute(employee, thread_id, {"messages": [HumanMessage(content=request.message)]})


@app.post("/chat/{thread_id}/approval", response_model=ChatResponse, tags=["Sohbet"])
def approve(thread_id: str, request: ApprovalRequest, employee: dict = Depends(get_current_employee)):
    """Onay bekleyen işlemi onaylar (approved=true) veya reddeder (approved=false)."""
    check_thread(thread_id, employee)
    if not has_pending_approval(employee, thread_id):
        raise HTTPException(409, "Bu konuşmada onay bekleyen bir işlem yok.")

    decision = "onay" if request.approved else "red"
    return execute(employee, thread_id, Command(resume=decision))

    # ---------- Web arayüzü (Aşama 7) ----------
# Bu bloğu src/api.py dosyasının EN SONUNA ekle.


WEB_DIR = Path(__file__).resolve().parent.parent / "web"


@app.get("/me/dashboard", tags=["Kullanıcı"])
def dashboard(employee: dict = Depends(get_current_employee)):
    """Web arayüzünün sol paneli: profil, izin bakiyesi ve son talepler."""
    return get_dashboard(employee["id"])


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(WEB_DIR / "index.html")