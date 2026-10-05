"""Proje ayarları: .env dosyasındaki değerleri okur."""
import os

from dotenv import load_dotenv

load_dotenv()

# Varsayılan sağlayıcı (.env içindeki LLM_PROVIDER)
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini").lower()

# Her sağlayıcı için kullanılacak model adı
MODELS = {
    "openai": os.getenv("OPENAI_MODEL"),
    "anthropic": os.getenv("ANTHROPIC_MODEL"),
    "gemini": os.getenv("GEMINI_MODEL"),
}

# Her sağlayıcının API anahtarını tutan ortam değişkeni
API_KEY_NAMES = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "gemini": "GOOGLE_API_KEY",
}
