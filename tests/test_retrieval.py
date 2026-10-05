"""Arama kalitesi testi. Embedding modeli ve indeks gerektirir.

Çalıştırmak için:  pytest -m slow
"""
import pytest

from src.rag import DB_DIR

pytestmark = pytest.mark.slow

MIN_HIT_RATE = 0.9


@pytest.mark.skipif(not DB_DIR.exists(), reason="Önce indeks oluştur: python -m scripts.build_index")
def test_retrieval_hit_rate():
    from scripts.eval_retrieval import K, TEST_SET
    from src.rag import retrieve

    hits = 0
    for question, kaynak, bolum in TEST_SET:
        results = retrieve(question, k=K)
        hits += any(
            d.metadata.get("kaynak") == kaynak and d.metadata.get("bolum") == bolum
            for d, _ in results
        )
    rate = hits / len(TEST_SET)
    assert rate >= MIN_HIT_RATE, f"İsabet oranı %{rate * 100:.0f}, eşik %{MIN_HIT_RATE * 100:.0f}"