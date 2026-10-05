"""Web arayüzünün sol paneli için özet bilgiler: profil, izin bakiyesi, son talepler."""
from src.database import get_connection
from src.tools import LEAVE_TYPES, _balance

STATUS_LABELS = {
    "onay_bekliyor": "Onay bekliyor",
    "onaylandi": "Onaylandı",
    "reddedildi": "Reddedildi",
}


def get_dashboard(employee_id: str) -> dict:
    with get_connection() as conn:
        profile = conn.execute(
            "SELECT e.*, m.name AS manager_name FROM employees e "
            "LEFT JOIN employees m ON e.manager_id = m.id WHERE e.id = ?",
            (employee_id,),
        ).fetchone()
        balance = _balance(conn, employee_id)
        requests = conn.execute(
            "SELECT * FROM leave_requests WHERE employee_id = ? ORDER BY id DESC LIMIT 5",
            (employee_id,),
        ).fetchall()

    return {
        "profile": {
            "name": profile["name"],
            "title": profile["title"],
            "department": profile["department"],
            "manager": profile["manager_name"],
            "start_date": profile["start_date"],
        },
        "balance": balance,
        "requests": [
            {
                "id": r["id"],
                "type": LEAVE_TYPES.get(r["leave_type"], r["leave_type"]),
                "start_date": r["start_date"],
                "end_date": r["end_date"],
                "days": r["days"],
                "status": r["status"],
                "status_label": STATUS_LABELS.get(r["status"], r["status"]),
            }
            for r in requests
        ],
    }