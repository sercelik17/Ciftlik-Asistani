from __future__ import annotations

from langchain_core.messages import AIMessage, HumanMessage


class FarmDataService:
    """Mevcut Süt Sihirbazı LangGraph ajanını tez router'ına bağlayan adaptör.

    Not: Orijinal tool_rag.py çok-kiracılı (multi-tenant) ciftlik_id filtrelemesini
    tüm sorgularda garanti etmiyor. Tez prototipinde tek çiftlik verisiyle kullanılabilir;
    gerçek çok kullanıcılı dağıtım öncesinde SQL araçları ciftlik_id ile sınırlandırılmalıdır.
    """

    def __init__(self):
        from tool_rag import toolrag_app
        self.app = toolrag_app

    def answer(self, question: str) -> str:
        result = self.app.invoke({"messages": [HumanMessage(content=question)]})
        messages = result.get("messages", [])
        for msg in reversed(messages):
            if isinstance(msg, AIMessage) and msg.content:
                return str(msg.content)
        return "Çiftlik verisinden yanıt üretilemedi."
