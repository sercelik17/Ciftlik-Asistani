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
            format="json",
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
- Kullanıcının sorusuna doğrudan cevap ver.
- Gereksiz ekonomik, tarihsel veya genel bilgiler ekleme.
- Kesin hastalık tanısı koyma.
- Kaynakta bulunmayan hiçbir bilgi ekleme.
- PDF metnindeki açık yazım ve kelime bölünme hatalarını düzelt.
- Aynı bilgiyi tekrar etme.
- 3 iddia üretmek zorunda değilsin. Soruyu doğrudan cevaplayan yalnızca
  1 veya 2 bilgi varsa sadece onları üret.
- Sırf iddia sayısını tamamlamak için dolaylı veya ilgisiz bilgi ekleme.
- "Ekonomik performans", "tedavi gideri", "sürüden çıkarma oranı",
  "hastalığın yayılması" veya "mikroorganizma türleri" kullanıcının
  sorusuyla doğrudan ilişkili değilse kesinlikle cevapta yer alma.
- Her iddia düzgün ve doğal Türkçe bir cümle olmalıdır.
- Sağlıkla ilgili ifadelerde kaynak açıkça kesin bir neden-sonuç göstermiyorsa
  "azaltabilir", "etkileyebilir" veya "ilişkili olabilir" gibi temkinli ifadeler kullan.
- Kullanıcının sorusundaki ana kavramı doğrudan açıklamayan iddia üretme.
- Her iddia için hangi kaynakların kullanıldığını belirt.
- Kullanıcı sorusunda belirtilmeyen kuru dönem, geçiş dönemi, laktasyon evresi
  veya başka özel fizyolojik durumlara ait mekanizmaları hayvanın olası nedeni
  olarak sunma.
  - Soruda bir değişkenin başka bir değişken üzerindeki etkisi soruluyorsa,
  nedensel yönü koru. Örneğin "X'in artması Y'yi nasıl etkiler?" sorusunda
  yalnızca X -> Y yönündeki sonuçları belirt. X'in neden arttığını,
  Y'nin X üzerindeki etkisini veya yalnızca X ile ilişkili başka bilgileri
  cevaba dahil etme.

- "Nasıl etkiler?" sorularında yalnızca doğrudan etki ve sonuçları yaz.
  Sorulan değişkenin nedenlerini açıklama.

- Soruyu yeniden ifade eden ancak yeni bilgi vermeyen genel cümleleri
  iddia olarak üretme.

SADECE geçerli JSON döndür.

Format tam olarak şöyledir:

{{
  "claims": [
    {{
      "text": "Bilimsel iddia",
      "sources": ["K1"]
    }}
  ]
}}

Kaynak kimlikleri yalnızca verilen K1, K2, K3 gibi kaynaklardan oluşmalıdır.
JSON dışında hiçbir metin yazma."""
    ),
    (
        "human",
        """SORU:
{question}

KAYNAK BAĞLAMI:
{context}

Soruyu doğrudan yanıtlamayan bilgileri dahil etme.
Yeterli doğrudan bilgi 2 iddia ise yalnızca 2 iddia üret.
İddia sayısını doldurmaya çalışma.
Soruda belirtilen neden-sonuç yönünü değiştirme.
Sorunun nedenlerini değil, soruda istenen etkilerini/sonuçlarını yanıtla."""
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
                    "Bilgi tabanında bu soruyu güvenilir biçimde "
                    "yanıtlayacak yeterli kaynak bulamadım."
                ),
                "sources": [],
            }

        response = self.chain.invoke(
            {
                "question": question,
                "context": context,
            }
        )

        valid_source_ids = {source.id for source in sources}

        used_source_ids = set()

        # Her durumda başlangıç değeri olsun.
        answer_text = (
            "Mevcut kaynaklarda bu soruyu yanıtlamak için "
            "yeterli bilgi bulunamadı."
        )

        try:
            data = json.loads(response.content)

            claims = data.get("claims", [])

            rendered_claims = []

            accepted_claim_texts = []

            for claim in claims:
                text = str(claim.get("text", "")).strip()

                if not text:
                    continue

                # Kullanıcı sorusuyla ilgisiz iddiaları çıkar.
                if not self._is_relevant_claim(question, text):
                    continue

                if not self._has_question_anchor(question, text):
                    continue

                if not self._matches_effect_target(question, text):
                    continue

                    # Önceden kabul edilen bir iddiayla aynı/anlamsal olarak çok benzerse atla.
                if self._is_duplicate_claim(text, accepted_claim_texts):
                    continue

                accepted_claim_texts.append(text)

                claim_sources = claim.get("sources", [])

                # Modelin uydurduğu kaynak kimliklerini engelle.
                claim_sources = [
                    source_id
                    for source_id in claim_sources
                    if source_id in valid_source_ids
                ]

                used_source_ids.update(claim_sources)

                citation = "".join(
                    f"[{source_id}]"
                    for source_id in claim_sources
                )

                if citation:
                    rendered_claims.append(
                        f"{text} {citation}"
                    )
                else:
                    rendered_claims.append(text)

                # Model daha fazla üretse bile en fazla 3 iddia kullan.
                if len(rendered_claims) >= 3:
                    break

            if rendered_claims:
                answer_text = "\n\n".join(rendered_claims)

        except json.JSONDecodeError:
            answer_text = (
                "Kaynak-temelli cevap oluşturulurken "
                "model geçerli JSON çıktısı üretemedi."
            )

        except Exception as e:
            answer_text = (
                "Kaynak-temelli cevap oluşturulurken "
                f"bir hata meydana geldi: {e}"
            )

        return {
            "answer": answer_text,
            "sources": [
                source.as_dict()
                for source in sources
                if source.id in used_source_ids
            ],
        }   