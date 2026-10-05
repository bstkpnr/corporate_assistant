"""Terminalde Ada ile sohbet (RAG destekli).

Çalıştırmak için:  python -m scripts.chat
Komutlar: /sifirla (geçmişi temizler), /debug (bulunan parçaları göster/gizle), /cikis
"""
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from src.llm import get_llm
from src.prompts import ASSISTANT_NAME, load_prompt
from src.rag import build_rag_message, retrieve, source_label

MAX_HISTORY = 20


def main():
    llm = get_llm(temperature=0.3)
    system = SystemMessage(content=load_prompt("system_prompt"))
    history = []
    debug = False

    print("Belgeler yükleniyor...")
    retrieve("ısınma")  # embedding modelini ve veritabanını önceden yükle
    print(f"{ASSISTANT_NAME} hazır. /sifirla, /debug, /cikis\n")

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
        if user_input == "/debug":
            debug = not debug
            print(f"(Debug modu {'açık' if debug else 'kapalı'})\n")
            continue

        # 1) Retrieval: soruyla ilgili belge parçalarını bul
        results = retrieve(user_input, k=4)
        docs = [doc for doc, _ in results]
        if debug:
            for doc, score in results:
                print(f"  [debug] mesafe={score:.3f}  {source_label(doc)}")

        # 2) Belge parçaları sadece BU turdaki mesaja eklenir. Geçmişe sadece
        #    sorunun kendisi kaydedilir; yoksa her turda eski belgeler de
        #    tekrar gönderilir ve maliyet hızla büyür.
        messages = [system] + history + [build_rag_message(user_input, docs)]

        print(f"{ASSISTANT_NAME}: ", end="", flush=True)
        reply = ""
        try:
            for chunk in llm.stream(messages):
                print(chunk.text, end="", flush=True)
                reply += chunk.text
        except Exception as e:
            print(f"\n[Hata] {e}")
            continue

        print("\n")
        history.append(HumanMessage(content=user_input))
        history.append(AIMessage(content=reply))
        history = history[-MAX_HISTORY:]


if __name__ == "__main__":
    main()