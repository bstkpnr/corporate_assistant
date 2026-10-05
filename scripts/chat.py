"""Terminalde Bastet ile sohbet (LangGraph agent'ı).

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
from src.service import make_config, run_graph


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
        return make_config(str(uuid.uuid4()))

    config = new_config()

    def print_tool_call(call):
        args_text = ", ".join(f"{k}={v!r}" for k, v in call["args"].items())
        print(f"  [araç] {call['name']}({args_text})")

    def print_tool_result(msg):
        if debug:
            for line in msg.text.splitlines()[:10]:
                print(f"         | {line}")

    def run(graph_input):
        """Grafı çalıştırır, adımları ekrana yazar ve sonucu döndürür."""
        return run_graph(graph, graph_input, config,
                         on_tool_call=print_tool_call, on_tool_result=print_tool_result)

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
            result = run({"messages": [HumanMessage(content=user_input)]})

            # Graf onay için durduysa: kullanıcıya sor, cevabıyla devam ettir
            while result["status"] == "approval_required":
                print("\n  ONAY GEREKİYOR")
                for action in result["pending_actions"]:
                    print(f"  - {action}")
                answer = input("  Onaylıyor musunuz? (e/h): ").strip().lower()
                decision = "onay" if answer in ("e", "evet") else "red"
                result = run(Command(resume=decision))
        except GraphRecursionError:
            print(f"{ASSISTANT_NAME}: Bu isteği tamamlamak için çok fazla adım gerekti, "
                  "lütfen daha küçük adımlarla tekrar dener misiniz?\n")
            continue
        except Exception as e:
            print(f"[Hata] {e}\n")
            continue

        print(f"\n{ASSISTANT_NAME}: {result['reply']}\n")


if __name__ == "__main__":
    main()