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


CATEGORY_KEYWORDS = {
    "01_mastitis": (
        "mastitis",
        "subklinik",
        "klinik mastitis",
        "meme sagligi",
        "meme enfeksiyonu",
    ),

    "02_sut_kalitesi": (
        "sut kalitesi",
        "somatik hucre",
        "shs",
        "scc",
        "milk quality",
        "laktoz",
        "raf omru",
    ),

    "03_besleme": (
        "besleme",
        "rasyon",
        "kuru madde",
        "kuru madde tuketimi",
        "yem tuketimi",
        "yemleme",
        "feed intake",
        "dry matter",
        "dmi",
        "rumen",
    ),

    "04_metabolik_hastaliklar": (
        "sut hummasi",
        "milk fever",
        "hipokalsemi",
        "hypocalcemia",
        "ketozis",
        "ketosis",
        "metabolik",
        "gecis donemi",
        "transition cow",
        "fresh cow",
        "negatif enerji dengesi",
    ),

    "05_buzagi_sagligi": (
        "buzagi",
        "kolostrum",
        "calf",
        "calves",
        "colostrum",
        "igg",
        "pasif bagisiklik",
        "sutten kesim",
        "weaning",
    ),

    "06_ureme": (
        "ureme",
        "ureme performansi",
        "fertilite",
        "fertility",
        "kizginlik",
        "tohumlama",
        "gebelik",
        "ovulasyon",
        "vucut kondisyonu",
        "body condition",
        "d?l tutma",
        "dol tutma",
    ),

    "07_hayvan_refahi": (
        "hayvan refahi",
        "refah",
        "topallik",
        "lameness",
        "stres",
        "cow comfort",
        "barinak",
    ),

    "08_sut_hijyeni": (
        "sut hijyeni",
        "sagim hijyeni",
        "meme basi temizligi",
        "meme basi",
        "dezenfeksiyon",
        "dezenfektan",
        "milking hygiene",
        "teat cleaning",
        "sagim oncesi",
        "sagim sonrasi",
    ),
}


def normalize_text(text: str) -> str:
    text = str(text).translate(_TR_TRANSLATION).lower()
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def tokenize(text: str) -> list[str]:
    normalized = normalize_text(text)
    return [
        token.lower()
        for token in _TOKEN_RE.findall(normalized)
    ]


def _doc_key(doc: Document) -> str:
    return str(
        doc.metadata.get("chunk_id")
        or (
            doc.metadata.get("source"),
            doc.metadata.get("page_number"),
            doc.page_content[:80],
        )
    )


def _metadata_category(metadata: dict) -> str | None:
    """
    Metadata icindeki source yolundan bilgi tabani
    kategori klasorunu bulur.

    Ornek:
    .../knowledge_base/03_besleme/file.pdf
    -> 03_besleme
    """

    source = str(metadata.get("source") or "")

    parts = [
        part
        for part in re.split(r"[\\/]+", source)
        if part
    ]

    for part in parts:
        if part in CATEGORY_KEYWORDS:
            return part

    return None


class HybridRetriever:
    """
    Dense FAISS + sparse BM25 sonuclarini Weighted Reciprocal
    Rank Fusion ile birlestirir.

    Soru belirli bir uzmanlik kategorisine acikca aitse,
    retrieval o kategoriye ait dokumanlarla sinirlandirilir.
    """

    def __init__(self, index_dir: Path | None = None):
        self.index_dir = (
            index_dir
            or settings.resolved_index_dir()
        )

        chunks_path = self.index_dir / "chunks.json"
        faiss_path = self.index_dir / "faiss"

        if not chunks_path.exists() or not faiss_path.exists():
            raise FileNotFoundError(
                "RAG indeksi bulunamadi. "
                "Once `python -m thesis_rag.build_index` calistirin."
            )

        raw = json.loads(
            chunks_path.read_text(encoding="utf-8")
        )

        self.documents = [
            Document(
                page_content=item["page_content"],
                metadata=item["metadata"],
            )
            for item in raw
        ]

        self.bm25 = BM25Okapi(
            [
                tokenize(d.page_content)
                for d in self.documents
            ]
        )

        self.embeddings = OllamaEmbeddings(
            model=settings.embed_model,
            base_url=settings.ollama_base_url,
        )

        self.vector_store = FAISS.load_local(
            str(faiss_path),
            self.embeddings,
            allow_dangerous_deserialization=True,
        )

    @staticmethod
    def detect_categories(
        question: str,
    ) -> list[str]:
        """
        Soruda acik konu sinyali varsa ilgili bilgi tabani
        kategorisini/kategorilerini deterministik olarak bulur.

        Birden fazla konu ayni anda aciksa birden fazla kategori
        dondurulebilir. Ornegin:
        'Mastitis sut kalitesini nasil etkiler?'
        -> 01_mastitis + 02_sut_kalitesi
        """

        q = normalize_text(question)

        category_scores: dict[str, int] = {}

        for category, keywords in CATEGORY_KEYWORDS.items():
            score = 0

            for keyword in keywords:
                keyword_normalized = normalize_text(keyword)

                if keyword_normalized in q:
                    score += 1

            if score > 0:
                category_scores[category] = score

        if not category_scores:
            return []

        max_score = max(category_scores.values())

        # En guclu kategoriyi al.
        selected = [
            category
            for category, score in category_scores.items()
            if score == max_score
        ]

        # Farkli iki alan da acik bicimde belirtilmisse,
        # ikinci kategoriyi de koru.
        # Ornek: mastitis + sut kalitesi.
        if len(selected) == 1:
            strongest = selected[0]

            for category, score in category_scores.items():
                if category == strongest:
                    continue

                if score >= 1 and max_score <= 2:
                    selected.append(category)

        return selected

    @staticmethod
    def _allowed(
        doc: Document,
        categories: list[str] | None,
    ) -> bool:
        if not categories:
            return True

        return (
            _metadata_category(doc.metadata)
            in categories
        )

    def _bm25_docs(
        self,
        question: str,
        top_k: int,
        categories: list[str] | None = None,
    ) -> list[Document]:

        scores = self.bm25.get_scores(
            tokenize(question)
        )

        candidate_indexes = [
            i
            for i, doc in enumerate(self.documents)
            if self._allowed(doc, categories)
        ]

        ranked = sorted(
            candidate_indexes,
            key=lambda i: float(scores[i]),
            reverse=True,
        )

        return [
            self.documents[i]
            for i in ranked
            if float(scores[i]) > 0
        ][:top_k]

    def _dense_docs(
        self,
        question: str,
        top_k: int,
        categories: list[str] | None = None,
    ) -> list[Document]:

        if not categories:
            return self.vector_store.similarity_search(
                question,
                k=top_k,
            )

        def metadata_filter(metadata: dict) -> bool:
            return (
                _metadata_category(metadata)
                in categories
            )

        # FAISS'in metadata filter destegi varsa,
        # tum indeks icinden filtrelenmis en iyi sonuclari al.
        try:
            return self.vector_store.similarity_search(
                question,
                k=top_k,
                filter=metadata_filter,
                fetch_k=len(self.documents),
            )

        except (TypeError, ValueError):
            # Surum uyumsuzlugu olursa guvenli fallback:
            # tum vektor sonuclarini sirala, sonra kategoriye gore filtrele.
            candidates = (
                self.vector_store.similarity_search(
                    question,
                    k=len(self.documents),
                )
            )

            return [
                doc
                for doc in candidates
                if self._allowed(doc, categories)
            ][:top_k]

    def retrieve(
        self,
        question: str,
        final_top_k: int | None = None,
    ) -> list[Document]:

        final_top_k = (
            final_top_k
            or settings.final_top_k
        )

        categories = self.detect_categories(question)

        dense = self._dense_docs(
            question,
            settings.vector_top_k,
            categories=categories,
        )

        sparse = self._bm25_docs(
            question,
            settings.bm25_top_k,
            categories=categories,
        )

        # Kategori siniflandirmasi cok kati kalirsa ve
        # hic sonuc bulunamazsa global retrieval'a geri don.
        if categories and not dense and not sparse:
            categories = []

            dense = self._dense_docs(
                question,
                settings.vector_top_k,
            )

            sparse = self._bm25_docs(
                question,
                settings.bm25_top_k,
            )

        scores: dict[str, float] = defaultdict(float)
        docs_by_key: dict[str, Document] = {}

        rrf_k = 60.0

        for rank, doc in enumerate(
            dense,
            start=1,
        ):
            key = _doc_key(doc)
            docs_by_key[key] = doc

            scores[key] += (
                settings.dense_weight
                / (rrf_k + rank)
            )

        for rank, doc in enumerate(
            sparse,
            start=1,
        ):
            key = _doc_key(doc)
            docs_by_key[key] = doc

            scores[key] += (
                settings.sparse_weight
                / (rrf_k + rank)
            )

        ranked_keys = sorted(
            scores,
            key=scores.get,
            reverse=True,
        )[:final_top_k]

        result = []

        for key in ranked_keys:
            doc = docs_by_key[key]

            doc.metadata["hybrid_score"] = round(
                scores[key],
                8,
            )

            doc.metadata["retrieval_category"] = (
                _metadata_category(doc.metadata)
            )

            doc.metadata["detected_categories"] = (
                categories
            )

            result.append(doc)

        return result
