"""Yapılandırılmış (JSON) loglama.

Her log satırı tek bir JSON nesnesidir. Bu format, Elasticsearch, Datadog veya
Grafana Loki gibi log sistemlerinde arama ve filtrelemeyi kolaylaştırır.

GİZLİLİK: Kullanıcı mesajlarının içeriği bilerek loglanmaz; çalışanların
kişisel bilgilerini içerebilir (KVKK). Sadece meta veriler loglanır.
"""
import json
import logging
import sys
from datetime import datetime, timezone

# Log kayıtlarına eklenebilecek ek alanlar
EXTRA_FIELDS = ("request_id", "method", "path", "status_code", "duration_ms",
                "employee_id", "thread_id", "status", "tool_calls")


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        data = {
            "time": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for field in EXTRA_FIELDS:
            if hasattr(record, field):
                data[field] = getattr(record, field)
        if record.exc_info:
            data["error"] = self.formatException(record.exc_info)
        return json.dumps(data, ensure_ascii=False)


def setup_logging(level: int = logging.INFO) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)
    # Kütüphanelerin gürültülü loglarını kıs
    for noisy in ("httpx", "httpx2", "httpcore", "sentence_transformers", "chromadb", "uvicorn.access"):
        logging.getLogger(noisy).setLevel(logging.WARNING)