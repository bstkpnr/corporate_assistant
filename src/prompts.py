"""Prompt dosyalarını okur ve içlerindeki değişkenleri doldurur.

Prompt'lar kodun içine gömülmek yerine prompts/ klasöründe ayrı dosyalarda
tutulur. Böylece Git geçmişinde nasıl değiştikleri izlenebilir.
"""
from datetime import date
from pathlib import Path

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"

COMPANY_NAME = "Nova Teknoloji A.Ş."
ASSISTANT_NAME = "Ada"
WEEKDAYS = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]


def load_prompt(name: str, **variables) -> str:
    """prompts/<name>.md dosyasını okur, {degisken} alanlarını doldurur."""
    text = (PROMPTS_DIR / f"{name}.md").read_text(encoding="utf-8")

    today = date.today()
    values = {
        "company_name": COMPANY_NAME,
        "assistant_name": ASSISTANT_NAME,
        "today": today.strftime("%d.%m.%Y"),
        "today_iso": today.isoformat(),
        "weekday": WEEKDAYS[today.weekday()],
        "employee_name": "Bilinmeyen kullanıcı",
        "employee_id": "-",
    }
    values.update(variables)  # dışarıdan gelen değerler varsayılanları ezer

    return text.format(**values)