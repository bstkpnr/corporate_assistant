"""Testlerde ortak kullanılan yardımcılar (fixture'lar).

En önemli fikir: FakeLLM. Gerçek LLM yerine, ona verdiğimiz bir fonksiyona göre
cevap üreten sahte bir model kullanıyoruz. Böylece testler ücretsiz, internetsiz
ve her seferinde aynı sonucu veriyor.
"""
from datetime import date, timedelta

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

import src.database as database
import src.graph as graph_module


# ---------- Veritabanı ----------

@pytest.fixture
def db(tmp_path, monkeypatch):
    """Her test için geçici, temiz bir veritabanı. Gerçek data/mitogent.db'ye dokunmaz."""
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "test.db")
    database.init_db()
    return database.DB_PATH


# ---------- Sahte LLM ----------

class FakeLLM:
    """bind_tools ve invoke metotları olan, cevabını responder fonksiyonundan alan model."""

    def __init__(self, responder):
        self.responder = responder
        self.calls = 0

    def bind_tools(self, tools):
        return self

    def invoke(self, messages):
        self.calls += 1
        return self.responder(messages)


@pytest.fixture
def fake_llm(monkeypatch):
    """Grafın kullandığı LLM'i sahtesiyle değiştirir. Kullanım: fake_llm(responder)"""
    def install(responder):
        llm = FakeLLM(responder)
        monkeypatch.setattr(graph_module, "get_llm", lambda *a, **k: llm)
        monkeypatch.setattr(graph_module, "get_fallback_llm", lambda *a, **k: None)
        return llm
    return install


def tool_call(name: str, args: dict, call_id: str = "call_1") -> AIMessage:
    """Belirli bir aracı çağırmak isteyen bir LLM cevabı üretir."""
    return AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": call_id}])


# ---------- Tarih yardımcıları ----------

def next_monday(min_days_ahead: int) -> date:
    """Bugünden en az min_days_ahead gün sonraki ilk pazartesi."""
    d = date.today() + timedelta(days=min_days_ahead)
    while d.weekday() != 0:
        d += timedelta(days=1)
    return d


def leave_responder(start: date, end: date):
    """Mesajda 'izin' geçerse izin talebi aracını çağıran, araç sonucunu
    olduğu gibi kullanıcıya aktaran basit bir sahte LLM davranışı."""
    def respond(messages):
        last = messages[-1]
        if isinstance(last, HumanMessage) and "izin" in last.content.lower():
            return tool_call("create_leave_request", {
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
                "leave_type": "yillik",
            }, call_id=f"call_{len(messages)}")
        if isinstance(last, ToolMessage):
            return AIMessage(content=f"Sonuç: {last.content}")
        return AIMessage(content="Merhaba, size nasıl yardımcı olabilirim?")
    return respond