"""Hayali şirketin çalışan veritabanı (SQLite).

Gerçek bir şirkette bu bilgiler bir İK sisteminden (SAP, Workday vb.) gelirdi.
Biz öğrenme amacıyla küçük bir SQLite veritabanı kullanıyoruz.
"""
import sqlite3
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "nova.db"

SCHEMA = """
CREATE TABLE employees (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    email       TEXT NOT NULL,
    department  TEXT NOT NULL,
    title       TEXT NOT NULL,
    manager_id  TEXT REFERENCES employees(id),
    start_date  TEXT NOT NULL
);

CREATE TABLE leave_balances (
    employee_id   TEXT REFERENCES employees(id),
    year          INTEGER NOT NULL,
    entitled_days INTEGER NOT NULL,   -- o yılın izin hakkı (Nova ek izni dahil)
    carried_over  INTEGER NOT NULL,   -- geçen yıldan devreden
    used_days     INTEGER NOT NULL,   -- onaylanıp kullanılan
    PRIMARY KEY (employee_id, year)
);

CREATE TABLE leave_requests (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id TEXT REFERENCES employees(id),
    leave_type  TEXT NOT NULL,
    start_date  TEXT NOT NULL,
    end_date    TEXT NOT NULL,
    days        INTEGER NOT NULL,
    status      TEXT NOT NULL,        -- onay_bekliyor | onaylandi | reddedildi
    created_at  TEXT NOT NULL
);

CREATE TABLE it_tickets (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id TEXT REFERENCES employees(id),
    title       TEXT NOT NULL,
    description TEXT NOT NULL,
    priority    TEXT NOT NULL,
    status      TEXT NOT NULL,
    created_at  TEXT NOT NULL
);
"""

EMPLOYEES = [
    # id, ad, e-posta, departman, unvan, yönetici, işe başlama
    ("E005", "Can Öztürk", "can.ozturk@novateknoloji.com", "Yazılım", "Yazılım Müdürü", None, "2016-05-02"),
    ("E002", "Elif Demir", "elif.demir@novateknoloji.com", "İnsan Kaynakları", "İK Müdürü", None, "2015-09-14"),
    ("E001", "Deniz Kaya", "deniz.kaya@novateknoloji.com", "Yazılım", "Yazılım Geliştirici", "E005", "2023-03-01"),
    ("E003", "Mert Çelik", "mert.celik@novateknoloji.com", "Yazılım", "Kıdemli Yazılım Geliştirici", "E005", "2018-11-19"),
    ("E004", "Zeynep Arslan", "zeynep.arslan@novateknoloji.com", "İnsan Kaynakları", "İK Uzmanı", "E002", "2026-02-02"),
]


def balances_for(year: int):
    # employee_id, yıl, hak (yasal + 2 gün Nova ek izni), devreden, kullanılan
    return [
        ("E001", year, 16, 2, 4),
        ("E002", year, 28, 5, 12),
        ("E003", year, 22, 5, 10),
        ("E004", year, 0, 0, 0),    # 1 yılını doldurmadı
        ("E005", year, 22, 3, 8),
    ]


def init_db() -> None:
    """Veritabanını silip örnek verilerle baştan oluşturur."""
    DB_PATH.parent.mkdir(exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()

    year = date.today().year
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA)
    conn.executemany("INSERT INTO employees VALUES (?, ?, ?, ?, ?, ?, ?)", EMPLOYEES)
    conn.executemany("INSERT INTO leave_balances VALUES (?, ?, ?, ?, ?)", balances_for(year))
    conn.execute(
        "INSERT INTO leave_requests (employee_id, leave_type, start_date, end_date, days, status, created_at) "
        "VALUES ('E001', 'yillik', ?, ?, 4, 'onaylandi', ?)",
        (f"{year}-07-14", f"{year}-07-17", f"{year}-06-20"),
    )
    conn.commit()
    conn.close()


def get_connection() -> sqlite3.Connection:
    if not DB_PATH.exists():
        raise RuntimeError("Veritabanı bulunamadı. Önce çalıştır: python -m scripts.init_db")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # satırlara row["name"] şeklinde erişim
    return conn


def get_employee(employee_id: str):
    with get_connection() as conn:
        return conn.execute("SELECT * FROM employees WHERE id = ?", (employee_id,)).fetchone()