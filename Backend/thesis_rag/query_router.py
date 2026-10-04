from __future__ import annotations

import re

from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama

from .route_rules import Route, deterministic_route
from .settings import settings


class QueryRouter:
    def __init__(self):
        self.llm = ChatOllama(
            model=settings.router_llm,
            temperature=0,
            base_url=settings.ollama_base_url,
            num_ctx=1024,
            num_predict=16,
            seed=settings.llm_seed,
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
'Teşekkürler' -> CHAT
'Nasılsın?' -> CHAT

Sadece etiketi döndür.""",
                ),
                ("human", "{question}"),
            ]
        )

        self.chain = self.prompt | self.llm

    @staticmethod
    def _deterministic_route(question: str) -> Route | None:
        return deterministic_route(question)

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