"""Arama (retrieval) kalitesini ölçer. LLM kullanmaz, yani ücretsizdir.

Her test sorusu için beklenen belge bölümü, bulunan ilk k parça arasında mı?
Çalıştırmak için:  python -m scripts.eval_retrieval
"""
from src.rag import retrieve, source_label

K = 3

# (soru, beklenen kaynak dosya, beklenen bölüm başlığı)
TEST_SET = [
    ("Kullanmadığım izinleri seneye aktarabilir miyim?", "leave_policy.md", "Yıllık İzin Devri"),
    ("3 yıldır çalışıyorum, kaç gün iznim var?", "leave_policy.md", "Yıllık İzin Süreleri"),
    ("Evlenirsem kaç gün izin alırım?", "leave_policy.md", "Mazeret İzinleri"),
    ("Doktor raporumu kime göndermeliyim?", "leave_policy.md", "Hastalık İzni"),
    ("İş seyahatinde akşam yemeğine ne kadar harcayabilirim?", "expense_policy.md", "Harcama Limitleri"),
    ("Fişlerimi en geç ne zaman sisteme girmeliyim?", "expense_policy.md", "Masraf Beyanı ve Teslim Süresi"),
    ("Masraf ödemeleri hesabıma ne zaman yatar?", "expense_policy.md", "Geri Ödeme Takvimi"),
    ("Hangi günler ofise gelmem gerekiyor?", "remote_work.md", "Hibrit Çalışma Modeli"),
    ("Evime monitör almak istiyorum, şirket destek veriyor mu?", "remote_work.md", "Ev Ofis Desteği"),
    ("Şifremi unuttum ne yapmalıyım?", "information_IT.md", "Şifre Sıfırlama"),
    ("Laptopumu kaybettim, ne yapmalıyım?", "information_IT.md", "Cihaz Kaybı ve Güvenlik İhlali"),
    ("Udemy kursu almak istiyorum, şirket karşılar mı?", "benefits.md", "Eğitim ve Gelişim Bütçesi"),
]


def main():
    hits = 0
    for question, kaynak, bolum in TEST_SET:
        results = retrieve(question, k=K)
        found = any(
            doc.metadata.get("kaynak") == kaynak and doc.metadata.get("bolum") == bolum
            for doc, _ in results
        )
        hits += found
        mark = "OK  " if found else "YOK "
        print(f"{mark} {question}")
        if not found:
            print(f"      beklenen: {kaynak} > {bolum}")
            print(f"      bulunan : {source_label(results[0][0])}")

    print(f"\nSonuç: {hits}/{len(TEST_SET)} soruda doğru bölüm ilk {K} parça içinde "
          f"(isabet oranı: %{100 * hits / len(TEST_SET):.0f})")


if __name__ == "__main__":
    main()