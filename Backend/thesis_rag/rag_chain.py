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
            num_predict=160,
            num_ctx=2048,
            num_gpu=0,
            keep_alive="5m",
        )
        self.prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                """Sen süt sığırcılığı alanında çalışan kaynak-temelli bir yapay zekâ danışmanısın.

SADECE verilen KAYNAK BAĞLAMI içindeki bilgileri kullan.

KURALLAR:
- HER ZAMAN TÜRKÇE cevap ver.
- Kaynak İngilizceyse cümleyi kelimesi kelimesine çevirme; bilimsel anlamını doğru ve doğal Türkçe ile özetle.
- İngilizce veya yarı İngilizce cümle bırakma.
- Kullanıcının sorusuna doğrudan cevap ver.
- Cevap en fazla 3 kısa ve tam cümleden oluşsun.
- Her cümle kullanıcının sorusunu doğrudan yanıtlasın.
- Soruda hangi sonuç değişkeni soruluyorsa yalnızca ona odaklan.
- Süt verimi sorusunda süt kalitesi, ekonomik kayıp, sürüden çıkarılma veya başka sonuçları gereksiz yere ekleme.
- Süt kalitesi sorusunda yalnızca süt veriminin azalmasından söz etmek yeterli değildir; süt kalitesi üzerindeki etkiyi açıkça belirt.
- Cevaba 'Bu durumda', 'Ayrıca' veya benzeri bağlamsız ifadelerle başlama.
- Soru ekonomik kayıplarla ilgili değilse ekonomik kayıp, prim veya rekabet bilgisini ekleme.
- Ayrı bir 'Kaynaklar:' bölümü oluşturma.
- Gereksiz ekonomik, tarihsel veya genel bilgilere girme.
- Sorunun konusu süt verimiyse süt verimine odaklan.
- Sorunun konusu süt kalitesiyse süt kalitesine odaklan.
- Neden-sonuç ilişkisini kaynakta açıkça belirtilmedikçe uydurma.
- Kesin hastalık tanısı koyma.
- Kaynakta bulunmayan bilgi ekleme.
- İngilizce teknik terimleri şu anlamlarla kullan: calving = buzağılama/doğum; calf = buzağı; antibody = antikor; immunoglobulin = immünoglobulin; colostrum = kolostrum/ağız sütü; body condition score = vücut kondisyon skoru; reproductive = üreme ile ilgili; embryo = embriyo; lameness = topallık; milking personnel = sağım personeli; teat = meme başı; udder = meme; cow = inek.
- antibody kelimesini antibiyotik, calf kelimesini kuzu, cow veya milking personnel ifadelerini kadın olarak çevirme.
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

    def _postprocess_answer(
        self,
        question: str,
        raw_text: str,
        valid_source_ids: set[str],
    ) -> tuple[str, set[str]]:

        text = str(raw_text or "").replace("\r", "\n").strip()

        # Model ayrica Kaynaklar: bolumu yazmissa kaldir.
        text = re.split(
            r"\n\s*Kaynaklar\s*:",
            text,
            maxsplit=1,
            flags=re.IGNORECASE,
        )[0].strip()

        # (K1, s. 2) veya (K1, s. 2, K3, s. 3) -> [K1][K3]
        def normalize_parenthetical(match):
            inside = match.group(1)

            ids = []
            for source_id in re.findall(r"\b(K\d+)\b", inside):
                if source_id in valid_source_ids and source_id not in ids:
                    ids.append(source_id)

            if ids:
                return " " + "".join(
                    f"[{source_id}]"
                    for source_id in ids
                )

            return match.group(0)

        text = re.sub(
            r"\(([^()\n]*\bK\d+\b[^()\n]*)\)",
            normalize_parenthetical,
            text,
        )

        # K1, s. 2 -> [K1]
        text = re.sub(
            r"\b(K\d+)\s*,?\s*s\.\s*\d+\b",
            r"[\1]",
            text,
            flags=re.IGNORECASE,
        )

        # "Cumle. [K1]" -> "Cumle [K1]."
        text = re.sub(
            r"([.!?])\s*((?:\[(?:K\d+)\][,\s]*)+)",
            lambda m: (
                " "
                + "".join(
                    f"[{source_id}]"
                    for source_id in dict.fromkeys(
                        source_id
                        for source_id in re.findall(
                            r"K\d+",
                            m.group(2),
                        )
                        if source_id in valid_source_ids
                    )
                )
                + m.group(1)
                + " "
            ),
            text,
        )

        # Gecersiz K99 vb. atiflari temizle.
        def clean_invalid_citation(match):
            source_id = match.group(1)
            return (
                match.group(0)
                if source_id in valid_source_ids
                else ""
            )

        text = re.sub(
            r"\[(K\d+)\]",
            clean_invalid_citation,
            text,
        )

        candidates = re.split(
            r"(?<=[.!?])\s+|\n+",
            text,
        )

        q = question.lower()

        asks_economy = "ekonom" in q or "maliyet" in q
        asks_quality = "kalite" in q
        asks_yield = "verim" in q or "üretim" in q

        asks_subclinical_detection = (
            "subklinik" in q
            and (
                "fark" in q
                or "tespit" in q
                or "zor" in q
            )
        )

        accepted = []
        accepted_plain = []
        used_source_ids: set[str] = set()

        for candidate in candidates:
            candidate = candidate.strip(" \t-*?")

            if not candidate:
                continue

            lowered = candidate.lower()

            # Kaynakta açıkça desteklenmeyen derece ifadelerini temizle.
            candidate = re.sub(
                r"\b(hafifçe|hafifce|çok ciddi|ciddi biçimde|ciddi şekilde)\b",
                "",
                candidate,
                flags=re.IGNORECASE,
            )

            candidate = re.sub(r"[ \t]+", " ", candidate).strip()

# Kalite sorusunda ekonomik sonuç kısmını kes.
            if asks_quality and not asks_economy:
                candidate = re.sub(
                r"\s+ve\s+buna\s+bağlı\s+olarak\s+da\s+.*$",
                "",
                candidate,
                flags=re.IGNORECASE,
            ).strip()

# Verim sorusunda gereksiz kalite uzantısını kes.
            if asks_yield and not asks_quality:
                candidate = re.sub(
                r"\s+ve\s+sütün\s+kalitesini.*$",
                "",
                candidate,
                flags=re.IGNORECASE,
            ).strip()

            candidate = re.sub(
                r"^(?:Ayr\u0131ca|Bu durumda|Bunun yan\u0131nda)\\s*,?\\s*",
                "",
                candidate,
                flags=re.IGNORECASE,
            ).strip()

            # Temizliklerden sonra guncel metinle tekrar hesapla.
            lowered = candidate.casefold()

            # Model kaynak basligini cevap gibi tekrar etmesin.
            if lowered.startswith(("kaynak:", "source:")):
                continue

            # JSON/artifact kalintilari.
            if any(
                token in lowered
                for token in [
                    '"response"',
                    '"content"',
                    '"source"',
                    '"claims"',
                ]
            ):
                continue

            citation_ids = [
                source_id
                for source_id in re.findall(
                    r"\[(K\d+)\]",
                    candidate,
                )
                if source_id in valid_source_ids
            ]

            citation_ids = list(dict.fromkeys(citation_ids))

            plain = re.sub(
                r"\[(K\d+)\]",
                "",
                candidate,
            ).strip(" ,.;:")

            # Sadece kaynak etiketi olan satirlari alma.
            if len(plain) < 20 or not citation_ids:
                continue

            # Ekonomi sorulmadiysa ekonomi odakli cumleleri cikart.
            if not asks_economy and any(
                term in lowered
                for term in [
                    "ekonomik kay",
                    "kaybettikleri prim",
                    "rekabet",
                    "maliyetli hastal",
                    "ekonomik getir",
                ]
            ):
                continue

            # Subklinik mastitiste SHS bir tanisal gostergedir;
            # "fark edilmesinin nedeni" gibi yazilmasini engelle.
            if asks_subclinical_detection:
                marker_pattern = (
                    r"(?:somatik|so\s*matik|shs|h\u00fccre)"
                )

                wrong_causality = (
                    re.search(marker_pattern, lowered)
                    and "nedeniyle" in lowered
                    and (
                        "fark edilmesi zor" in lowered
                        or "tespit edilmesi zor" in lowered
                    )
                )

                if wrong_causality:
                    continue

            # Kalite sorusunda tamamen ilgisiz cumleleri alma.
            if asks_quality:
                quality_terms = [
                    "kalite",
                    "raf ömr",
                    "lezzet",
                    "yağ",
                    "protein",
                    "laktoz",
                    "kuru madde",
                    "süt ürün",
                    "bileşim",
                ]

                if not any(term in lowered for term in quality_terms):
                    continue

            # Verim sorusunda tamamen ilgisiz cumleleri alma.
            elif asks_yield:
                yield_terms = [
                    "verim",
                    "üretim",
                    "azal",
                    "düş",
                    "kayıp",
                ]

                if not any(term in lowered for term in yield_terms):
                    continue

            if self._is_duplicate_claim(
                plain,
                accepted_plain,
            ):
                continue

            # Tek cumlede en fazla iki kaynak goster.
            kept_ids = citation_ids[:2]

            # Eski atiflari kaldir.
            clean_plain = re.sub(
                r"\[(K\d+)\]",
                "",
                candidate,
            ).strip()

            punctuation = "."

            if clean_plain.endswith(("!", "?")):
                punctuation = clean_plain[-1]
                clean_plain = clean_plain[:-1].rstrip()
            elif clean_plain.endswith("."):
                clean_plain = clean_plain[:-1].rstrip()

            rendered = (
                clean_plain
                + " "
                + "".join(
                    f"[{source_id}]"
                    for source_id in kept_ids
                )
                + punctuation
            )

            accepted.append(rendered)
            accepted_plain.append(plain)
            used_source_ids.update(kept_ids)

            if len(accepted) >= 3:
                break

        # Cok kati filtre nedeniyle hicbir sey kalmazsa:
        # kaynakli ilk anlamli cumleyi koru.
        if not accepted:
            for candidate in candidates:
                candidate = candidate.strip(" \t-*?")

                citation_ids = [
                    source_id
                    for source_id in re.findall(
                        r"\[(K\d+)\]",
                        candidate,
                    )
                    if source_id in valid_source_ids
                ]

                citation_ids = list(dict.fromkeys(citation_ids))

                plain = re.sub(
                    r"\[(K\d+)\]",
                    "",
                    candidate,
                ).strip(" ,.;:")

                if len(plain) < 20 or not citation_ids:
                    continue

                fallback_lowered = plain.casefold()

                # Ekonomi sorulmadiysa ekonomi cumlesini alma.
                if not asks_economy and "ekonom" in fallback_lowered:
                    continue

                if asks_quality:
                    quality_fallback_terms = [
                        "kalite",
                        "bile\u015fim",
                        "protein",
                        "ya\u011f",
                        "laktoz",
                        "raf \u00f6mr",
                        "teknolojik",
                        "i\u015flen",
                    ]

                    if not any(
                        term in fallback_lowered
                        for term in quality_fallback_terms
                    ):
                        continue

                if asks_yield:
                    yield_fallback_terms = [
                        "verim",
                        "\u00fcretim",
                        "azal",
                        "d\u00fc\u015f",
                        "kay\u0131p",
                    ]

                    if not any(
                        term in fallback_lowered
                        for term in yield_fallback_terms
                    ):
                        continue

                kept_ids = citation_ids[:2]

                clean_plain = re.sub(
                    r"\[(K\d+)\]",
                    "",
                    candidate,
                ).strip().rstrip(".")

                rendered = (
                    clean_plain
                    + " "
                    + "".join(
                        f"[{source_id}]"
                        for source_id in kept_ids
                    )
                    + "."
                )

                accepted.append(rendered)
                used_source_ids.update(kept_ids)
                break

        if not accepted:
            return (
                "Mevcut kaynaklardan soruya yeterince "
                "g\u00fcvenilir ve kaynakland\u0131r\u0131lm\u0131\u015f "
                "bir yan\u0131t olu\u015fturulamad\u0131.",
                set(),
            )

        return "\n".join(accepted).strip(), used_source_ids


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

            valid_source_ids = {source.id for source in sources}

            answer_text, used_source_ids = self._postprocess_answer(
                question=question,
                raw_text=str(response.content),
                valid_source_ids=valid_source_ids,
            )

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

