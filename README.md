# Kurumsal Çalışan Asistanı (AI Agent)

Hayali bir şirketin çalışanlarına yardım eden, Türkçe konuşan bir yapay zekâ asistanı.
Şirket politikalarını **RAG** ile cevaplar, **tool calling** ile işlem yapar
(izin bakiyesi sorgulama, destek talebi açma) ve çok adımlı görevleri bir
**agent workflow** ile planlar.

OpenAI, Anthropic ve Google Gemini modelleriyle çalışır; sağlayıcı tek bir
ayarla değiştirilebilir.

> Proje geliştirme aşamasındadır.

## Yol haritası

- [x] Aşama 0: Kurulum ve çoklu LLM sağlayıcı desteği
- [ ] Aşama 1: Sohbet ve prompt engineering
- [ ] Aşama 2: Şirket belgeleri üzerinde RAG
- [ ] Aşama 3: Tool / function calling
- [ ] Aşama 4: LangGraph ile agent workflow
- [ ] Aşama 5: FastAPI, loglama ve Docker
- [ ] Aşama 6: Testler, değerlendirme ve CI
- [ ] Aşama 7: Arayüz ve demo

## Kurulum

```bash
git clone https://github.com/KULLANICI_ADIN/kurumsal-asistan.git
cd kurumsal-asistan
python -m venv .venv
# Windows: .venv\Scripts\activate    Mac/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # sonra .env içine API anahtarını yaz
python -m scripts.test_connection
```

## Teknolojiler

Python, LangChain, (yakında) LangGraph, ChromaDB, FastAPI, Docker
