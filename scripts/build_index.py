"""Şirket belgelerini parçalayıp vektör veritabanına kaydeder.

Çalıştırmak için:           python -m scripts.build_index
Farklı parça boyutuyla:     python -m scripts.build_index --chunk-size 400 --overlap 50
"""
import argparse

from src.rag import build_index, source_label


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--chunk-size", type=int, default=800)
    parser.add_argument("--overlap", type=int, default=100)
    args = parser.parse_args()

    print("Belgeler indeksleniyor (ilk çalıştırmada embedding modeli indirilir)...")
    chunks = build_index(args.chunk_size, args.overlap)

    print(f"\n{len(chunks)} parça oluşturuldu ve kaydedildi.")
    print(f"Parça boyutu: {args.chunk_size}, örtüşme: {args.overlap}\n")
    print("Örnek parça:")
    print("-" * 60)
    print(f"Kaynak: {source_label(chunks[0])}")
    print(chunks[0].page_content[:400])
    print("-" * 60)


if __name__ == "__main__":
    main()