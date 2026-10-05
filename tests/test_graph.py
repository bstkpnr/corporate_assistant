"""Agent grafının testleri: onay akışı ve yönlendirme. Sahte LLM kullanılır."""
import uuid
from datetime import timedelta

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.types import Command

from src.database import get_connection
from src.graph import build_graph
from tests.conftest import leave_responder, next_monday, tool_call


def new_config():
    return {"configurable": {"thread_id": str(uuid.uuid4())}, "recursion_limit": 15}


def leave_request_count() -> int:
    with get_connection() as conn:
        return conn.execute("SELECT COUNT(*) FROM leave_requests").fetchone()[0]


def test_sensitive_tool_waits_for_approval(db, fake_llm):
    start = next_monday(30)
    fake_llm(leave_responder(start, start + timedelta(days=1)))
    graph, config = build_graph("E001"), new_config()
    before = leave_request_count()

    graph.invoke({"messages": [HumanMessage("izin istiyorum")]}, config)

    state = graph.get_state(config)
    assert state.interrupts, "Graf onay için durmalıydı"
    assert leave_request_count() == before, "Onay olmadan kayıt oluşmamalı"


def test_approval_creates_request(db, fake_llm):
    start = next_monday(30)
    fake_llm(leave_responder(start, start + timedelta(days=1)))
    graph, config = build_graph("E001"), new_config()
    before = leave_request_count()

    graph.invoke({"messages": [HumanMessage("izin istiyorum")]}, config)
    graph.invoke(Command(resume="onay"), config)

    assert leave_request_count() == before + 1
    assert "BAŞARILI" in graph.get_state(config).values["messages"][-1].text


def test_rejection_creates_nothing(db, fake_llm):
    start = next_monday(30)
    fake_llm(leave_responder(start, start + timedelta(days=1)))
    graph, config = build_graph("E001"), new_config()
    before = leave_request_count()

    graph.invoke({"messages": [HumanMessage("izin istiyorum")]}, config)
    graph.invoke(Command(resume="red"), config)

    assert leave_request_count() == before
    messages = graph.get_state(config).values["messages"]
    assert any(isinstance(m, ToolMessage) and "İŞLEM İPTAL" in m.text for m in messages)


def test_read_only_tool_runs_without_approval(db, fake_llm):
    def respond(messages):
        if isinstance(messages[-1], HumanMessage):
            return tool_call("get_leave_balance", {})
        return AIMessage(content=f"Bakiye: {messages[-1].content}")

    fake_llm(respond)
    graph, config = build_graph("E001"), new_config()
    graph.invoke({"messages": [HumanMessage("kaç gün iznim var")]}, config)

    state = graph.get_state(config)
    assert not state.interrupts
    assert "14 gün" in state.values["messages"][-1].text


def test_conversation_memory_is_per_thread(db, fake_llm):
    fake_llm(lambda messages: AIMessage(content=f"{len(messages)} mesaj gördüm"))
    graph = build_graph("E001")
    first, second = new_config(), new_config()

    graph.invoke({"messages": [HumanMessage("bir")]}, first)
    graph.invoke({"messages": [HumanMessage("iki")]}, first)
    graph.invoke({"messages": [HumanMessage("üç")]}, second)

    assert len(graph.get_state(first).values["messages"]) == 4
    assert len(graph.get_state(second).values["messages"]) == 2