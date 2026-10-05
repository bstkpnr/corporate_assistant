FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HF_HOME=/app/.cache/huggingface

WORKDIR /app

# PyTorch'un sadece CPU sürümü: GPU sürümüne göre imajı birkaç GB küçültür
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# Önce sadece requirements kopyalanır: kod değişince paketler yeniden kurulmaz (katman önbelleği)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Embedding modelini indir, belgeleri indeksle, örnek veritabanını oluştur.
# Böylece konteyner açılır açılmaz kullanıma hazır olur.
RUN python -m scripts.build_index && python -m scripts.init_db

EXPOSE 8000
CMD ["uvicorn", "src.api:app", "--host", "0.0.0.0", "--port", "8000"]