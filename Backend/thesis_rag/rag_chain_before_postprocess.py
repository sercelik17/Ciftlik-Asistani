from __future__ import annotations
import json
import re

from dataclasses import dataclass
from typing import Any

from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama

from .hybrid_retriever import HybridRetriever
from .settings import settings


@dataclass
class SourceItem:
    id: str
    title: str
    page: int | None
    chunk_id: str | None
    score: float | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "page": self.page,
            "chunk_id": self.chunk_id,
            "score": self.score,
        }


class RAGService:
    def __init__(self):
        self.retriever = HybridRetriever()
        self.llm = ChatOllama(
            model=settings.rag_llm,
            temperature=0.0,
            base_url=settings.ollama_base_url,
            num_predict=320,
            num_ctx=4096,
            keep_alive="30m",
        )
        self.prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                """Sen süt sığırcılığı alanında çalışan kaynak-temelli bir yapay zekâ danışmanısın.

SADECE verilen KAYNAK BAĞLAMI içindeki bilgileri kullan.

KURALLAR:
- HER ZAMAN TÜRKÇE cevap ver.
- Kullanıcının sorusuna doğrudan cevap ver.
- En fazla 3 kısa ve açık bilimsel bulgu yaz.
- Gereksiz ekonomik, tarihsel veya genel bilgilere girme.
- Sorunun konusu süt verimiyse süt verimine odaklan.
- Sorunun konusu süt kalitesiyse süt kalitesine odaklan.
- Neden-sonuç ilişkisini kaynakta açıkça belirtilmedikçe uydurma.
- Kesin hastalık tanısı koyma.
- Kaynakta bulunmayan bilgi ekleme.
- Her bilimsel bulgunun sonunda onu destekleyen kaynak kimliğini [K1], [K2] gibi yaz.
- Yalnızca KAYNAK BAĞLAMI içinde verilen K1, K2, K3 gibi kaynak kimliklerini kullan.
- JSON, XML, Python sözlüğü veya kod bloğu üretme.
- "response", "content", "source", "id", "claims" gibi yapısal alan adları kullanma.
- Kaynak yetersizse açıkça: "Mevcut kaynaklarda bu soruyu güvenilir biçimde yanıtlayacak yeterli bilgi bulunamadı." de.

YANIT BİÇİMİ:
Doğrudan normal Türkçe metin yaz.

Örnek:
Mastitis, süt veriminde azalmaya neden olabilir. [K1]
Subklinik olgularda belirgin klinik bulgular görülmeyebilir ve somatik hücre sayısı gibi dolaylı göstergelerden yararlanılabilir. [K2]"""
            ),
            (
                "human",
                """SORU:
{question}

KAYNAK BAĞLAMI:
{context}

Yalnızca yukarıdaki kaynak bağlamına dayanarak Türkçe cevap ver."""
            ),
        ])

        self.chain = self.prompt | self.llm

    @staticmethod
    def format_context(docs: list[Document]) -> tuple[str, list[SourceItem]]:
        blocks = []
        sources: list[SourceItem] = []
        for i, doc in enumerate(docs, start=1):
            source_id = f"K{i}"
            title = str(doc.metadata.get("source_name") or doc.metadata.get("source_stem") or "Kaynak")
            page = doc.metadata.get("page_number")
            header = f"[{source_id}] {title}"
            if page:
                header += f", s. {page}"
            blocks.append(f"{header}\n{doc.page_content.strip()}")
            sources.append(SourceItem(
                id=source_id,
                title=title,
                page=int(page) if page is not None else None,
                chunk_id=doc.metadata.get("chunk_id"),
                score=doc.metadata.get("hybrid_score"),
            ))
        return "\n\n---\n\n".join(blocks), sources


    @staticmethod
    def _is_relevant_claim(question: str, claim_text: str) -> bool:
        """
        Üretilen iddianın kullanıcı sorusuyla ilgili olup
        olmadığını deterministik olarak kontrol eder.
        """

        stopwords = {
            "nasıl", "nedir", "neden", "niçin",
            "ne", "ile", "ve", "veya", "bir",
            "bu", "şu", "için", "olarak",
            "etkiler", "etkiler?", "etkisi",
        }

        def get_tokens(text: str) -> set[str]:
            tokens = re.findall(
                r"[a-zA-ZçğıöşüÇĞİÖŞÜ]+",
                text.casefold()
            )

            result = set()

            for token in tokens:
                if token in stopwords:
                    continue

                if len(token) > 5:
                    token = token[:5]

                result.add(token)

            return result

        question_tokens = get_tokens(question)
        claim_tokens = get_tokens(claim_text)

        if not question_tokens:
            return True

        overlap = len(question_tokens & claim_tokens)

        required_overlap = 1 if len(question_tokens) <= 2 else 2

        return overlap >= required_overlap


    @staticmethod
    def _is_duplicate_claim(
        new_text: str,
        existing_texts: list[str]
    ) -> bool:
        """
        Daha önce kabul edilmiş bir iddiayla çok benzer olan
        yeni iddiaları filtreler.
        """

        def tokens(text: str) -> set[str]:
            words = re.findall(
                r"[a-zA-ZçğıöşüÇĞİÖŞÜ]+",
                text.casefold()
            )

            return {
                word[:5] if len(word) > 5 else word
                for word in words
                if len(word) >= 3
            }

        new_tokens = tokens(new_text)

        for existing in existing_texts:
            existing_tokens = tokens(existing)

            if not new_tokens or not existing_tokens:
                continue

            similarity = (
                len(new_tokens & existing_tokens)
                / len(new_tokens | existing_tokens)
            )

            if similarity >= 0.50:
                return True

        return False

    @staticmethod
    def _matches_effect_target(question: str, claim_text: str) -> bool:
        """
        'X, Y'yi nasıl etkiler?' türü sorularda,
        iddianın sorulan hedef değişkeni gerçekten içerip
        içermediğini kontrol eder.
        """

        q = question.casefold()
        claim = claim_text.casefold()

        match = re.search(
            r"([a-zA-ZçğıöşüÇĞİÖŞÜ]+\s+[a-zA-ZçğıöşüÇĞİÖŞÜ]+)\s+nasıl\s+etkiler",
            q
        )

        if not match:
            return True

        target_phrase = match.group(1)

        target_words = re.findall(
            r"[a-zA-ZçğıöşüÇĞİÖŞÜ]+",
            target_phrase
        )

        target_stems = {
            word[:5] if len(word) > 5 else word
            for word in target_words
        }

        claim_words = re.findall(
            r"[a-zA-ZçğıöşüÇĞİÖŞÜ]+",
            claim
        )

        claim_stems = {
            word[:5] if len(word) > 5 else word
            for word in claim_words
        }

        return bool(target_stems & claim_stems)


    @staticmethod
    def _has_question_anchor(question: str, claim_text: str) -> bool:
        """
        İddianın, sorunun ana konusunu gerçekten içerip
        içermediğini kontrol eder.

        Örnek:
        'Yetersiz kuru madde tüketimi süt verimini nasıl etkiler?'
        sorusunda yalnızca 'süt verimi' demek yeterli değildir.
        İddiada kuru madde tüketimiyle ilgili ana kavramlardan
        en az biri de bulunmalıdır.
        """

        generic_stems = {
            "nasıl",
            "nedir",
            "neden",
            "niçin",
            "hangi",
            "daha",
            "için",
            "ile",
            "ve",
            "veya",
            "bir",
            "süt",
            "inek",
            "inekl",
            "sığır",
            "hayva",
            "verim",
            "kalit",
            "etkil",
            "etkis",
            "olabi",
            "olara",
        }

        def get_tokens(text: str) -> set[str]:
            words = re.findall(
                r"[a-zA-ZçğıöşüÇĞİÖŞÜ]+",
                text.casefold()
            )

            result = set()

            for word in words:
                stem = word[:5] if len(word) > 5 else word

                if len(stem) < 3:
                    continue

                if stem in generic_stems:
                    continue

                result.add(stem)

            return result

        question_anchors = get_tokens(question)
        claim_tokens = get_tokens(claim_text)

        if not question_anchors:
            return True

        return bool(question_anchors & claim_tokens)

    def retrieve(self, question: str) -> tuple[str, list[SourceItem]]:
        # Önce daha geniş bir aday havuzu getir.
        candidates = self.retriever.retrieve(
            question,
            final_top_k=10,
        )

        selected: list[Document] = []
        source_counts: dict[str, int] = {}

        # Aynı PDF'den en fazla 2 chunk seç.
        for doc in candidates:
            source_name = str(
                doc.metadata.get("source_name")
                or doc.metadata.get("source_stem")
                or "Kaynak"
            )

            current_count = source_counts.get(source_name, 0)

            if current_count >= 2:
                continue

            selected.append(doc)
            source_counts[source_name] = current_count + 1

            if len(selected) >= 5:
                break

        return self.format_context(selected)

    def answer(self, question: str) -> dict[str, Any]:
        context, sources = self.retrieve(question)

        if not context.strip():
            return {
                "answer": (
                    "Bilgi taban\u0131nda bu soruyu g\u00fcvenilir bi\u00e7imde "
                    "yan\u0131tlayacak yeterli kaynak bulamad\u0131m."
                ),
                "sources": [],
            }

        try:
            response = self.chain.invoke(
                {
                    "question": question,
                    "context": context,
                }
            )

            answer_text = str(response.content).strip()

            if not answer_text:
                return {
                    "answer": (
                        "Mevcut kaynaklarda bu soruyu yan\u0131tlamak i\u00e7in "
                        "yeterli bilgi bulunamad\u0131."
                    ),
                    "sources": [],
                }

            valid_source_ids = {source.id for source in sources}

            cited_ids = set(
                re.findall(r"\[(K\d+)\]", answer_text)
            )

            used_source_ids = cited_ids.intersection(valid_source_ids)

            if not used_source_ids:
                used_source_ids = valid_source_ids

            def clean_invalid_citation(match):
                source_id = match.group(1)

                if source_id in valid_source_ids:
                    return match.group(0)

                return ""

            answer_text = re.sub(
                r"\[(K\d+)\]",
                clean_invalid_citation,
                answer_text,
            )

            answer_text = re.sub(r"[ \t]+", " ", answer_text)
            answer_text = re.sub(r"\n{3,}", "\n\n", answer_text).strip()

            return {
                "answer": answer_text,
                "sources": [
                    source.as_dict()
                    for source in sources
                    if source.id in used_source_ids
                ],
            }

        except Exception as e:
            return {
                "answer": (
                    "Kaynak-temelli cevap olu\u015fturulurken "
                    f"bir hata meydana geldi: {e}"
                ),
                "sources": [],
            }

