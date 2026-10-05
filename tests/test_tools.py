"""Araçların ve iş kurallarının testleri. LLM kullanılmaz."""
from datetime import date, timedelta

from src.database import get_connection
from src.tools import business_days, describe_action, make_tools
from tests.conftest import next_monday


def tools_of(employee_id: str) -> dict:
    return {t.name: t for t in make_tools(employee_id)}


def leave(tools, start: date, end: date, leave_type="yillik") -> str:
    return tools["create_leave_request"].invoke({
        "start_date": start.isoformat(), "end_date": end.isoformat(), "leave_type": leave_type,
    })


# ---------- Yardımcı fonksiyonlar ----------

def test_business_days_skips_weekend():
    friday, monday = date(2026, 10, 9), date(2026, 10, 12)
    assert business_days(friday, monday) == 2


def test_describe_action_uses_real_weekdays():
    text = describe_action("create_leave_request", {
        "start_date": "2026-11-02", "end_date": "2026-11-03", "leave_type": "yillik",
    })
    assert "02.11.2026 Pazartesi" in text
    assert "03.11.2026 Salı" in text
    assert "2 iş günü" in text


def test_calendar_marks_weekends(db):
    result = tools_of("E001")["get_calendar"].invoke({"month": "2026-11"})
    assert "2026-11-01 Pazar (hafta sonu)" in result
    assert "2026-11-02 Pazartesi" in result


# ---------- İzin bakiyesi ----------

def test_initial_balance(db):
    result = tools_of("E001")["get_leave_balance"].invoke({})
    assert "Kalan kullanılabilir izin: 14 gün" in result


def test_zero_balance_explains_reason(db):
    result = tools_of("E004")["get_leave_balance"].invoke({})
    assert "kıdem" in result


# ---------- İzin talebi iş kuralları ----------

def test_rejects_past_date(db):
    yesterday = date.today() - timedelta(days=1)
    assert "HATA" in leave(tools_of("E001"), yesterday, yesterday)


def test_rejects_end_before_start(db):
    start = next_monday(30)
    assert "HATA" in leave(tools_of("E001"), start, start - timedelta(days=3))


def test_rejects_short_notice(db):
    d = date.today() + timedelta(days=1)
    while d.weekday() >= 5:
        d += timedelta(days=1)
    result = leave(tools_of("E001"), d, d)
    assert "HATA" in result and "önceden" in result


def test_rejects_insufficient_balance(db):
    start = next_monday(60)
    end = start + timedelta(days=27)  # 20 iş günü, kalan 14
    result = leave(tools_of("E001"), start, end)
    assert "Yetersiz bakiye" in result


def test_successful_request_updates_balance(db):
    tools = tools_of("E001")
    start = next_monday(30)
    result = leave(tools, start, start + timedelta(days=1))
    assert result.startswith("BAŞARILI")
    assert "Kalan kullanılabilir izin: 12 gün" in tools["get_leave_balance"].invoke({})


# ---------- Güvenlik ----------

def test_no_tool_accepts_employee_id(db):
    """Hiçbir araç kimliği parametre olarak almamalı; kimlik oturumdan gelir."""
    for tool in make_tools("E001"):
        assert "employee_id" not in tool.args, f"{tool.name} employee_id kabul ediyor!"


def test_employees_cannot_see_each_others_requests(db):
    start = next_monday(30)
    leave(tools_of("E001"), start, start)
    result = tools_of("E003")["list_my_leave_requests"].invoke({})
    assert "Hiç izin talebi bulunamadı" in result


def test_it_ticket_is_created(db):
    result = tools_of("E001")["create_it_ticket"].invoke({
        "title": "Laptop açılmıyor", "description": "Hiç açılmıyor", "priority": "P1",
    })
    assert result.startswith("BAŞARILI") and "4 saat" in result
    with get_connection() as conn:
        assert conn.execute("SELECT COUNT(*) FROM it_tickets").fetchone()[0] == 1