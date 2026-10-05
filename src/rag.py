"""RAG: şirket belgelerini indeksleme, arama ve belgelere dayalı cevap üretme."""
import shutil
from pathlib import Path

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)

from src.embeddings import E5Embeddings
from src.llm import get_llm
from src.prompts import load_prompt

ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = ROOT / "data" / "policies"
DB_DIR = ROOT / "chroma_db"
COLLECTION = "mitogent_politikalar"

_embeddings = None
_vectorstore = None


def get_embeddings() -> E5Embeddings:
    """Embedding modelini bir kere yükler, sonra aynı nesneyi kullanır."""
    global _embeddings
    if _embeddings is None:
        _embeddings = E5Embeddings()
    return _embeddings


# ---------- 1. Parçalama (chunking) ----------

def load_and_split(chunk_size: int = 800, chunk_overlap: int = 100) -> list[Document]:
    """Belgeleri önce başlıklarına, uzun bölümleri de karakter sayısına göre böler."""
    header_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=[("#", "belge"), ("##", "bolum")],
        strip_headers=False,
    )
    char_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size, chunk_overlap=chunk_overlap
    )

    chunks = []
    for path in sorted(DOCS_DIR.glob("*.md")):
        sections = header_splitter.split_text(path.read_text(encoding="utf-8"))
        for section in sections:
            section.metadata["kaynak"] = path.name
        chunks.extend(char_splitter.split_documents(sections))
    return chunks


# ---------- 2. İndeksleme ----------

def build_index(chunk_size: int = 800, chunk_overlap: int = 100) -> list[Document]:
    """Eski indeksi silip belgeleri baştan indeksler."""
    global _vectorstore
    _vectorstore = None
    if DB_DIR.exists():
        shutil.rmtree(DB_DIR)

    chunks = load_and_split(chunk_size, chunk_overlap)
    Chroma.from_documents(
        chunks,
        embedding=get_embeddings(),
        persist_directory=str(DB_DIR),
        collection_name=COLLECTION,
        collection_metadata={"hnsw:space": "cosine"},
    )
    return chunks


def get_vectorstore() -> Chroma:
    global _vectorstore
    if _vectorstore is None:
        if not DB_DIR.exists():
            raise RuntimeError("İndeks bulunamadı. Önce çalıştır: python -m scripts.build_index")
        _vectorstore = Chroma(
            persist_directory=str(DB_DIR),
            embedding_function=get_embeddings(),
            collection_name=COLLECTION,
        )
    return _vectorstore


# ---------- 3. Arama (retrieval) ----------

def retrieve(question: str, k: int = 4) -> list[tuple[Document, float]]:
    """Soruya anlamca en yakın k parçayı döndürür.
    Skor bir mesafedir: 0'a ne kadar yakınsa o kadar benzer."""
    return get_vectorstore().similarity_search_with_score(question, k=k)


def retrieve_multi(queries: list[str], k: int = 4) -> list[Document]:
    """Birden fazla sorguyla arar ve sonuçları birleştirir (multi-query retrieval).

    Birleştirme için Reciprocal Rank Fusion (RRF) kullanılır: her parça, her
    sorgunun sonuç listesindeki sırasına göre puan alır (1. sıra en yüksek).
    Birden fazla sorguda üst sıralarda çıkan parçalar en üste yükselir.
    """
    scores: dict[str, float] = {}
    docs: dict[str, Document] = {}
    for query in queries:
        for rank, (doc, _) in enumerate(retrieve(query, k=k)):
            key = f"{doc.metadata.get('kaynak')}|{doc.page_content[:100]}"
            scores[key] = scores.get(key, 0) + 1 / (60 + rank)
            docs[key] = doc
    best = sorted(scores, key=scores.get, reverse=True)[:k]
    return [docs[key] for key in best]


def source_label(doc: Document) -> str:
    bolum = doc.metadata.get("bolum")
    return f"{doc.metadata['kaynak']} > {bolum}" if bolum else doc.metadata["kaynak"]


def format_context(docs: list[Document]) -> str:
    parts = []
    for i, doc in enumerate(docs, start=1):
        parts.append(f"[{i}] Kaynak: {source_label(doc)}\n{doc.page_content}")
    return "\n\n".join(parts)


def build_rag_message(question: str, docs: list[Document]) -> HumanMessage:
    """Soruyu, bulunan belge parçalarıyla birlikte tek bir mesaja paketler."""
    content = load_prompt("rag_answer", context=format_context(docs), question=question)
    return HumanMessage(content=content)


# ---------- 4. Cevap üretme ----------

def answer(question: str, k: int = 4) -> tuple[str, list[Document]]:
    """Tek bir soruyu belgelere dayanarak cevaplar."""
    docs = [doc for doc, _ in retrieve(question, k)]
    llm = get_llm(temperature=0)
    reply = llm.invoke([
        SystemMessage(content=load_prompt("system_prompt")),
        build_rag_message(question, docs),
    ])
    return reply.text, docs