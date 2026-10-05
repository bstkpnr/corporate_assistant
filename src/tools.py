"""Bastet'in kullanabileceği araçlar (tools).

Her aracın docstring'i, LLM'e aracın ne işe yaradığını anlatan açıklamadır.
LLM hangi aracı ne zaman çağıracağına bu açıklamalara bakarak karar verir;
yani docstring'ler de bir tür prompt'tur.

GÜVENLİK: Araçlar employee_id parametresi ALMAZ. Kimlik, oturum açmış
kullanıcıdan gelir (make_tools'a verilen employee_id). Böylece LLM başka
bir çalışanın verisine erişemez.
"""
from datetime import date, datetime, timedelta
from typing import Literal

from langchain_core.tools import tool

from src.database import get_connection
from src.prompts import WEEKDAYS
from src.rag import retrieve_multi, source_label

SLA = {"P1": "4 saat", "P2": "1 iş günü", "P3": "3 iş günü"}

# Kayıt oluşturan araçlar: graf bunları çalıştırmadan önce kullanıcı onayı alır
SENSITIVE_TOOLS = {"create_leave_request", "create_it_ticket"}
LEAVE_TYPES = {"yillik": "Yıllık izin", "mazeret": "Mazeret izni", "hastalik": "Hastalık izni"}


def business_days(start: date, end: date) -> int:
    """İki tarih arasındaki (ikisi dahil) hafta içi gün sayısı.
    Not: Resmi tatiller hesaba katılmıyor; bu bilinen bir sınırlama."""
    days, d = 0, start
    while d <= end:
        if d.weekday() < 5:
            days += 1
        d += timedelta(days=1)
    return days


def fmt_day(d: date) -> str:
    """2026-11-02 -> '02.11.2026 Pazartesi'"""
    return f"{d.strftime('%d.%m.%Y')} {WEEKDAYS[d.weekday()]}"


def _balance(conn, employee_id: str) -> dict | None:
    row = conn.execute(
        "SELECT * FROM leave_balances WHERE employee_id = ? AND year = ?",
        (employee_id, date.today().year),
    ).fetchone()
    if row is None:
        return None
    pending = conn.execute(
        "SELECT COALESCE(SUM(days), 0) FROM leave_requests "
        "WHERE employee_id = ? AND leave_type = 'yillik' AND status = 'onay_bekliyor'",
        (employee_id,),
    ).fetchone()[0]
    total = row["entitled_days"] + row["carried_over"]
    return {
        "hak": row["entitled_days"],
        "devreden": row["carried_over"],
        "kullanilan": row["used_days"],
        "onay_bekleyen": pending,
        "kalan": total - row["used_days"] - pending,
    }


def describe_action(name: str, args: dict) -> str:
    """Onay ekranı için araç çağrısını insanın okuyabileceği bir özete çevirir.
    Tarihler ve gün sayısı LLM'den değil koddan hesaplanır."""
    if name == "create_leave_request":
        try:
            start = datetime.strptime(args["start_date"], "%Y-%m-%d").date()
            end = datetime.strptime(args["end_date"], "%Y-%m-%d").date()
            leave = LEAVE_TYPES.get(args.get("leave_type"), args.get("leave_type"))
            return f"İzin talebi: {leave}, {fmt_day(start)} - {fmt_day(end)} ({business_days(start, end)} iş günü)"
        except (KeyError, ValueError):
            return f"İzin talebi: {args}"
    if name == "create_it_ticket":
        priority = args.get("priority")
        return (
            f"IT destek talebi: {args.get('title')} (öncelik {priority}, hedef süre {SLA.get(priority, '?')})\n"
            f"    Açıklama: {args.get('description')}"
        )
    return f"{name}: {args}"


def make_tools(employee_id: str) -> list:
    """Oturum açmış çalışana özel araç listesini oluşturur."""

    @tool(parse_docstring=True)
    def search_company_policies(queries: list[str]) -> str:
        """Şirket politika belgelerinde arama yapar (izin, masraf, uzaktan çalışma,
        bilgi güvenliği ve IT destek, yan haklar). Şirket kuralları, limitler,
        süreler veya prosedürlerle ilgili her soruda kullan.

        Args:
            queries: 1-3 arama ifadesi. Kullanıcının sorusunu belgelerin resmi diline çevir; marka veya ürün adları yerine genel kavramlar kullan (örneğin "Udemy kursu" yerine "online kurs eğitim bütçesi"). Soruyu farklı açılardan ifade eden birden fazla sorgu verebilirsin.
        """
        docs = retrieve_multi(queries[:3], k=4)
        return "\n\n".join(f"[Kaynak: {source_label(d)}]\n{d.page_content}" for d in docs)

    @tool(parse_docstring=True)
    def get_calendar(month: str) -> str:
        """Belirtilen ayın takvimini gün adlarıyla getirir. "Yarın", "gelecek pazartesi",
        "ayın ilk cuması" gibi göreli tarihleri belirlemeden önce MUTLAKA kullan;
        tarihleri asla kafadan hesaplama.

        Args:
            month: Ay, YYYY-MM formatında. Örneğin 2026-11.
        """
        try:
            first = datetime.strptime(month, "%Y-%m").date()
        except ValueError:
            return "HATA: Ay YYYY-MM formatında olmalı."
        lines, d = [], first
        while d.month == first.month:
            note = " (hafta sonu)" if d.weekday() >= 5 else ""
            if d == date.today():
                note += " <- BUGÜN"
            lines.append(f"{d.isoformat()} {WEEKDAYS[d.weekday()]}{note}")
            d += timedelta(days=1)
        return "\n".join(lines)

    @tool
    def get_my_profile() -> str:
        """Kullanıcının kendi profil bilgilerini getirir: adı, departmanı, unvanı,
        yöneticisi ve işe başlama tarihi."""
        with get_connection() as conn:
            row = conn.execute(
                "SELECT e.*, m.name AS manager_name FROM employees e "
                "LEFT JOIN employees m ON e.manager_id = m.id WHERE e.id = ?",
                (employee_id,),
            ).fetchone()
        return (
            f"Ad: {row['name']}\nDepartman: {row['department']}\nUnvan: {row['title']}\n"
            f"Yönetici: {row['manager_name'] or 'Yok'}\nİşe başlama: {row['start_date']}"
        )

    @tool
    def get_leave_balance() -> str:
        """Kullanıcının bu yılki yıllık izin bakiyesini getirir: hak edilen,
        devreden, kullanılan, onay bekleyen ve kalan gün sayıları."""
        with get_connection() as conn:
            b = _balance(conn, employee_id)
            start = conn.execute(
                "SELECT start_date FROM employees WHERE id = ?", (employee_id,)
            ).fetchone()[0]
        if b is None:
            return "Bu yıl için izin bakiyesi kaydı bulunamadı."
        text = (
            f"Bu yılki hak: {b['hak']} gün\nGeçen yıldan devreden: {b['devreden']} gün\n"
            f"Kullanılan: {b['kullanilan']} gün\nOnay bekleyen talepler: {b['onay_bekleyen']} gün\n"
            f"Kalan kullanılabilir izin: {b['kalan']} gün"
        )
        # Araç sadece sayı değil, sayının sebebini de döndürmeli; yoksa LLM tahmin eder
        start_date = datetime.strptime(start, "%Y-%m-%d").date()
        if (date.today() - start_date).days < 365:
            text += (
                f"\nNot: İşe başlama tarihi {fmt_day(start_date)}. Çalışan henüz 1 yıllık "
                f"kıdemi doldurmadığı için yıllık izin hakkı oluşmamıştır."
            )
        return text

    @tool
    def list_my_leave_requests() -> str:
        """Kullanıcının son izin taleplerini ve durumlarını listeler."""
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM leave_requests WHERE employee_id = ? ORDER BY id DESC LIMIT 10",
                (employee_id,),
            ).fetchall()
        if not rows:
            return "Hiç izin talebi bulunamadı."
        return "\n".join(
            f"#{r['id']}: {LEAVE_TYPES[r['leave_type']]}, {r['start_date']} - {r['end_date']}, "
            f"{r['days']} iş günü, durum: {r['status']}"
            for r in rows
        )

    @tool(parse_docstring=True)
    def create_leave_request(
        start_date: str,
        end_date: str,
        leave_type: Literal["yillik", "mazeret", "hastalik"],
    ) -> str:
        """Kullanıcı adına izin talebi oluşturur ve yöneticisinin onayına gönderir.
        Sistem bu aracı çalıştırmadan önce kullanıcıdan onay alır.

        Args:
            start_date: İznin ilk günü, YYYY-MM-DD formatında.
            end_date: İznin son günü, YYYY-MM-DD formatında.
            leave_type: İzin türü: yillik, mazeret veya hastalik.
        """
        # 1) Girdi doğrulama: LLM'in verdiği değerlere körü körüne güvenme
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d").date()
            end = datetime.strptime(end_date, "%Y-%m-%d").date()
        except ValueError:
            return "HATA: Tarihler YYYY-MM-DD formatında olmalı."
        today = date.today()
        if start < today:
            return "HATA: Geçmiş bir tarih için izin talebi oluşturulamaz."
        if end < start:
            return "HATA: Bitiş tarihi başlangıç tarihinden önce olamaz."
        days = business_days(start, end)
        if days == 0:
            return "HATA: Seçilen aralıkta hiç iş günü yok (sadece hafta sonu)."

        # 2) İş kuralları (izin politikası): kodda zorunlu kılınır
        if leave_type == "yillik":
            required = 15 if days > 5 else 5
            notice = business_days(today + timedelta(days=1), start - timedelta(days=1))
            if notice < required:
                return (
                    f"HATA: Politika gereği {days} günlük yıllık izin en az {required} iş günü "
                    f"önceden talep edilmeli; şu an {notice} iş günü var. Acil durumlarda "
                    f"yöneticiyle görüşülerek süre kısaltılabilir."
                )

        with get_connection() as conn:
            if leave_type == "yillik":
                b = _balance(conn, employee_id)
                if b is None or b["kalan"] < days:
                    kalan = b["kalan"] if b else 0
                    return f"HATA: Yetersiz bakiye. Talep {days} gün, kalan izin {kalan} gün."

            cur = conn.execute(
                "INSERT INTO leave_requests (employee_id, leave_type, start_date, end_date, days, status, created_at) "
                "VALUES (?, ?, ?, ?, ?, 'onay_bekliyor', ?)",
                (employee_id, leave_type, start_date, end_date, days, datetime.now().isoformat(timespec="seconds")),
            )
            manager = conn.execute(
                "SELECT m.name FROM employees e LEFT JOIN employees m ON e.manager_id = m.id WHERE e.id = ?",
                (employee_id,),
            ).fetchone()[0]

        return (
            f"BAŞARILI: İzin talebi #{cur.lastrowid} oluşturuldu. {LEAVE_TYPES[leave_type]}, "
            f"{fmt_day(start)} - {fmt_day(end)}, {days} iş günü. "
            f"Onay için gönderildi: {manager or 'İK'}."
        )

    @tool(parse_docstring=True)
    def create_it_ticket(
        title: str,
        description: str,
        priority: Literal["P1", "P2", "P3"],
    ) -> str:
        """Kullanıcı adına IT destek talebi açar.
        Sistem bu aracı çalıştırmadan önce kullanıcıdan onay alır.

        Args:
            title: Sorunun kısa başlığı.
            description: Sorunun ayrıntılı açıklaması.
            priority: P1 çalışmayı tamamen durduran kritik sorunlar, P2 çalışmayı ciddi şekilde etkileyen sorunlar, P3 diğer talepler.
        """
        with get_connection() as conn:
            cur = conn.execute(
                "INSERT INTO it_tickets (employee_id, title, description, priority, status, created_at) "
                "VALUES (?, ?, ?, ?, 'acik', ?)",
                (employee_id, title, description, priority, datetime.now().isoformat(timespec="seconds")),
            )
        return f"BAŞARILI: IT destek talebi #{cur.lastrowid} açıldı. Öncelik {priority}, hedef çözüm süresi {SLA[priority]}."

    return [
        search_company_policies,
        get_calendar,
        get_my_profile,
        get_leave_balance,
        list_my_leave_requests,
        create_leave_request,
        create_it_ticket,
    ]