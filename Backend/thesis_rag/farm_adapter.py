from __future__ import annotations

import os

import psycopg2
from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

load_dotenv()


class FarmDataService:
    def __init__(self):
        self.app = None

    def _invoke(self, question: str):
        if self.app is None:
            from tool_rag import toolrag_app
            self.app = toolrag_app

        return self.app.invoke(
    {
        "messages": [
            HumanMessage(content=question)
        ]
    },
    config={
        "recursion_limit": 8
    }
    )

    def answer(self, question: str) -> str:
        """
        SQL rotasında normal LangGraph cevabını döndürür.
        """
        result = self._invoke(question)

        messages = result.get("messages", [])

        for msg in reversed(messages):
            if isinstance(msg, AIMessage) and msg.content:
                return str(msg.content)

        return "Çiftlik verisinden yanıt üretilemedi."

    def raw_context(self, question: str) -> str:
        """
        Tool sonuçlarını ham olarak döndürür.
        """
        result = self._invoke(question)

        messages = result.get("messages", [])

        tool_results = []

        for msg in messages:
            if isinstance(msg, ToolMessage):
                tool_name = getattr(msg, "name", "tool")

                tool_results.append(
                    f"ARAÇ: {tool_name}\n"
                    f"SONUÇ: {msg.content}"
                )

        if not tool_results:
            return "Çiftlik kayıtlarından ilgili veri bulunamadı."

        return "\n\n".join(tool_results)

    def get_latest_milk_drop(
        self,
        question: str,
        ciftlik_id: int | None = None,
    ) -> dict | None:
        """
        Soruda geçen inek ismini veya küpe numarasını bulur
        ve o ineğin en son süt düşüş alarmını doğrudan PostgreSQL'den getirir.

        HYBRID cevapta sayısal değerlerin LLM tarafından
        değiştirilmesini veya atlanmasını önlemek için kullanılır.
        """

        connection = psycopg2.connect(
            dbname=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            host=os.getenv("DB_HOST"),
            port=int(os.getenv("DB_PORT", "5432")),
        )

        try:
            with connection.cursor() as cursor:

                # Önce kullanıcının çiftliğindeki inekleri bul.
                if ciftlik_id is not None:
                    cursor.execute(
                        """
                        SELECT kupe_no, isim
                        FROM inekler
                        WHERE ciftlik_id = %s
                        """,
                        (ciftlik_id,),
                    )
                else:
                    cursor.execute(
                        """
                        SELECT kupe_no, isim
                        FROM inekler
                        """
                    )

                cows = cursor.fetchall()

                question_lower = question.casefold()

                selected_cow = None

                for kupe_no, isim in cows:
                    if (
                        str(kupe_no).casefold() in question_lower
                        or str(isim).casefold() in question_lower
                    ):
                        selected_cow = (kupe_no, isim)
                        break

                if selected_cow is None:
                    return None

                kupe_no, isim = selected_cow

                # İneğin en son süt düşüş alarmını getir.
                if ciftlik_id is not None:
                    cursor.execute(
                        """
                        SELECT
                            a.tarih,
                            a.sagim_zamani,
                            a.eski_ortalama,
                            a.son_verim,
                            a.dusus_yuzdesi
                        FROM alarmlar a
                        WHERE
                            a.kupe_no = %s
                            AND a.ciftlik_id = %s
                        ORDER BY a.tarih DESC, a.id DESC
                        LIMIT 1
                        """,
                        (kupe_no, ciftlik_id),
                    )
                else:
                    cursor.execute(
                        """
                        SELECT
                            a.tarih,
                            a.sagim_zamani,
                            a.eski_ortalama,
                            a.son_verim,
                            a.dusus_yuzdesi
                        FROM alarmlar a
                        WHERE a.kupe_no = %s
                        ORDER BY a.tarih DESC, a.id DESC
                        LIMIT 1
                        """,
                        (kupe_no,),
                    )

                row = cursor.fetchone()

                if row is None:
                    return None

                tarih, sagim_zamani, eski_ortalama, son_verim, dusus_yuzdesi = row

                return {
                    "kupe_no": str(kupe_no),
                    "isim": str(isim),
                    "tarih": tarih,
                    "sagim_zamani": str(sagim_zamani),
                    "eski_ortalama": float(eski_ortalama),
                    "son_verim": float(son_verim),
                    "dusus_yuzdesi": float(dusus_yuzdesi),
                }

        finally:
            connection.close()