"""Arama (retrieval) kalitesini ölçer. LLM kullanmaz, yani ücretsizdir.

Her test sorusu için beklenen belge bölümü, bulunan ilk k parça arasında mı?
Çalıştırmak için:                  python -m scripts.eval_retrieval
Sorgu yeniden yazma ile (LLM'li):   python -m scripts.eval_retrieval --rewrite
"""
import argparse

from src.rag import retrieve, retrieve_multi, source_label

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
    parser = argparse.ArgumentParser()
    parser.add_argument("--rewrite", action="store_true", help="Aramadan önce LLM ile sorguyu yeniden yaz")
    args = parser.parse_args()
    if args.rewrite:
        from src.query_rewrite import rewrite_query

    hits = 0
    for question, kaynak, bolum in TEST_SET:
        if args.rewrite:
            queries = [question] + rewrite_query(question)
            docs = retrieve_multi(queries, k=K)
        else:
            docs = [doc for doc, _ in retrieve(question, k=K)]
        results = [(doc, None) for doc in docs]
        found = any(
            doc.metadata.get("kaynak") == kaynak and doc.metadata.get("bolum") == bolum
            for doc, _ in results
        )
        hits += found
        mark = "OK  " if found else "YOK "
        print(f"{mark} {question}")
        if args.rewrite:
            print(f"      sorgular: {queries[1:]}")
        if not found:
            print(f"      beklenen: {kaynak} > {bolum}")
            print(f"      bulunan : {source_label(results[0][0])}")

    mode = "sorgu yeniden yazma İLE" if args.rewrite else "doğrudan arama"
    print(f"\nMod: {mode}")
    print(f"Sonuç: {hits}/{len(TEST_SET)} soruda doğru bölüm ilk {K} parça içinde "
          f"(isabet oranı: %{100 * hits / len(TEST_SET):.0f})")


if __name__ == "__main__":
    main()