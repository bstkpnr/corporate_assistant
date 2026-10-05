"""Metinleri embedding'e (anlam vektörüne) çeviren yerel model.

intfloat/multilingual-e5-small: Türkçe dahil 100'e yakın dili anlayan,
bilgisayarda ücretsiz çalışan küçük bir model. İlk kullanımda bir kere
indirilir (~470 MB), sonra önbellekten yüklenir.

E5 modellerinin bir özelliği: belgelerin başına "passage: ", sorguların
başına "query: " eklenmesini bekler. Bu yüzden kendi küçük sınıfımızı yazdık.
"""
from langchain_core.embeddings import Embeddings
from sentence_transformers import SentenceTransformer

EMBEDDING_MODEL = "intfloat/multilingual-e5-base"


class E5Embeddings(Embeddings):
    def __init__(self, model_name: str = EMBEDDING_MODEL):
        self.model = SentenceTransformer(model_name)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        vectors = self.model.encode(
            [f"passage: {t}" for t in texts], normalize_embeddings=True
        )
        return vectors.tolist()

    def embed_query(self, text: str) -> list[float]:
        vector = self.model.encode(f"query: {text}", normalize_embeddings=True)
        return vector.tolist()