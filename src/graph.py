"""Ada'nın LangGraph ile kurulmuş agent grafı.

Akış:
    START -> agent
    agent -> (araç çağrısı yok)          -> END
    agent -> (kayıt oluşturan araç var)  -> human_approval
    agent -> (sadece okuma araçları)     -> tools
    human_approval -> (onay) -> tools
    human_approval -> (red)  -> agent   (iptal bilgisiyle)
    tools -> agent

Aşama 3'teki elle yazılmış döngü (src/agent.py) ile aynı işi yapar; farkı,
onay adımının prompt'a değil koda bağlı olması ve durumun (state) her adımda
checkpointer tarafından kaydedilmesidir.
"""
from typing import Literal

from langchain_core.messages import SystemMessage, ToolMessage, trim_messages
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode
from langgraph.types import Command, interrupt

from src.database import get_employee
from src.llm import get_llm
from src.prompts import load_prompt
from src.tools import SENSITIVE_TOOLS, describe_action, make_tools

# LLM'e gönderilecek en fazla mesaj sayısı (maliyet kontrolü)
MAX_CONTEXT_MESSAGES = 30


def build_graph(employee_id: str, checkpointer=None):
    employee = get_employee(employee_id)
    tools = make_tools(employee_id)
    llm = get_llm(temperature=0).bind_tools(tools)
    system = SystemMessage(content=load_prompt(
        "system_prompt", employee_name=employee["name"], employee_id=employee_id
    ))

    # ---------- Node 1: agent ----------
    def agent(state: MessagesState):
        # Son mesajları al; kesimi her zaman bir kullanıcı mesajından başlat ki
        # araç çağrısı ile sonucu birbirinden ayrılmasın.
        recent = trim_messages(
            state["messages"],
            max_tokens=MAX_CONTEXT_MESSAGES,
            token_counter=len,  # "token" yerine mesaj sayısı say
            strategy="last",
            start_on="human",
        )
        return {"messages": [llm.invoke([system] + recent)]}

    # ---------- Yönlendirme: agent'tan sonra nereye? ----------
    def route_after_agent(state: MessagesState) -> Literal["human_approval", "tools", "__end__"]:
        last = state["messages"][-1]
        if not last.tool_calls:
            return END
        if any(call["name"] in SENSITIVE_TOOLS for call in last.tool_calls):
            return "human_approval"
        return "tools"

    # ---------- Node 2: human_approval ----------
    def human_approval(state: MessagesState) -> Command[Literal["tools", "agent"]]:
        last = state["messages"][-1]
        actions = [
            describe_action(call["name"], call["args"])
            for call in last.tool_calls
            if call["name"] in SENSITIVE_TOOLS
        ]
        # interrupt: graf burada DURUR. Kullanıcının cevabı gelince
        # graf bu satırdan devam eder ve decision o cevabı alır.
        decision = interrupt({"actions": actions})

        if decision == "onay":
            return Command(goto="tools")

        # Reddedildi: her araç çağrısına "iptal" sonucu verip agent'a dön
        cancelled = [
            ToolMessage(content="İŞLEM İPTAL: Kullanıcı bu işlemi onaylamadı.", tool_call_id=call["id"])
            for call in last.tool_calls
        ]
        return Command(goto="agent", update={"messages": cancelled})

    # ---------- Grafı kur ----------
    builder = StateGraph(MessagesState)
    builder.add_node("agent", agent)
    builder.add_node("human_approval", human_approval)
    builder.add_node("tools", ToolNode(tools))  # LangGraph'ın hazır araç çalıştırıcısı

    builder.add_edge(START, "agent")
    builder.add_conditional_edges("agent", route_after_agent)
    builder.add_edge("tools", "agent")

    return builder.compile(checkpointer=checkpointer or InMemorySaver())