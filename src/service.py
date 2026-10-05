"""Grafı çalıştırma mantığı: terminal sohbeti (scripts/chat.py) ve API (src/api.py)
aynı fonksiyonları kullanır.
"""
from typing import Callable

# Sonsuz döngüye karşı bir konuşma turunda izin verilen en fazla adım sayısı
RECURSION_LIMIT = 15


def make_config(thread_id: str) -> dict:
    """thread_id: konuşmanın kimliği. Checkpointer geçmişi bu kimlikle saklar."""
    return {"configurable": {"thread_id": thread_id}, "recursion_limit": RECURSION_LIMIT}


def run_graph(
    graph,
    graph_input,
    config: dict,
    on_tool_call: Callable[[dict], None] | None = None,
    on_tool_result: Callable[[object], None] | None = None,
) -> dict:
    """Grafı çalıştırır; onay için durursa bekleyen işlemleri döndürür.

    on_tool_call / on_tool_result verilirse her araç çağrısında ve araç
    sonucunda, graf çalışırken anında çağrılır (terminalde canlı göstermek için).
    """
    tool_calls, pending = [], None
    for update in graph.stream(graph_input, config, stream_mode="updates"):
        for node, data in update.items():
            if node == "__interrupt__":
                pending = data[0].value["actions"]
            elif node == "agent":
                for call in data["messages"][-1].tool_calls:
                    tool_calls.append(call["name"])
                    if on_tool_call:
                        on_tool_call(call)
            elif node == "tools" and on_tool_result:
                for msg in data["messages"]:
                    on_tool_result(msg)

    if pending:
        return {"status": "approval_required", "pending_actions": pending, "tool_calls": tool_calls}
    final = graph.get_state(config).values["messages"][-1]
    return {"status": "completed", "reply": final.text, "tool_calls": tool_calls}
