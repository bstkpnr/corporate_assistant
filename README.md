# Kurumsal Çalışan Asistanı (AI Agent)

Hayali bir şirketin çalışanlarına yardım eden, Türkçe konuşan bir yapay zekâ asistanı.
Şirket politikalarını **RAG** ile cevaplar, **tool calling** ile işlem yapar
(izin bakiyesi sorgulama, destek talebi açma) ve çok adımlı görevleri bir
**agent workflow** ile planlar.

OpenAI, Anthropic ve Google Gemini modelleriyle çalışır; sağlayıcı tek bir
ayarla değiştirilebilir.



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

## RAG Değerlendirmesi

12 test sorusunda doğru belge bölümünün ilk 3 sonuç içinde bulunma oranı:

| Embedding modeli | Parça boyutu | İsabet |
|---|---|---|
| multilingual-e5-small | 200 | %92 |
| multilingual-e5-small | 800 | %83 |
| multilingual-e5-small | 1500 | %83 |
| multilingual-e5-base | 400 | %92 |
| **multilingual-e5-base** | **800** | **%92** (seçilen) |

**Bulgular**
- Belgeler önce başlıklara göre bölündüğü için 800 ve 1500 aynı parçaları üretti.
- Küçük modelde yüksek isabet için parçaları 200 karaktere indirmek gerekti; bu
  da içeriksiz başlık parçalarına ve bağlamı kopuk listelere yol açtı.
- Büyük model, bölümleri bütün tutarken aynı isabete ulaştı.
- Kaçan tek soru ("Udemy kursu...") belgede geçmeyen bir marka adı içeriyor;
  bu, embedding değil sorgu dönüştürme (query rewriting) ile çözülecek.