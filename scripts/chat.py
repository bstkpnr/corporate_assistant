"""Terminalde Ada ile sohbet.

Çalıştırmak için:  python -m scripts.chat
Komutlar: /sifirla (geçmişi temizler), /cikis (programdan çıkar)
"""
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from src.llm import get_llm
from src.prompts import ASSISTANT_NAME, load_prompt

# Her mesajda tüm geçmiş modele tekrar gönderilir. Geçmiş uzadıkça maliyet
# artar, bu yüzden sadece son N mesajı tutuyoruz.
MAX_HISTORY = 20


def main():
    llm = get_llm(temperature=0.3)
    system = SystemMessage(content=load_prompt("system_prompt"))
    history = []

    print(f"{ASSISTANT_NAME} hazır. /sifirla ile geçmişi temizle, /cikis ile çık.\n")

    while True:
        try:
            user_input = input("Sen: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nGörüşmek üzere!")
            break

        if not user_input:
            continue
        if user_input == "/cikis":
            print("Görüşmek üzere!")
            break
        if user_input == "/sifirla":
            history = []
            print("(Sohbet geçmişi temizlendi)\n")
            continue

        history.append(HumanMessage(content=user_input))
        history = history[-MAX_HISTORY:]

        print(f"{ASSISTANT_NAME}: ", end="", flush=True)
        reply = ""
        try:
            # stream: cevabı kelime kelime yazdırır, ChatGPT'deki gibi
            for chunk in llm.stream([system] + history):
                print(chunk.text, end="", flush=True)
                reply += chunk.text
        except Exception as e:
            print(f"\n[Hata] {e}")
            history.pop()  # cevaplanamayan mesajı geçmişten çıkar
            continue

        print("\n")
        history.append(AIMessage(content=reply))


if __name__ == "__main__":
    main()