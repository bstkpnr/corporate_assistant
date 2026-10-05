"""Tool calling döngüsü (elle yazılmış basit bir agent).

Döngü şöyle işler:
  1. LLM'e mesajları ve araç listesini gönder.
  2. LLM araç çağırmak isterse (tool_calls), araçları BİZ çalıştırırız.
  3. Sonuçları ToolMessage olarak mesajlara ekleyip tekrar LLM'e göndeririz.
  4. LLM araç çağırmadan düz cevap verene kadar tekrarla.

Aşama 4'te bu döngünün yerini LangGraph alacak.
"""
from typing import Callable

from langchain_core.messages import AIMessage, BaseMessage, ToolMessage

# Sonsuz döngüye karşı emniyet kemeri: hem hataları hem de maliyeti sınırlar
MAX_STEPS = 6


def run_turn(
    llm,
    tools: list,
    messages: list[BaseMessage],
    on_tool_call: Callable[[str, dict, str], None] | None = None,
) -> list[BaseMessage]:
    """Bir kullanıcı mesajını işler; bu turda üretilen yeni mesajları döndürür.
    Son mesaj her zaman kullanıcıya gösterilecek cevaptır."""
    llm_with_tools = llm.bind_tools(tools)
    tools_by_name = {t.name: t for t in tools}
    new_messages: list[BaseMessage] = []

    for _ in range(MAX_STEPS):
        ai_message = llm_with_tools.invoke(messages + new_messages)
        new_messages.append(ai_message)

        if not ai_message.tool_calls:  # araç istemiyorsa cevap hazır demektir
            return new_messages

        for call in ai_message.tool_calls:
            tool = tools_by_name.get(call["name"])
            if tool is None:
                result = f"HATA: '{call['name']}' adında bir araç yok."
            else:
                try:
                    result = str(tool.invoke(call["args"]))
                except Exception as e:  # hatalı parametre vb. LLM'e geri bildir
                    result = f"HATA: Araç çalıştırılamadı: {e}"
            if on_tool_call:
                on_tool_call(call["name"], call["args"], result)
            new_messages.append(ToolMessage(content=result, tool_call_id=call["id"]))

    new_messages.append(AIMessage(
        content="Bu isteği tamamlamak için çok fazla adım gerekti. "
                "Lütfen isteğinizi daha küçük adımlara bölerek tekrar dener misiniz?"
    ))
    return new_messages