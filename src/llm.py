"""Tek bir fonksiyonla OpenAI, Anthropic veya Gemini modeline erişim sağlar.

Projenin geri kalanı sadece get_llm() fonksiyonunu kullanır; böylece
sağlayıcı değiştirmek için kodun hiçbir yerine dokunmak gerekmez.
"""
import os

from langchain.chat_models import init_chat_model

from src.config import API_KEY_NAMES, LLM_PROVIDER, MODELS

# LangChain'in sağlayıcı adları bizimkilerden biraz farklı
LANGCHAIN_PROVIDER = {
    "openai": "openai",
    "anthropic": "anthropic",
    "gemini": "google_genai",
}


def get_llm(provider: str | None = None, temperature: float = 0.2):
    """Seçilen sağlayıcı için hazır bir sohbet modeli döndürür."""
    provider = (provider or LLM_PROVIDER).lower()

    if provider not in LANGCHAIN_PROVIDER:
        raise ValueError(
            f"Bilinmeyen sağlayıcı: {provider}. Seçenekler: {list(LANGCHAIN_PROVIDER)}"
        )

    key_name = API_KEY_NAMES[provider]
    if not os.getenv(key_name):
        raise RuntimeError(f"{key_name} bulunamadı. .env dosyanı kontrol et.")

    model = MODELS[provider]
    if not model:
        raise RuntimeError(
            f"{provider} için model adı yok. .env dosyasına {provider.upper()}_MODEL ekle."
        )

    return init_chat_model(
        model,
        model_provider=LANGCHAIN_PROVIDER[provider],
        temperature=temperature,
    )
