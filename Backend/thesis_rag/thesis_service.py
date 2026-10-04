from __future__ import annotations

from typing import Any

from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama

from .farm_adapter import FarmDataService
from .farm_context import current_farm_id
from .query_router import QueryRouter
from .rag_chain import RAGService
from .safety import (
    VETERINARY_DISCLAIMER,
    ensure_veterinary_disclaimer,
    is_diagnosis_or_treatment_request,
    refuse_diagnosis_answer,
)
from .settings import settings


class ThesisAssistantService:
    """SQL + Hybrid RAG + LangChain router orkestrasyonu."""

    def __init__(self):
        self.router = QueryRouter()
        self.rag = RAGService()
        self.farm = FarmDataService()
        self.local_llm = ChatOllama(
            model=settings.rag_llm,
            temperature=settings.llm_temperature,
            base_url=settings.ollama_base_url,
            seed=settings.llm_seed,
            num_predict=settings.llm_num_predict,
            num_ctx=settings.llm_num_ctx,
        )
        self.hybrid_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        """Sen hayvancılık karar-destek asistanısın.

Elinde iki ayrı veri türü vardır:

1. ÇİFTLİK VERİSİ:
Kullanıcının kendi PostgreSQL kayıtlarından elde edilmiştir.
Bu verilerde bulunan isim, tarih, süt miktarı, yüzde değişim, alarm ve diğer sayısal değerleri AYNEN kullan.
Çiftlik verisinde bulunmayan bir sayıyı veya olayı uydurma.

2. KAYNAK BAĞLAMI:
RAG sistemi tarafından güvenilir dokümanlardan getirilen bilgidir.
Dokümanlardan gelen her sağlık veya teknik iddianın sonunda mutlaka [K1], [K2] gibi kaynak etiketi kullan.

YANIT KURALLARI:
- HER ZAMAN TÜRKÇE cevap ver.
- Önce çiftlik kayıtlarında görülen SOMUT BULGUYU açıkla.
- Çiftlik verisinde sayısal değer varsa mutlaka cevaba dahil et.
- Sonra bu bulgunun olası nedenlerini yalnızca KAYNAK BAĞLAMI üzerinden açıkla.
- Kaynakta geçmeyen hastalık, stres, besleme problemi veya başka bir nedeni uydurma.
- Çiftlik alarm mesajında bir ihtimal yazıyor fakat RAG kaynağı bunu desteklemiyorsa, bunu kesin neden gibi sunma.
- Süt verimindeki düşüşü tek başına hastalık tanısı olarak yorumlama.
- Kesin veteriner tanısı koyma.
- Antibiyotik, ilaç veya doz önerme.
- Gerektiğinde veteriner hekim değerlendirmesi öner.
- Kaynak etiketlerini yalnızca KAYNAK BAĞLAMI içindeki etiketlerden kullan.
- Kısa, açık ve bilimsel olarak temkinli yanıt ver.
- Kullanıcı sorusunda geçen hayvan ismi kullanıcı adı değildir. Hayvan adına "Merhaba" diye hitap etme.
- ÇİFTLİK VERİSİNDE bulunan mastitis, stres veya başka bir olası neden ifadesini bilimsel gerçek kabul etme. Sağlıkla ilgili nedenleri yalnızca KAYNAK BAĞLAMI üzerinden açıkla.

Yanıt düzeni:
1. Çiftlik verisindeki bulgu
2. Kaynaklara göre olası açıklama
3. Kısa değerlendirme / öneri
""",
    ),
    (
        "human",
        """KULLANICI SORUSU:
{question}

ÇİFTLİK VERİSİ:
{farm_context}

KAYNAK BAĞLAMI:
{rag_context}

Birleştirilmiş yanıt:""",
    ),
])
        self.hybrid_chain = self.hybrid_prompt | self.local_llm
        self.chat_prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                "Sen süt sığırcılığı alanında çalışan kısa sohbet asistanısın. "
                "HER ZAMAN TÜRKÇE cevap ver. Tanı koyma, antibiyotik veya ilaç önerme. "
                "Kullanıcının selamına veya kısa sohbetine doğal, kısa ve yardımsever yanıt ver.",
            ),
            ("human", "{question}"),
        ])
        self.chat_chain = self.chat_prompt | self.local_llm

    @staticmethod
    def _knowledge_query(question: str) -> str:
        return (
            f"{question}\n\n"
            "Sorunun bilimsel kısmını genel süt sığırcılığı kaynaklarına göre yanıtla. "
            "Belirli bir hayvana kesin tanı koyma. Antibiyotik veya ilaç dozu önerme."
        )

    def _farm_finding(
        self,
        question: str,
        ciftlik_id: int | None,
    ) -> tuple[str, dict | None]:
        farm_data = self.farm.get_latest_milk_drop(
            question=question,
            ciftlik_id=ciftlik_id,
        )
        if farm_data:
            sagim_zamani = (
                "akşam"
                if farm_data["sagim_zamani"] == "e"
                else "sabah"
            )
            tarih = farm_data["tarih"].strftime("%d.%m.%Y")
            eski_ortalama = (
                f'{farm_data["eski_ortalama"]:.2f}'.replace(".", ",")
            )
            son_verim = (
                f'{farm_data["son_verim"]:.2f}'.replace(".", ",")
            )
            dusus_yuzdesi = (
                f'{farm_data["dusus_yuzdesi"]:.2f}'.replace(".", ",")
            )
            farm_answer = (
                f'Çiftlik kayıtlarına göre {farm_data["isim"]} '
                f'({farm_data["kupe_no"]}) için {tarih} tarihli '
                f'{sagim_zamani} sağımında süt verimi, '
                f'önceki sağım ortalaması olan {eski_ortalama} litreden '
                f'{son_verim} litreye düşmüştür. '
                f'Bu değişim yaklaşık %{dusus_yuzdesi} oranında '
                f'bir süt verimi düşüşüne karşılık gelmektedir.'
            )
            return farm_answer, farm_data

        farm_context = self.farm.raw_context(question)
        return farm_context, None

    def _hybrid_answer(
        self,
        question: str,
        ciftlik_id: int | None,
    ) -> dict[str, Any]:
        farm_answer, farm_data = self._farm_finding(question, ciftlik_id)
        rag_result = self.rag.answer(self._knowledge_query(question))
        cow_name = farm_data["isim"] if farm_data else "ilgili hayvan"

        answer = (
            f"{farm_answer}\n\n"
            f"Kaynaklara göre genel değerlendirme:\n"
            f"{rag_result['answer']}\n\n"
            f"Bu kaynak bilgileri {cow_name} için kesin bir neden veya tanı "
            f"göstermez. Süt verimindeki değişimin nedeni, diğer klinik "
            f"bulgular ve hayvanın genel durumu birlikte değerlendirilerek "
            f"belirlenmelidir.\n\n"
            f"{VETERINARY_DISCLAIMER}"
        )
        return {
            "route": "HYBRID",
            "answer": answer,
            "sources": rag_result.get("sources", []),
        }

    def ask(
        self,
        question: str,
        ciftlik_id: int | None = None,
        include_debug: bool = False,
    ) -> dict[str, Any]:
        token = current_farm_id.set(ciftlik_id)
        try:
            route = self.router.classify(question)

            if (
                is_diagnosis_or_treatment_request(question)
                and route != "CHAT"
            ):
                result = {
                    "route": route,
                    "answer": refuse_diagnosis_answer(),
                    "sources": [],
                }
            elif route == "SQL":
                answer = self.farm.answer(question)
                result = {
                    "route": route,
                    "answer": answer,
                    "sources": [],
                }
            elif route == "RAG":
                rag_result = self.rag.answer(question)
                result = {
                    "route": route,
                    "answer": ensure_veterinary_disclaimer(
                        rag_result.get("answer", "")
                    ),
                    "sources": rag_result.get("sources", []),
                }
            elif route == "HYBRID":
                result = self._hybrid_answer(question, ciftlik_id)
            else:
                response = self.chat_chain.invoke({"question": question})
                result = {
                    "route": "CHAT",
                    "answer": str(response.content),
                    "sources": [],
                }

            if include_debug:
                result["debug"] = {
                    "ciftlik_id": ciftlik_id,
                    "fusion_method": settings.fusion_method,
                    "dense_weight": settings.dense_weight,
                    "sparse_weight": settings.sparse_weight,
                }
            return result
        finally:
            current_farm_id.reset(token)
