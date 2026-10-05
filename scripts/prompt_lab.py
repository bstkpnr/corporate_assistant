"""Prompt deneyleri laboratuvarı.

Çalıştırmak için:  python -m scripts.prompt_lab
Deney 1: System prompt'un modelin davranışını nasıl değiştirdiğini gösterir.
Deney 2: Few-shot + structured output ile niyet sınıflandırması yapar.
"""
from langchain_core.messages import HumanMessage, SystemMessage

from src.intent import classify_intent
from src.llm import get_llm
from src.prompts import load_prompt

SORU = "Yıllık izin hakkım kaç gün ve kullanmadığım izinleri seneye devredebilir miyim?"

TEST_MESAJLARI = [
    "Seyahat masraflarımı nasıl beyan ederim?",
    "Yarın için izin talebi oluşturur musun?",
    "Teşekkürler Ada, çok yardımcı oldun!",
    "Hafta sonu için güzel bir film önerir misin?",
    "VPN şifremi unuttum, ne yapmam lazım?",
    "Yarın izin almak istiyorum, kurallar neydi?",
]


def deney_1():
    print("=" * 70)
    print("DENEY 1: System prompt olmadan ve olan aynı soru")
    print("=" * 70)
    print(f"Soru: {SORU}\n")

    llm = get_llm(temperature=0)

    cevap = llm.invoke([HumanMessage(content=SORU)])
    print("--- System prompt OLMADAN ---")
    print(cevap.text, "\n")

    cevap = llm.invoke([
        SystemMessage(content=load_prompt("system_prompt")),
        HumanMessage(content=SORU),
    ])
    print("--- System prompt İLE ---")
    print(cevap.text, "\n")


def deney_2():
    print("=" * 70)
    print("DENEY 2: Niyet sınıflandırma (few-shot + structured output)")
    print("=" * 70)
    for mesaj in TEST_MESAJLARI:
        sonuc = classify_intent(mesaj)
        print(f"\nMesaj   : {mesaj}")
        print(f"Kategori: {sonuc.kategori}")
        print(f"Gerekçe : {sonuc.gerekce}")


if __name__ == "__main__":
    deney_1()
    deney_2()