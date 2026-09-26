from __future__ import annotations

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
            temperature=0.1,
            base_url=settings.ollama_base_url,
        )
        self.prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                """Sen hayvancılık alanında çalışan kaynak-temelli bir yapay zekâ asistanısın.
Yalnızca verilen KAYNAK BAĞLAMI içindeki bilgilerden olgusal sonuç çıkar.
Bağlamda yeterli bilgi yoksa bunu açıkça söyle; modelin genel bilgisinden uydurma bilgi ekleme.
Her önemli iddianın sonunda ilgili kaynak etiketini [K1], [K2] biçiminde kullan.
Kaynak etiketlerini asla uydurma ve bağlamda olmayan bir kaynağı belirtme.
Sağlık sorularında kesin tanı koyma; bulguların veteriner hekim değerlendirmesi gerektirebileceğini belirt.
Yanıt Türkçe, anlaşılır ve çiftçinin okuyabileceği sadelikte olsun.""",
            ),
            (
                "human",
                """SORU:
{question}

KAYNAK BAĞLAMI:
{context}

Kaynaklara dayalı yanıt:""",
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

    def retrieve(self, question: str) -> tuple[str, list[SourceItem]]:
        docs = self.retriever.retrieve(question)
        return self.format_context(docs)

    def answer(self, question: str) -> dict[str, Any]:
        context, sources = self.retrieve(question)
        if not context.strip():
            return {
                "answer": "Bilgi tabanında bu soruyu güvenilir biçimde yanıtlayacak yeterli kaynak bulamadım.",
                "sources": [],
            }
        response = self.chain.invoke({"question": question, "context": context})
        return {
            "answer": response.content,
            "sources": [source.as_dict() for source in sources],
        }
