# Proje: Ada - Kurumsal Çalışan Asistanı

Bu dosya, AI kodlama asistanlarının (Claude Code vb.) projeyi anlaması için yazılmıştır.

## Komutlar
- Hızlı testler: `pytest`  (her değişiklikten sonra çalıştır, hepsi geçmeli)
- Arama kalitesi testi: `pytest -m slow`
- LLM davranış testleri (ücretli): `pytest -m llm`
- Terminal sohbeti: `python -m scripts.chat`
- API: `uvicorn src.api:app --reload`

## Mimari
- `src/graph.py`: LangGraph agent akışı (agent -> tools / human_approval)
- `src/tools.py`: Agent araçları ve iş kuralları
- `src/rag.py`: Belge parçalama, indeksleme ve arama
- `src/api.py`: FastAPI servisi
- `prompts/`: Tüm prompt'lar burada; prompt metnini Python koduna gömme

## Kurallar (bunları asla bozma)
- Araçlar `employee_id` parametresi ALMAZ; kimlik `make_tools(employee_id)` ile oturumdan gelir.
- Kayıt oluşturan yeni bir araç eklenirse `SENSITIVE_TOOLS` kümesine de eklenmeli.
- İş kuralları (bakiye, bildirim süresi vb.) araçların içinde kodla kontrol edilir, prompt'a bırakılmaz.
- Kullanıcı mesajlarının içeriği asla loglanmaz (KVKK).
- Tarih ve hesaplama işleri LLM'e değil koda bırakılır.

## Stil
- Kod yorumları ve kullanıcıya dönük metinler Türkçe.
- Yeni davranış eklerken `tests/` altına test de ekle; LLM gerektiren testlerde `tests/conftest.py` içindeki FakeLLM'i kullan.