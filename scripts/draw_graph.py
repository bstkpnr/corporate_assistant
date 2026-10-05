"""Agent grafının Mermaid diyagramını üretir (README'ye eklemek için).

Çalıştırmak için:  python -m scripts.draw_graph
"""
from src.graph import build_graph


def main():
    graph = build_graph("E001")
    print("```mermaid")
    print(graph.get_graph().draw_mermaid())
    print("```")


if __name__ == "__main__":
    main()