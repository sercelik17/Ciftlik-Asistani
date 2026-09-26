from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_ollama import OllamaEmbeddings
from rank_bm25 import BM25Okapi

from .settings import settings

_TOKEN_RE = re.compile(r"[\wçğıöşüÇĞİÖŞÜ-]+", re.UNICODE)


def tokenize(text: str) -> list[str]:
    return [token.lower() for token in _TOKEN_RE.findall(text)]


def _doc_key(doc: Document) -> str:
    return str(doc.metadata.get("chunk_id") or (
        doc.metadata.get("source"), doc.metadata.get("page_number"), doc.page_content[:80]
    ))


class HybridRetriever:
    """Dense FAISS + sparse BM25 sonuçlarını Weighted Reciprocal Rank Fusion ile birleştirir."""

    def __init__(self, index_dir: Path | None = None):
        self.index_dir = index_dir or settings.resolved_index_dir()
        chunks_path = self.index_dir / "chunks.json"
        faiss_path = self.index_dir / "faiss"
        if not chunks_path.exists() or not faiss_path.exists():
            raise FileNotFoundError(
                "RAG indeksi bulunamadı. Önce `python -m thesis_rag.build_index` çalıştırın."
            )

        raw = json.loads(chunks_path.read_text(encoding="utf-8"))
        self.documents = [
            Document(page_content=item["page_content"], metadata=item["metadata"])
            for item in raw
        ]
        self.bm25 = BM25Okapi([tokenize(d.page_content) for d in self.documents])

        self.embeddings = OllamaEmbeddings(
            model=settings.embed_model,
            base_url=settings.ollama_base_url,
        )
        self.vector_store = FAISS.load_local(
            str(faiss_path),
            self.embeddings,
            allow_dangerous_deserialization=True,  # yalnızca kendi oluşturduğumuz yerel indeks
        )

    def _bm25_docs(self, question: str, top_k: int) -> list[Document]:
        scores = self.bm25.get_scores(tokenize(question))
        ranked = sorted(range(len(scores)), key=lambda i: float(scores[i]), reverse=True)
        return [self.documents[i] for i in ranked[:top_k] if float(scores[i]) > 0]

    def _dense_docs(self, question: str, top_k: int) -> list[Document]:
        return self.vector_store.similarity_search(question, k=top_k)

    def retrieve(self, question: str, final_top_k: int | None = None) -> list[Document]:
        final_top_k = final_top_k or settings.final_top_k
        dense = self._dense_docs(question, settings.vector_top_k)
        sparse = self._bm25_docs(question, settings.bm25_top_k)

        scores: dict[str, float] = defaultdict(float)
        docs_by_key: dict[str, Document] = {}
        rrf_k = 60.0

        for rank, doc in enumerate(dense, start=1):
            key = _doc_key(doc)
            docs_by_key[key] = doc
            scores[key] += settings.dense_weight / (rrf_k + rank)

        for rank, doc in enumerate(sparse, start=1):
            key = _doc_key(doc)
            docs_by_key[key] = doc
            scores[key] += settings.sparse_weight / (rrf_k + rank)

        ranked_keys = sorted(scores, key=scores.get, reverse=True)[:final_top_k]
        result = []
        for key in ranked_keys:
            doc = docs_by_key[key]
            doc.metadata["hybrid_score"] = round(scores[key], 8)
            result.append(doc)
        return result
