"""Aşama 0 testi: .env'de anahtarı olan her sağlayıcıya kısa bir mesaj gönderir.

Çalıştırmak için proje klasöründe:  python -m scripts.test_connection
"""
import os

from src.config import API_KEY_NAMES
from src.llm import get_llm


def main():
    tested = 0
    for provider, key_name in API_KEY_NAMES.items():
        if not os.getenv(key_name):
            print(f"[{provider}] anahtar yok, atlanıyor.")
            continue

        tested += 1
        try:
            llm = get_llm(provider)
            reply = llm.invoke("Tek cümleyle kendini Türkçe tanıt.")
            print(f"[{provider}] OK -> {reply.content}")
        except Exception as e:
            print(f"[{provider}] HATA -> {e}")

    if tested == 0:
        print("Hiç API anahtarı bulunamadı. .env.example dosyasını .env olarak kopyalayıp anahtarını ekle.")


if __name__ == "__main__":
    main()
