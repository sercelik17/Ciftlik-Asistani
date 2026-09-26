from __future__ import annotations

import re
from typing import Literal

from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama

from .settings import settings

Route = Literal["RAG", "SQL", "HYBRID", "CHAT"]


class QueryRouter:
    def __init__(self):
        self.llm = ChatOllama(
            model=settings.router_llm,
            temperature=0,
            base_url=settings.ollama_base_url,
        )
        self.prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                """Kullanıcının sorusunu yalnızca şu dört etiketten biriyle sınıflandır:
RAG: genel hayvancılık, süt sığırı sağlığı, besleme, mastitis, ketozis, buzağı, üreme, süt kalitesi gibi uzmanlık bilgisini dokümandan gerektiren soru.
SQL: kullanıcının kendi çiftliğindeki inek, sağım, alarm, günlük üretim, trend veya sayısal kayıtları soran soru.
HYBRID: hem kullanıcının çiftlik verisini hem de hayvancılık/veteriner kaynak bilgisini birlikte gerektiren soru.
CHAT: yalnızca selamlaşma, teşekkür veya alan dışı küçük sohbet.

Örnekler:
'Mastitis nedir?' -> RAG
'Bugün toplam kaç litre süt aldım?' -> SQL
'Sütü en fazla düşen ineğin olası nedenleri nelerdir?' -> HYBRID
'Merhaba' -> CHAT

Sadece etiketi döndür.""",
            ),
            ("human", "{question}"),
        ])
        self.chain = self.prompt | self.llm

    @staticmethod
    def _fallback(question: str) -> Route:
        q = question.lower()
        farm_terms = [
            "bugün", "dün", "son sağım", "ineğim", "ineklerim", "çiftliğim", "küpe",
            "toplam süt", "kaç litre", "alarm", "verim", "trend", "en çok süt",
        ]
        knowledge_terms = [
            "neden", "olası", "nedir", "belirti", "tedavi", "mastitis", "ketozis",
            "besleme", "rasyon", "somatik", "hastalık", "sağlık", "üreme", "buzağı",
        ]
        has_farm = any(t in q for t in farm_terms)
        has_knowledge = any(t in q for t in knowledge_terms)
        if has_farm and has_knowledge:
            return "HYBRID"
        if has_farm:
            return "SQL"
        if has_knowledge:
            return "RAG"
        if any(t in q for t in ["merhaba", "selam", "teşekkür", "sağ ol"]):
            return "CHAT"
        return "RAG"

    def classify(self, question: str) -> Route:
        try:
            raw = str(self.chain.invoke({"question": question}).content).upper().strip()
            match = re.search(r"\b(RAG|SQL|HYBRID|CHAT)\b", raw)
            if match:
                return match.group(1)  # type: ignore[return-value]
        except Exception:
            pass
        return self._fallback(question)
