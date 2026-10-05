"""Terminalde Ada ile sohbet (araç kullanan agent).

Çalıştırmak için:            python -m scripts.chat
Başka bir çalışan olarak:    python -m scripts.chat --user E004
Komutlar: /sifirla (geçmişi temizler), /debug (araç sonuçlarını göster/gizle), /cikis
"""
import argparse

from langchain_core.messages import HumanMessage, SystemMessage

from src.agent import run_turn
from src.database import get_employee
from src.llm import get_llm
from src.prompts import ASSISTANT_NAME, load_prompt
from src.rag import retrieve
from src.tools import make_tools

# Geçmiş mesaj sayısıyla değil "tur" sayısıyla sınırlanır. Bir turda araç
# çağrısı ve sonucu birlikte bulunmalı; ortadan kesilirse API hata verir.
MAX_TURNS = 8


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--user", default="E001", help="Oturum açan çalışanın ID'si")
    args = parser.parse_args()

    employee = get_employee(args.user)
    if employee is None:
        print(f"{args.user} adında bir çalışan yok. Önce: python -m scripts.init_db")
        return

    llm = get_llm(temperature=0)
    tools = make_tools(employee["id"])
    system = SystemMessage(content=load_prompt(
        "system_prompt", employee_name=employee["name"], employee_id=employee["id"]
    ))
    turns: list[list] = []
    debug = False

    print("Belgeler yükleniyor...")
    retrieve("ısınma")  # embedding modelini önceden yükle
    print(f"{ASSISTANT_NAME} hazır. Oturum: {employee['name']} ({employee['id']})")
    print("Komutlar: /sifirla, /debug, /cikis\n")

    def show_tool_call(name: str, call_args: dict, result: str):
        args_text = ", ".join(f"{k}={v!r}" for k, v in call_args.items())
        print(f"  [araç] {name}({args_text})")
        if debug:
            for line in result.splitlines()[:12]:
                print(f"         | {line}")

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
            turns = []
            print("(Sohbet geçmişi temizlendi)\n")
            continue
        if user_input == "/debug":
            debug = not debug
            print(f"(Debug modu {'açık' if debug else 'kapalı'})\n")
            continue

        user_message = HumanMessage(content=user_input)
        history = [m for turn in turns[-MAX_TURNS:] for m in turn]

        try:
            new_messages = run_turn(llm, tools, [system] + history + [user_message], show_tool_call)
        except Exception as e:
            print(f"[Hata] {e}\n")
            continue

        print(f"{ASSISTANT_NAME}: {new_messages[-1].text}\n")
        turns.append([user_message] + new_messages)


if __name__ == "__main__":
    main()