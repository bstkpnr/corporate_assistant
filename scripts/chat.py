"""Terminalde Ada ile sohbet (LangGraph agent'ı).

Çalıştırmak için:            python -m scripts.chat
Başka bir çalışan olarak:    python -m scripts.chat --user E004
Komutlar: /sifirla (yeni konuşma), /debug (araç sonuçlarını göster/gizle), /cikis
"""
import argparse
import uuid

from langchain_core.messages import HumanMessage
from langgraph.errors import GraphRecursionError
from langgraph.types import Command

from src.database import get_employee
from src.graph import build_graph
from src.prompts import ASSISTANT_NAME
from src.rag import retrieve


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--user", default="E001", help="Oturum açan çalışanın ID'si")
    args = parser.parse_args()

    employee = get_employee(args.user)
    if employee is None:
        print(f"{args.user} adında bir çalışan yok. Önce: python -m scripts.init_db")
        return

    graph = build_graph(employee["id"])
    debug = False

    def new_config():
        # thread_id: konuşmanın kimliği. Checkpointer geçmişi bu kimlikle saklar.
        # recursion_limit: sonsuz döngüye karşı en fazla adım sayısı.
        return {"configurable": {"thread_id": str(uuid.uuid4())}, "recursion_limit": 15}

    config = new_config()

    def run(graph_input):
        """Grafı çalıştırır, adımları ekrana yazar. Graf onay için durursa
        interrupt bilgisini döndürür, durmazsa None döndürür."""
        for update in graph.stream(graph_input, config, stream_mode="updates"):
            for node, data in update.items():
                if node == "__interrupt__":
                    return data[0].value
                if node == "agent":
                    for call in data["messages"][-1].tool_calls:
                        args_text = ", ".join(f"{k}={v!r}" for k, v in call["args"].items())
                        print(f"  [araç] {call['name']}({args_text})")
                elif node == "tools" and debug:
                    for msg in data["messages"]:
                        for line in msg.text.splitlines()[:10]:
                            print(f"         | {line}")
        return None

    print("Belgeler yükleniyor...")
    retrieve("ısınma")
    print(f"{ASSISTANT_NAME} hazır. Oturum: {employee['name']} ({employee['id']})")
    print("Komutlar: /sifirla, /debug, /cikis\n")

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
            config = new_config()
            print("(Yeni konuşma başlatıldı)\n")
            continue
        if user_input == "/debug":
            debug = not debug
            print(f"(Debug modu {'açık' if debug else 'kapalı'})\n")
            continue

        try:
            pending = run({"messages": [HumanMessage(content=user_input)]})

            # Graf onay için durduysa: kullanıcıya sor, cevabıyla devam ettir
            while pending:
                print("\n  ONAY GEREKİYOR")
                for action in pending["actions"]:
                    print(f"  - {action}")
                answer = input("  Onaylıyor musunuz? (e/h): ").strip().lower()
                decision = "onay" if answer in ("e", "evet") else "red"
                pending = run(Command(resume=decision))
        except GraphRecursionError:
            print(f"{ASSISTANT_NAME}: Bu isteği tamamlamak için çok fazla adım gerekti, "
                  "lütfen daha küçük adımlarla tekrar dener misiniz?\n")
            continue
        except Exception as e:
            print(f"[Hata] {e}\n")
            continue

        final = graph.get_state(config).values["messages"][-1]
        print(f"\n{ASSISTANT_NAME}: {final.text}\n")


if __name__ == "__main__":
    main()