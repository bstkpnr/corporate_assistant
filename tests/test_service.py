"""Ortak graf çalıştırma mantığının (src/service.py) testleri. Sahte LLM kullanılır."""
import uuid
from datetime import timedelta

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.types import Command

from src.graph import build_graph
from src.service import make_config, run_graph
from tests.conftest import leave_responder, next_monday, tool_call


def test_make_config():
    config = make_config("abc")
    assert config["configurable"]["thread_id"] == "abc"
    assert config["recursion_limit"] == 15


def test_completed_turn_returns_reply(db, fake_llm):
    fake_llm(lambda messages: AIMessage(content="Merhaba!"))
    graph, config = build_graph("E001"), make_config(str(uuid.uuid4()))

    result = run_graph(graph, {"messages": [HumanMessage("selam")]}, config)

    assert result == {"status": "completed", "reply": "Merhaba!", "tool_calls": []}


def test_approval_required_then_resume(db, fake_llm):
    start = next_monday(30)
    fake_llm(leave_responder(start, start + timedelta(days=1)))
    graph, config = build_graph("E001"), make_config(str(uuid.uuid4()))

    result = run_graph(graph, {"messages": [HumanMessage("izin istiyorum")]}, config)
    assert result["status"] == "approval_required"
    assert result["pending_actions"]
    assert result["tool_calls"] == ["create_leave_request"]

    result = run_graph(graph, Command(resume="onay"), config)
    assert result["status"] == "completed"
    assert "BAŞARILI" in result["reply"]


def test_callbacks_receive_tool_calls_and_results(db, fake_llm):
    def respond(messages):
        if isinstance(messages[-1], HumanMessage):
            return tool_call("get_leave_balance", {})
        return AIMessage(content="tamam")

    fake_llm(respond)
    graph, config = build_graph("E001"), make_config(str(uuid.uuid4()))
    calls, results = [], []

    run_graph(graph, {"messages": [HumanMessage("bakiye")]}, config,
              on_tool_call=calls.append, on_tool_result=results.append)

    assert [c["name"] for c in calls] == ["get_leave_balance"]
    assert len(results) == 1 and "14 gün" in results[0].text
