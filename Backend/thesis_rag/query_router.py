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
            num_ctx=1024,
            num_predict=16,
            num_gpu=0,
            keep_alive="2m",
        )

        self.prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """Kullanıcının sorusunu yalnızca şu dört etiketten biriyle sınıflandır:

RAG:
Genel hayvancılık, süt sığırı sağlığı, besleme, mastitis,
ketozis, buzağı, üreme ve süt kalitesi gibi uzmanlık
bilgisini dokümanlardan gerektiren sorular.

SQL:
Kullanıcının kendi çiftliğindeki inekler, sağım kayıtları,
süt miktarı, günlük üretim, alarmlar, trendler ve sayısal
çiftlik kayıtlarıyla ilgili sorular.

HYBRID:
Hem kullanıcının çiftlik verisini hem de bilimsel/veteriner
kaynak bilgisini birlikte gerektiren sorular.

CHAT:
Selamlaşma, teşekkür veya kısa genel sohbet.

Örnekler:
'Mastitis nedir?' -> RAG
'Somatik hücre sayısı süt kalitesini nasıl etkiler?' -> RAG
'Bugün toplam kaç litre süt aldım?' -> SQL
'Süt verimi en yüksek inekleri getir' -> SQL
'Serap'ın sütü neden düştü?' -> HYBRID
'Merhaba' -> CHAT

Sadece etiketi döndür.""",
                ),
                ("human", "{question}"),
            ]
        )

        self.chain = self.prompt | self.llm

    @staticmethod
    def _deterministic_route(question: str) -> Route | None:
        q = question.casefold().strip()

        chat_terms = [
            "merhaba",
            "selam",
            "teşekkür",
            "teşekkürler",
            "sağ ol",
            "sağol",
        ]

        farm_terms = [
            "bugün",
            "dün",
            "son sağım",
            "sağım kaydı",
            "sağım kayıt",
            "ineğim",
            "ineklerim",
            "inekleri",
            "ineği",
            "inekler",
            "çiftliğim",
            "çiftlikte",
            "küpe",
            "toplam süt",
            "kaç litre",
            "alarm",
            "süt verimi en yüksek",
            "en yüksek süt",
            "en çok süt",
            "en verimli",
            "sürü ortalaması",
            "üretim trendi",
            "günlük üretim",
            "süt miktarı",
        ]

        knowledge_terms = [
            "neden",
            "olası neden",
            "nedir",
            "belirti",
            "tedavi",
            "mastitis",
            "ketozis",
            "besleme",
            "rasyon",
            "somatik",
            "hastalık",
            "sağlık",
            "üreme",
            "buzağı",
            "süt kalitesi",
            "meme sağlığı",
            "kolostrum",
            "kuru dönem",
        ]

        if (
            any(term in q for term in chat_terms)
            and len(q.split()) <= 5
        ):
            return "CHAT"

        has_farm = any(term in q for term in farm_terms)
        has_knowledge = any(
            term in q for term in knowledge_terms
        )

        if has_farm and has_knowledge:
            return "HYBRID"

        if has_farm:
            return "SQL"

        if has_knowledge:
            return "RAG"

        return None

    def classify(self, question: str) -> Route:
        deterministic = self._deterministic_route(question)

        if deterministic is not None:
            return deterministic

        try:
            response = self.chain.invoke(
                {"question": question}
            )

            raw = str(response.content).upper().strip()

            match = re.search(
                r"\b(RAG|SQL|HYBRID|CHAT)\b",
                raw,
            )

            if match:
                return match.group(1)  # type: ignore[return-value]

        except Exception as exc:
            print(
                f"[Router] LLM sınıflandırma hatası: {exc}"
            )

        return "RAG"