"""Örnek çalışan veritabanını oluşturur (varsa sıfırlar).

Çalıştırmak için:  python -m scripts.init_db
"""
from src.database import DB_PATH, get_connection, init_db


def main():
    init_db()
    print(f"Veritabanı oluşturuldu: {DB_PATH}\n")
    print("Örnek çalışanlar (sohbette --user ile seçebilirsin):")
    with get_connection() as conn:
        for r in conn.execute("SELECT id, name, title FROM employees ORDER BY id"):
            print(f"  {r['id']}  {r['name']:<15} {r['title']}")


if __name__ == "__main__":
    main()