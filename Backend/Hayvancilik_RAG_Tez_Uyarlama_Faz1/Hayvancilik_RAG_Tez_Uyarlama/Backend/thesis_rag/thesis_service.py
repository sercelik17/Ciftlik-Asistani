from __future__ import annotations

from typing import Any

from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama

from .farm_adapter import FarmDataService
from .query_router import QueryRouter
from .rag_chain import RAGService
from .settings import settings


class ThesisAssistantService:
    """SQL + Hybrid RAG + LangChain router orkestrasyonu."""

    def __init__(self):
        self.router = QueryRouter()
        self.rag = RAGService()
        self.farm = FarmDataService()
        self.local_llm = ChatOllama(
            model=settings.rag_llm,
            temperature=0.1,
            base_url=settings.ollama_base_url,
        )
        self.hybrid_prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                """Sen hayvancılık karar-destek asistanısın.
Aşağıdaki ÇİFTLİK VERİSİ, kullanıcının kendi kayıtlarından elde edilmiştir.
KAYNAK BAĞLAMI ise güvenilir dokümanlardan retrieval ile getirilmiştir.
Bu iki veri türünü birbirinden ayırarak birlikte yorumla.
Kesin veteriner tanısı koyma. Doküman kaynaklı her önemli iddiayı [K1], [K2] biçiminde kaynaklandır.
Kaynakta bulunmayan tıbbi/teknik nedeni uydurma. Çiftlik verisini değiştirme veya hayali değer ekleme.
Türkçe, kısa fakat açıklayıcı yanıt ver.""",
            ),
            (
                "human",
                """KULLANICI SORUSU:
{question}

ÇİFTLİK VERİSİ / SQL AJAN SONUCU:
{farm_context}

KAYNAK BAĞLAMI:
{rag_context}

Birleştirilmiş yanıt:""",
            ),
        ])
        self.hybrid_chain = self.hybrid_prompt | self.local_llm

    def ask(self, question: str, ciftlik_id: int | None = None) -> dict[str, Any]:
        route = self.router.classify(question)

        if route == "SQL":
            answer = self.farm.answer(question)
            return {"route": route, "answer": answer, "sources": []}

        if route == "RAG":
            result = self.rag.answer(question)
            return {"route": route, **result}

        if route == "HYBRID":
            farm_context = self.farm.answer(question)
            rag_context, sources = self.rag.retrieve(question)
            response = self.hybrid_chain.invoke({
                "question": question,
                "farm_context": farm_context,
                "rag_context": rag_context or "Bu soru için ilgili doküman bağlamı bulunamadı.",
            })
            return {
                "route": route,
                "answer": response.content,
                "sources": [s.as_dict() for s in sources],
            }

        # CHAT
        response = self.local_llm.invoke(
            "Sen hayvancılık alanında çalışan yardımsever bir asistansın. "
            "Kullanıcının aşağıdaki kısa sohbet mesajına doğal ve kısa Türkçe cevap ver: "
            + question
        )
        return {"route": route, "answer": response.content, "sources": []}
