"""Kullanıcı mesajının niyetini (intent) sınıflandırır.

Burada structured output kullanıyoruz: model serbest metin yerine,
aşağıdaki Intent sınıfına uyan bir nesne döndürüyor. Aşama 4'te agent,
bu sınıflandırmaya bakarak hangi yolu izleyeceğine karar verecek.
"""
from typing import Literal

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from src.llm import get_llm
from src.prompts import load_prompt


class Intent(BaseModel):
    kategori: Literal["politika_sorusu", "islem_talebi", "sohbet", "kapsam_disi"] = Field(
        description="Mesajın ait olduğu kategori"
    )
    gerekce: str = Field(description="Bu kategorinin neden seçildiğine dair tek cümlelik açıklama")


def classify_intent(message: str, provider: str | None = None) -> Intent:
    # Sınıflandırmada tutarlılık istediğimiz için temperature=0
    llm = get_llm(provider, temperature=0).with_structured_output(Intent)
    return llm.invoke([
        SystemMessage(content=load_prompt("intent_classifier")),
        HumanMessage(content=message),
    ])