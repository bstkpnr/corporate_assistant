# Ada: Kurumsal Çalışan Asistanı (AI Agent)

Hayali bir şirketin (Nova Teknoloji A.Ş.) çalışanlarına yardım eden, Türkçe konuşan bir yapay zekâ asistanı.

Ada şirket politikalarını **RAG** ile kaynak göstererek cevaplar, **tool calling** ile çalışan adına işlem yapar (izin bakiyesi sorgulama, izin talebi oluşturma, IT destek talebi açma) ve çok adımlı görevleri **LangGraph** ile kurulmuş bir agent akışında yürütür. Kayıt oluşturan her işlem, çalıştırılmadan önce kodla zorunlu kılınmış bir **kullanıcı onayından** geçer.

OpenAI, Anthropic ve Google Gemini ile çalışır; sağlayıcı tek bir ayarla değiştirilebilir.

## Örnek konuşma

```
Sen: Devreden iznimi ne zamana kadar kullanmam gerekiyor ve kaç gün devreden iznim var?
  [araç] search_company_policies(queries=['devreden izin son kullanma tarihi'])
  [araç] get_leave_balance()
Ada: Devreden izniniz 2 gündür ve bunu en geç 31 Mart tarihine kadar kullanmanız gerekir.
     Bu tarihe kadar kullanılmayan devreden izinler yanar.
     Kaynak: leave_policy.md > Yıllık İzin Devri

Sen: Gelecek ayın ilk pazartesi ve salı günü yıllık izin almak istiyorum.
  [araç] get_calendar(month='2026-11')
  [araç] create_leave_request(start_date='2026-11-02', end_date='2026-11-03', leave_type='yillik')

  ONAY GEREKİYOR
  - İzin talebi: Yıllık izin, 02.11.2026 Pazartesi - 03.11.2026 Salı (2 iş günü)
  Onaylıyor musunuz? (e/h): e

Ada: İzin talebiniz oluşturuldu ve onay için yöneticiniz Can Öztürk'e gönderildi.
```

## Özellikler

- **Agentic RAG:** Belge araması bir araçtır; ne zaman arama yapılacağına agent karar verir. Cevaplar kaynak belge ve bölümle birlikte verilir.
- **Multi-query retrieval:** Agent, kullanıcının sorusunu belgelerin diline çeviren 1-3 sorgu üretir; sonuçlar Reciprocal Rank Fusion ile birleştirilir.
- **Tool calling:** Profil, izin bakiyesi, izin talepleri, takvim ve IT destek araçları.
- **Human-in-the-loop:** Kayıt oluşturan araçlar LangGraph `interrupt` ile durdurulur; kullanıcı onaylamadan çalışmaz. Onay özeti LLM'den değil koddan üretilir.
- **Kodda yetkilendirme:** Araçlar çalışan kimliğini parametre olarak almaz, oturumdan alır. LLM başka bir çalışanın verisine erişemez.
- **Kodda iş kuralları:** İzin bakiyesi, en az 5 iş günü önceden bildirim gibi politikalar araçların içinde zorunlu kılınır.
- **Sağlayıcıdan bağımsız mimari:** OpenAI, Anthropic veya Gemini arasında `.env` üzerinden geçiş.
- **Sürümlenen prompt'lar:** Tüm prompt'lar `prompts/` klasöründe ayrı dosyalarda tutulur ve Git ile izlenir.

## Mimari

```mermaid
flowchart TD
    U([Kullanıcı mesajı]) --> A["agent<br/>LLM karar verir"]
    A -->|araç çağrısı yok| E([Cevap])
    A -->|okuma aracı| T["tools<br/>araçları çalıştırır"]
    A -->|kayıt oluşturan araç| H{"human_approval<br/>kullanıcı onayı"}
    H -->|onay| T
    H -->|red| A
    T --> A
```

| Bileşen | Teknoloji |
|---|---|
| Agent akışı | LangGraph (StateGraph, interrupt, checkpointer) |
| LLM | Anthropic Claude Haiku 4.5 (varsayılan), OpenAI, Gemini |
| Embedding | `intfloat/multilingual-e5-base` (yerel, ücretsiz) |
| Vektör veritabanı | ChromaDB |
| Çalışan verisi | SQLite |

## Proje yapısı

```
corporate_assistant/
├── data/policies/        # Şirket politika belgeleri (Markdown)
├── prompts/              # Sürümlenen prompt dosyaları
├── src/
│   ├── llm.py            # Sağlayıcıdan bağımsız LLM erişimi
│   ├── embeddings.py     # Yerel embedding modeli
│   ├── rag.py            # Parçalama, indeksleme, arama, multi-query
│   ├── tools.py          # Agent araçları ve iş kuralları
│   ├── graph.py          # LangGraph agent akışı
│   ├── database.py       # SQLite çalışan veritabanı
│   └── agent.py          # İlk sürüm: elle yazılmış tool calling döngüsü
└── scripts/
    ├── chat.py           # Terminal sohbet arayüzü
    ├── build_index.py    # Belgeleri indeksler
    ├── init_db.py        # Örnek veritabanını oluşturur
    ├── eval_retrieval.py # Arama kalitesini ölçer
    └── draw_graph.py     # Agent grafının diyagramını üretir
```

## Kurulum

Python 3.10 veya üzeri gerekir.

```bash
git clone https://github.com/KULLANICI_ADIN/corporate_assistant.git
cd corporate_assistant
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env               # .env içine en az bir API anahtarı yaz
python -m scripts.test_connection  # LLM bağlantısını test et

python -m scripts.build_index      # Belgeleri indeksle (ilk seferde embedding modeli indirilir)
python -m scripts.init_db          # Örnek çalışan veritabanını oluştur
```

## Kullanım

```bash
python -m scripts.chat               # Deniz Kaya (E001) olarak
python -m scripts.chat --user E004   # Farklı bir çalışan olarak
```

Sohbet içinde `/debug` araç sonuçlarını gösterir, `/sifirla` yeni konuşma başlatır.

| ID | Çalışan | Durum |
|---|---|---|
| E001 | Deniz Kaya | 3 yıllık kıdem, 14 gün kalan izin |
| E003 | Mert Çelik | 7 yıllık kıdem |
| E004 | Zeynep Arslan | 1 yılını doldurmamış, izin hakkı yok |
| E005 | Can Öztürk | Yönetici |

## RAG değerlendirmesi

12 test sorusunda doğru belge bölümünün ilk 3 sonuç içinde bulunma oranı. Ölçüm LLM kullanmaz, tekrar üretmek için: `python -m scripts.eval_retrieval`

| Embedding modeli | Parça boyutu | Sorgu yeniden yazma | İsabet |
|---|---|---|---|
| multilingual-e5-small | 200 | Yok | %92 |
| multilingual-e5-small | 800 | Yok | %83 |
| multilingual-e5-small | 1500 | Yok | %83 |
| multilingual-e5-base | 400 | Yok | %92 |
| multilingual-e5-base | 800 | Yok | %92 |
| **multilingual-e5-base** | **800** | **Var** | **%100** |

**Bulgular**

- Belgeler önce başlıklara göre bölündüğü için 800 ve 1500 aynı parçaları üretti; yapıya göre bölmede parça boyutu daha az kritik hale geliyor.
- Küçük modelde yüksek isabet için parçaları 200 karaktere indirmek gerekti; bu da içeriksiz başlık parçalarına ve bağlamı kopuk listelere yol açtı. Büyük model, bölümleri bütün tutarken aynı isabete ulaştı.
- Doğrudan aramada kaçan tek soru ("Udemy kursu almak istiyorum...") belgede geçmeyen bir marka adı içeriyordu. Hata embedding modelinde değil sorgunun ifadesindeydi; sorgu yeniden yazma ile çözüldü.
- **Test sızıntısı düzeltmesi:** İlk sürümde sorgu yeniden yazma prompt'undaki örnek, test sorusunun cevabını ("Udemy" → "online kurs") içeriyordu. Ölçümün adil olması için örnek, testte bulunmayan bir markayla değiştirildi ve ölçüm tekrarlandı.

## Tasarım kararları ve öğrenilenler

**LLM'in zayıf olduğu işi koda bırakmak.** İlk sürümde Ada "gelecek ayın ilk pazartesi" ifadesini yanlış hesapladı ve talebi yanlış günlere oluşturdu; ardından "yarın" için yanlış ayı söyledi. Prompt'u sertleştirmek yerine bir `get_calendar` aracı eklendi; onay ekranındaki tarih ve gün adları da LLM'den değil koddan üretiliyor.

**Onayı prompt'tan koda taşımak.** Aşama 3'te onay adımı sadece system prompt'taki bir kurala bağlıydı. LangGraph'a geçişle birlikte kayıt oluşturan araçlar `interrupt` ile durduruluyor; LLM kurala uymasa bile işlem onaysız çalışamıyor.

**Halüsinasyonu kural netleştirerek azaltmak.** İlk prompt sürümünde Ada izin günü uydurmadı ama var olmayan bir "çalışan portalı" önerdi. Yönlendirme kanallarını açıkça sınırlayan bir kural eklenerek giderildi.

**Araçlar sebep de döndürmeli.** İzin hakkı 0 olan bir çalışan için araç sadece "0 gün" döndürdüğünde Ada sebebini tahmin etmeye çalıştı. Araç artık sayının sebebini de (kıdem süresi) döndürüyor.

**Kişisel veri her seferinde kaynaktan okunmalı.** Ada bir noktada kalan izni önceki cevaptaki sayıdan hesapladı. Prompt, kişisel verilerin her soruda araçla yeniden sorgulanmasını zorunlu kılacak şekilde güncellendi.



### REST API

```bash
uvicorn src.api:app --reload      # veya: docker compose up --build
```

Swagger arayüzü: http://127.0.0.1:8000/docs (Authorize: `demo-token-e001`)

| Endpoint | Açıklama |
|---|---|
| `POST /chat` | Mesaj gönderir; onay gereken işlemlerde `approval_required` döner |
| `POST /chat/{thread_id}/approval` | Bekleyen işlemi onaylar veya reddeder |
| `GET /me` | Token'a göre oturum açmış çalışan |
| `GET /health` | Servis durumu |

Kimlik istek gövdesinden değil token'dan alınır; kullanıcılar yalnızca kendi
konuşmalarına erişebilir. Loglar JSON formatındadır ve mesaj içerikleri
gizlilik nedeniyle loglanmaz.

## Yol haritası

- [x] Aşama 0: Kurulum ve çoklu LLM sağlayıcı desteği
- [x] Aşama 1: Sohbet, prompt engineering ve niyet sınıflandırma
- [x] Aşama 2: Şirket belgeleri üzerinde RAG ve değerlendirme
- [x] Aşama 3: Tool calling, iş kuralları ve yetkilendirme
- [x] Aşama 4: LangGraph agent, human-in-the-loop onay, multi-query retrieval
- [ ] Aşama 5: FastAPI servisi, loglama ve Docker
- [ ] Aşama 6: Otomatik testler ve CI
- [ ] Aşama 7: Web arayüzü ve demo

## Teknolojiler

Python, LangChain, LangGraph, ChromaDB, sentence-transformers, SQLite, Pydantic