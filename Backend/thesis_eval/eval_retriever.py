from __future__ import annotations

import math
import json
import re
import urllib.request
from collections import defaultdict
from pathlib import Path

import numpy as np

from thesis_rag.settings import settings

_TOKEN_RE = re.compile(r"[\w-]+", re.UNICODE)
_TR_TRANSLATION = str.maketrans({
    "\u00e7": "c",
    "\u011f": "g",
    "\u0131": "i",
    "\u00f6": "o",
    "\u015f": "s",
    "\u00fc": "u",
    "\u00c7": "c",
    "\u011e": "g",
    "\u0130": "i",
    "\u00d6": "o",
    "\u015e": "s",
    "\u00dc": "u",
})

class BM25OkapiLite:
    """rank_bm25.BM25Okapi ile ayni formül; harici paket gerektirmez."""

    def __init__(self, corpus: list[list[str]], k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.corpus_size = len(corpus)
        self.doc_len = [len(doc) for doc in corpus]
        self.avgdl = sum(self.doc_len) / self.corpus_size if self.corpus_size else 0
        df: dict[str, int] = defaultdict(int)
        self.doc_freqs: list[dict[str, int]] = []
        for doc in corpus:
            freqs: dict[str, int] = defaultdict(int)
            for word in doc:
                freqs[word] += 1
            self.doc_freqs.append(freqs)
            for word in freqs:
                df[word] += 1
        self.idf = {}
        for word, freq in df.items():
            idf = math.log(self.corpus_size - freq + 0.5) - math.log(freq + 0.5)
            self.idf[word] = idf if idf >= 0 else 1e-6

    def get_scores(self, query: list[str]) -> np.ndarray:
        scores = np.zeros(self.corpus_size, dtype=np.float64)
        if self.avgdl <= 0:
            return scores
        for word in query:
            idf = self.idf.get(word)
            if idf is None:
                continue
            for index, freqs in enumerate(self.doc_freqs):
                tf = freqs.get(word, 0)
                if not tf:
                    continue
                denom = tf + self.k1 * (
                    1 - self.b + self.b * self.doc_len[index] / self.avgdl
                )
                scores[index] += idf * tf * (self.k1 + 1) / denom
        return scores


CATEGORY_KEYWORDS = {
    "01_mastitis": (
        "mastitis", "subklinik", "klinik mastitis",
        "meme sagligi", "meme enfeksiyonu",
    ),
    "02_sut_kalitesi": (
        "sut kalitesi", "somatik hucre", "shs", "scc",
        "milk quality", "laktoz", "raf omru",
    ),
    "03_besleme": (
        "besleme", "rasyon", "kuru madde", "kuru madde tuketimi",
        "yem tuketimi", "yemleme", "feed intake", "dry matter",
        "dmi", "rumen",
    ),
    "04_metabolik_hastaliklar": (
        "sut hummasi", "milk fever", "hipokalsemi", "hypocalcemia",
        "ketozis", "ketosis", "metabolik", "gecis donemi",
        "transition cow", "fresh cow", "negatif enerji dengesi",
    ),
    "05_buzagi_sagligi": (
        "buzagi", "kolostrum", "calf", "calves", "colostrum",
        "igg", "pasif bagisiklik", "sutten kesim", "weaning",
    ),
    "06_ureme": (
        "ureme", "ureme performansi", "fertilite", "fertility",
        "kizginlik", "tohumlama", "gebelik", "ovulasyon",
        "vucut kondisyonu", "body condition",
    ),
    "07_hayvan_refahi": (
        "hayvan refahi", "refah", "topallik", "lameness",
        "stres", "cow comfort", "barinak",
    ),
    "08_sut_hijyeni": (
        "sut hijyeni", "sagim hijyeni", "meme basi temizligi",
        "meme basi", "dezenfeksiyon", "dezenfektan",
        "milking hygiene", "teat cleaning", "sagim oncesi",
        "sagim sonrasi",
    ),
}


def normalize_text(text: str) -> str:
    text = str(text).translate(_TR_TRANSLATION).lower()
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def tokenize(text: str) -> list[str]:
    return [token.lower() for token in _TOKEN_RE.findall(normalize_text(text))]


def metadata_category(metadata: dict) -> str | None:
    source = str(metadata.get("source") or "")
    for part in re.split(r"[\\/]+", source):
        if part in CATEGORY_KEYWORDS:
            return part
    return None


def detect_categories(question: str) -> list[str]:
    q = normalize_text(question)
    scores: dict[str, int] = {}
    for category, keywords in CATEGORY_KEYWORDS.items():
        score = sum(1 for keyword in keywords if normalize_text(keyword) in q)
        if score:
            scores[category] = score
    if not scores:
        return []
    max_score = max(scores.values())
    selected = [cat for cat, score in scores.items() if score == max_score]
    if len(selected) == 1:
        strongest = selected[0]
        for category, score in scores.items():
            if category != strongest and score >= 1 and max_score <= 2:
                selected.append(category)
    return selected


def _post_json(url: str, payload: dict, timeout: int = 180) -> dict:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _embed_text(text: str) -> np.ndarray:
    body = _post_json(
        f"{settings.ollama_base_url.rstrip('/')}/api/embed",
        {"model": settings.embed_model, "input": text},
    )
    vector = body.get("embeddings")
    if not vector:
        raise RuntimeError("Ollama embedding cevabi bos")
    return np.asarray(vector[0], dtype=np.float32)


def _embed_texts(texts: list[str], batch_size: int = 16) -> np.ndarray:
    vectors = []
    total = len(texts)
    for start in range(0, total, batch_size):
        batch = texts[start:start + batch_size]
        body = _post_json(
            f"{settings.ollama_base_url.rstrip('/')}/api/embed",
            {"model": settings.embed_model, "input": batch},
        )
        embeddings = body.get("embeddings") or []
        if len(embeddings) != len(batch):
            raise RuntimeError(
                f"Beklenen {len(batch)} embedding, gelen {len(embeddings)}"
            )
        vectors.extend(embeddings)
        done = min(start + batch_size, total)
        print(f"  embedding {done}/{total}")
    return np.asarray(vectors, dtype=np.float32)


class TorchFreeRetriever:
    """
    LangChain / FAISS / Torch olmadan production ile ayni mantik:
    BM25 + BGE-M3 (Ollama HTTP) + Weighted RRF.
    Dense taraf FAISS IndexFlatL2 ile ayni: L2 uzakligina gore sira.
    """

    def __init__(self, cache_dir: Path | None = None):
        chunks_path = settings.resolved_index_dir() / "chunks.json"
        raw = json.loads(chunks_path.read_text(encoding="utf-8"))
        self.texts = [item["page_content"] for item in raw]
        self.metadatas = [item["metadata"] for item in raw]
        self.titles = [
            str(meta.get("source_name") or meta.get("source_stem") or "")
            for meta in self.metadatas
        ]
        self.bm25 = BM25OkapiLite(
            [tokenize(text) for text in self.texts],
            k1=settings.bm25_k1,
            b=settings.bm25_b,
        )
        self.cache_dir = cache_dir or settings.resolved_index_dir()
        self.dense = self._load_or_build_dense()

    def _load_or_build_dense(self) -> np.ndarray:
        cache_path = self.cache_dir / "eval_dense_embeddings.npy"
        if cache_path.exists():
            matrix = np.load(cache_path)
            if len(matrix) == len(self.texts):
                print(f"Hazir embedding onbellegi kullanildi: {cache_path}")
                return matrix

        print(f"BGE-M3 embedding olusturuluyor: {len(self.texts)} parca")
        matrix = _embed_texts(self.texts)
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        np.save(cache_path, matrix)
        print(f"Embedding onbellegi yazildi: {cache_path}")
        return matrix

    def _allowed(self, index: int, categories: list[str]) -> bool:
        if not categories:
            return True
        return metadata_category(self.metadatas[index]) in categories

    def _bm25_ranked(self, question: str, top_k: int, categories: list[str]) -> list[int]:
        scores = self.bm25.get_scores(tokenize(question))
        order = [
            i for i in np.argsort(scores)[::-1]
            if self._allowed(int(i), categories) and float(scores[i]) > 0
        ]
        return [int(i) for i in order[:top_k]]

    def _dense_ranked(self, question: str, top_k: int, categories: list[str]) -> list[int]:
        query = _embed_text(question)
        # IndexFlatL2: smaller distance is better
        distances = np.linalg.norm(self.dense - query, axis=1)
        order = [
            i for i in np.argsort(distances)
            if self._allowed(int(i), categories)
        ]
        return [int(i) for i in order[:top_k]]

    def _ranked_indices(
        self,
        question: str,
        final_top_k: int = 5,
        mode: str = "hybrid",
        dense_weight: float | None = None,
        sparse_weight: float | None = None,
    ) -> list[int]:
        dense_weight = settings.dense_weight if dense_weight is None else dense_weight
        sparse_weight = settings.sparse_weight if sparse_weight is None else sparse_weight
        categories = detect_categories(question)

        if mode == "bm25":
            sparse_idx = self._bm25_ranked(
                question, settings.bm25_top_k, categories
            )
            if categories and not sparse_idx:
                sparse_idx = self._bm25_ranked(
                    question, settings.bm25_top_k, []
                )
            return sparse_idx[:final_top_k]

        dense_idx = self._dense_ranked(
            question, settings.vector_top_k, categories
        )
        if mode == "faiss":
            if categories and not dense_idx:
                dense_idx = self._dense_ranked(
                    question, settings.vector_top_k, []
                )
            return dense_idx[:final_top_k]

        sparse_idx = self._bm25_ranked(
            question, settings.bm25_top_k, categories
        )
        if categories and not dense_idx and not sparse_idx:
            categories = []
            dense_idx = self._dense_ranked(
                question, settings.vector_top_k, categories
            )
            sparse_idx = self._bm25_ranked(
                question, settings.bm25_top_k, categories
            )

        scores: dict[int, float] = defaultdict(float)
        rrf_k = settings.rrf_k
        for rank, index in enumerate(dense_idx, start=1):
            scores[index] += dense_weight / (rrf_k + rank)
        for rank, index in enumerate(sparse_idx, start=1):
            scores[index] += sparse_weight / (rrf_k + rank)
        return sorted(scores, key=scores.get, reverse=True)[:final_top_k]

    def retrieve(
        self,
        question: str,
        final_top_k: int = 5,
        mode: str = "hybrid",
        dense_weight: float | None = None,
        sparse_weight: float | None = None,
    ) -> list[str]:
        indices = self._ranked_indices(
            question,
            final_top_k=final_top_k,
            mode=mode,
            dense_weight=dense_weight,
            sparse_weight=sparse_weight,
        )
        return [self.titles[i] for i in indices]

    def retrieve_hits(
        self,
        question: str,
        final_top_k: int = 5,
        mode: str = "hybrid",
    ) -> list[dict]:
        indices = self._ranked_indices(
            question, final_top_k=final_top_k, mode=mode
        )
        hits = []
        for i in indices:
            hits.append({
                "title": self.titles[i],
                "text": self.texts[i],
                "page": self.metadatas[i].get("page_number"),
                "chunk_id": self.metadatas[i].get("chunk_id"),
            })
        return hits
