"""Tek bir soru sor; hem bulunan parçaları hem de cevabı gör.

Çalıştırmak için:  python -m scripts.ask "Masraf fişlerini ne zamana kadar teslim etmeliyim?"
"""
import sys

from src.rag import answer, retrieve, source_label


def main():
    if len(sys.argv) < 2:
        print('Kullanım: python -m scripts.ask "sorunuz"')
        return
    question = sys.argv[1]

    print(f"Soru: {question}\n")
    print("=== 1. ADIM: Bulunan parçalar (retrieval) ===")
    for doc, score in retrieve(question):
        print(f"  mesafe={score:.3f}  {source_label(doc)}")

    print("\n=== 2. ADIM: Ada'nın cevabı (generation) ===")
    text, _ = answer(question)
    print(text)


if __name__ == "__main__":
    main()