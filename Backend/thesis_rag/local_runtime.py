from __future__ import annotations

import json
import os
import re
from typing import Any

import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import RealDictCursor

load_dotenv()

from thesis_eval.eval_retriever import TorchFreeRetriever, _post_json
from thesis_rag.farm_adapter import FarmDataService
from thesis_rag.farm_context import current_farm_id, farm_sql_clause
from thesis_rag.route_rules import deterministic_route, _normalize
from thesis_rag.answer_cleanup import finish_answer
from thesis_rag.chunk_filter import is_low_value_chunk
from thesis_rag.safety import (
    VETERINARY_DISCLAIMER,
    ensure_veterinary_disclaimer,
    is_diagnosis_or_treatment_request,
    refuse_diagnosis_answer,
)

RAG_SYSTEM = (
    "Sen süt sığırcılığı alanında kaynak-temelli bir danışmansın. "
    "Yalnızca verilen kaynak bağlamını kullan. Her zaman Türkçe yaz. "
    "3 veya 4 tam cümle kur; cümleyi yarıda kesme. "
    "Soruyu doğrudan yanıtla. Kaynakta yoksa 'Bu sorunun yanıtı verilen "
    "kaynaklarda yok.' yaz, uydurma. İngilizce sözcük bırakma. "
    "Tanı koyma, antibiyotik veya doz önerme. "
    "Her bilimsel cümlenin sonunda [K1] veya [K2] yaz."
)
from thesis_rag.settings import settings
from thesis_rag.sql_guard import reject_unsafe_sql

SCHEMA = """
inekler(kupe_no TEXT, isim TEXT, irk TEXT, dogum_tarihi DATE, ciftlik_id INT)
sagim_kayitlari(kupe_no TEXT, tarih DATE, sagim_zamani TEXT, sut_miktari NUMERIC, ciftlik_id INT)
  sagim_zamani: 'm' sabah, 'e' aksam
alarmlar(kupe_no TEXT, tarih DATE, sagim_zamani TEXT, eski_ortalama NUMERIC, son_verim NUMERIC,
         dusus_yuzdesi NUMERIC, mesaj TEXT, okundu BOOLEAN, ciftlik_id INT)
gunluk_ozetler(ciftlik_id INT, tarih DATE, dunku_toplam_sut NUMERIC, bugunku_toplam_sut NUMERIC,
               en_verimli_inek_kupe_no TEXT, mesaj TEXT)
ciftlikler(id INT, ad TEXT)
"""


def _chat(system: str, user: str, num_predict: int | None = None) -> str:
    body = _post_json(
        f"{settings.ollama_base_url.rstrip('/')}/api/chat",
        {
            "model": settings.rag_llm,
            "stream": False,
            "options": {
                "temperature": settings.llm_temperature,
                "num_predict": num_predict or settings.llm_num_predict,
                "num_ctx": settings.llm_num_ctx,
                "seed": settings.llm_seed,
            },
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        },
        timeout=180,
    )
    message = body.get("message") or {}
    return str(message.get("content") or "").strip()


CHAT_GREETING = (
    "Merhaba, ben Süt Sihirbazı. Çiftlik kayıtlarındaki süt verimi, "
    "inek sayısı ve alarmlar hakkında soru sorabilirsin. "
    "Mastitis, besleme ve buzağı sağlığı gibi genel konularda da "
    "kaynaklara dayalı bilgi verebilirim. Kesin hastalık tanısı koymam; "
    "antibiyotik veya doz önermem."
)

CHAT_THANKS = "Rica ederim. Başka bir soru sorabilirsin."


def _tr_num(value: Any, digits: int = 2) -> str:
    return f"{float(value):.{digits}f}".replace(".", ",")


def _extract_sql(text: str) -> str:
    fenced = re.search(r"```(?:sql)?\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if fenced:
        text = fenced.group(1)
    match = re.search(r"(?is)\b(?:WITH|SELECT)\b.*", text)
    if not match:
        return text.strip().rstrip(";")
    return match.group(0).split(";")[0].strip()


def _run_select(sql: str) -> list[dict]:
    blocked = reject_unsafe_sql(sql)
    if blocked:
        raise ValueError(blocked)
    conn = _connect()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(sql)
            return list(cursor.fetchmany(40))
    finally:
        conn.close()


def _canned_chat(question: str) -> str | None:
    q = _normalize(question).strip()
    if not q:
        return CHAT_GREETING
    if any(term in q for term in ("tesekkur", "sag ol", "sagol")):
        return CHAT_THANKS
    if any(
        term in q
        for term in (
            "merhaba",
            "selam",
            "nasilsin",
            "iyi gunler",
            "iyi aksamlar",
            "gunaydin",
            "ne yapabilirsin",
            "kendini tanit",
            "yardimci olur musun",
        )
    ):
        return CHAT_GREETING
    return None


def _templated_sql_answer(question: str) -> str | None:
    q = _normalize(question)
    farm_i = farm_sql_clause("i.")
    farm_a = farm_sql_clause("a.")
    farm_sk = farm_sql_clause("sk.")

    if ("suru" in q and "ortalama" in q) or "ortalama sut" in q:
        rows = _run_select(
            f"""
            SELECT
                ROUND(AVG(sk.sut_miktari)::numeric, 2) AS sagim_ortalamasi,
                COUNT(*) AS sagim_sayisi,
                COUNT(DISTINCT sk.kupe_no) AS inek_sayisi
            FROM sagim_kayitlari sk
            WHERE 1=1{farm_sk}
            """
        )
        if not rows or rows[0]["sagim_ortalamasi"] is None:
            return "Çiftlik kayıtlarında sürü süt ortalaması hesaplanacak sağım verisi bulunamadı."
        row = rows[0]
        return (
            f"Çiftlik kayıtlarına göre sürü süt ortalaması "
            f"{_tr_num(row['sagim_ortalamasi'])} litredir "
            f"(sağım başına ortalama; {row['inek_sayisi']} inek, "
            f"{row['sagim_sayisi']} sağım kaydı)."
        )

    if (
        "inek sayisi" in q
        or "kac inek" in q
        or "kayitli inek" in q
        or ("kac" in q and "inek" in q)
    ):
        rows = _run_select(
            f"SELECT COUNT(*) AS n FROM inekler i WHERE 1=1{farm_i}"
        )
        n = int(rows[0]["n"]) if rows else 0
        return f"Çiftlikte kayıtlı inek sayısı {n} adettir."

    if ("bugun" in q or "bugunku" in q or "sagilan" in q) and (
        "toplam" in q or "kac litre" in q or "sut" in q
    ):
        farm_s2 = farm_sql_clause("s2.")
        rows = _run_select(
            f"""
            SELECT sk.tarih, ROUND(SUM(sk.sut_miktari)::numeric, 1) AS toplam
            FROM sagim_kayitlari sk
            WHERE sk.tarih = (
                SELECT MAX(s2.tarih) FROM sagim_kayitlari s2 WHERE 1=1{farm_s2}
            ){farm_sk}
            GROUP BY sk.tarih
            """
        )
        if not rows or rows[0]["toplam"] is None:
            return "Son sağım günü için toplam süt kaydı bulunamadı."
        tarih = rows[0]["tarih"]
        tarih_s = tarih.strftime("%d.%m.%Y") if hasattr(tarih, "strftime") else str(tarih)
        days = _run_select(
            f"""
            SELECT sk.tarih, ROUND(SUM(sk.sut_miktari)::numeric, 1) AS toplam
            FROM sagim_kayitlari sk
            WHERE 1=1{farm_sk}
            GROUP BY sk.tarih
            ORDER BY sk.tarih DESC
            LIMIT 7
            """
        )
        day_lines = []
        for day in reversed(days):
            gun = day["tarih"]
            gun_s = gun.strftime("%d.%m.%Y") if hasattr(gun, "strftime") else str(gun)
            day_lines.append(f"- {gun_s}: {_tr_num(day['toplam'], 1)} L")
        extra = ("\nSon 7 günün günlük toplamları:\n" + "\n".join(day_lines)) if day_lines else ""
        return (
            f"Takvimdeki bugün değil, kayıtlardaki son sağım günü ({tarih_s}) "
            f"için toplam süt {_tr_num(rows[0]['toplam'], 1)} litredir."
            f"{extra}"
        )

    if any(
        term in q
        for term in (
            "en yuksek",
            "en cok sut",
            "en fazla sut",
            "en verimli",
        )
    ):
        rows = _run_select(
            f"""
            SELECT i.isim, i.kupe_no,
                   ROUND(AVG(sk.sut_miktari)::numeric, 1) AS ortalama_sut
            FROM sagim_kayitlari sk
            JOIN inekler i ON sk.kupe_no = i.kupe_no
            WHERE 1=1{farm_i}{farm_sk}
            GROUP BY i.kupe_no, i.isim
            ORDER BY ortalama_sut DESC
            LIMIT 10
            """
        )
        if not rows:
            return "En verimli inekler için kayıt bulunamadı."
        lines = [
            f"- {row['isim']} ({row['kupe_no']}): {_tr_num(row['ortalama_sut'], 1)} L"
            for row in rows
        ]
        return "Süt verimi en yüksek 10 inek:\n" + "\n".join(lines)

    if any(
        term in q
        for term in ("risk", "dusen", "dusus", "alarm")
    ) and "neden" not in q:
        rows = _run_select(
            f"""
            SELECT a.kupe_no, i.isim, a.tarih, a.sagim_zamani,
                   a.eski_ortalama, a.son_verim, a.dusus_yuzdesi
            FROM alarmlar a
            LEFT JOIN inekler i ON a.kupe_no = i.kupe_no
            WHERE 1=1{farm_a}
            ORDER BY a.tarih DESC, a.id DESC
            LIMIT 10
            """
        )
        if not rows:
            return "Kayıtlarda süt düşüş alarmı bulunmuyor."
        lines = []
        for row in rows:
            sagim = "akşam" if row["sagim_zamani"] == "e" else "sabah"
            tarih = row["tarih"]
            tarih_s = tarih.strftime("%d.%m.%Y") if hasattr(tarih, "strftime") else str(tarih)
            lines.append(
                f"- {row['isim'] or row['kupe_no']} ({row['kupe_no']}): "
                f"{tarih_s} {sagim} sağımında "
                f"{_tr_num(row['eski_ortalama'])} L → "
                f"{_tr_num(row['son_verim'])} L "
                f"(%{_tr_num(row['dusus_yuzdesi'])} düşüş)"
            )
        return "Süt veriminde düşüş yaşayan riskli inekler:\n" + "\n".join(lines)

    cow_row = _find_cow(q)
    if cow_row:
        return _cow_status_answer(cow_row, farm_i, farm_sk, farm_a)

    return None


def _connect():
    return psycopg2.connect(
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT", "5432")),
    )


def _resolve_farm_id(ciftlik_id: int | None) -> int | None:
    """Kullanıcının çiftliğinde inek yoksa sentetik demo sürüye (kayıtlı sürü) düş."""
    conn = _connect()
    try:
        with conn.cursor() as cursor:
            if ciftlik_id is not None:
                cursor.execute(
                    "SELECT COUNT(*) FROM inekler WHERE COALESCE(ciftlik_id, 1) = %s",
                    (int(ciftlik_id),),
                )
                if cursor.fetchone()[0] > 0:
                    return int(ciftlik_id)
            cursor.execute(
                "SELECT COALESCE(ciftlik_id, 1) FROM inekler "
                "GROUP BY 1 ORDER BY COUNT(*) DESC LIMIT 1"
            )
            row = cursor.fetchone()
            return int(row[0]) if row else ciftlik_id
    finally:
        conn.close()


def _sql_incomplete(sql: str) -> bool:
    text = (sql or "").strip()
    if not text or text.count("(") != text.count(")"):
        return True
    if re.search(r"(?i)\b(from|join)\s+[a-z_]{1,12}$", text):
        return True
    if re.search(r"(?i)sagim_kayitl(?!ari\b)", text):
        return True
    return False


def _find_cow(question_norm: str) -> dict | None:
    farm_i = farm_sql_clause("i.")
    rows = _run_select(
        f"SELECT i.kupe_no, i.isim, i.irk, i.ciftlik_id FROM inekler i WHERE 1=1{farm_i}"
    )
    for row in rows:
        kupe = _normalize(str(row["kupe_no"]))
        isim = _normalize(str(row["isim"]))
        if kupe and kupe in question_norm:
            return row
        if isim and isim in question_norm:
            return row
    match = re.search(r"tr\s*0*\d{3,5}", question_norm)
    if match:
        token = re.sub(r"\s+", "", match.group(0))
        for row in rows:
            if _normalize(str(row["kupe_no"])) == token:
                return row
    return None


def _cow_status_answer(cow: dict, farm_i: str, farm_sk: str, farm_a: str) -> str:
    kupe = str(cow["kupe_no"])
    milk = _run_select(
        f"""
        SELECT sk.tarih, sk.sagim_zamani, sk.sut_miktari
        FROM sagim_kayitlari sk
        JOIN inekler i ON i.kupe_no = sk.kupe_no
        WHERE i.kupe_no = '{kupe.replace("'", "")}'{farm_i}{farm_sk}
        ORDER BY sk.tarih DESC, sk.id DESC
        LIMIT 6
        """
    )
    alarms = _run_select(
        f"""
        SELECT a.tarih, a.sagim_zamani, a.eski_ortalama, a.son_verim, a.dusus_yuzdesi
        FROM alarmlar a
        WHERE a.kupe_no = '{kupe.replace("'", "")}'{farm_a}
        ORDER BY a.tarih DESC, a.id DESC
        LIMIT 1
        """
    )
    lines = [
        f"{cow['isim']} ({kupe}"
        + (f", {cow['irk']}" if cow.get("irk") else "")
        + ") için çiftlik kayıtları:"
    ]
    if milk:
        lines.append("Son sağımlar:")
        for row in milk:
            sagim = "akşam" if row["sagim_zamani"] == "e" else "sabah"
            tarih = row["tarih"]
            tarih_s = tarih.strftime("%d.%m.%Y") if hasattr(tarih, "strftime") else str(tarih)
            lines.append(
                f"- {tarih_s} {sagim}: {_tr_num(row['sut_miktari'])} L"
            )
    else:
        lines.append("Sağım kaydı bulunamadı.")
    if alarms:
        row = alarms[0]
        sagim = "akşam" if row["sagim_zamani"] == "e" else "sabah"
        tarih = row["tarih"]
        tarih_s = tarih.strftime("%d.%m.%Y") if hasattr(tarih, "strftime") else str(tarih)
        lines.append(
            f"Son süt düşüş alarmı: {tarih_s} {sagim} sağımında "
            f"{_tr_num(row['eski_ortalama'])} L → {_tr_num(row['son_verim'])} L "
            f"(%{_tr_num(row['dusus_yuzdesi'])})."
        )
    lines.append(
        "Bu kayıtlar tanı değildir. Hayvan sağlığı kararı veteriner hekimindir."
    )
    return "\n".join(lines)


class LocalThesisService:
    """Windows'ta Torch yüklenemediği için Ollama HTTP + BM25/BGE-M3 yolu."""

    def __init__(self):
        self.retriever = TorchFreeRetriever()
        self.farm = FarmDataService()

    def _route(self, question: str) -> str:
        route = deterministic_route(question)
        if route:
            return route
        label = _chat(
            "Sınıfı tek kelime yaz: RAG, SQL, HYBRID veya CHAT.",
            question,
            num_predict=8,
        ).upper()
        for candidate in ("HYBRID", "RAG", "SQL", "CHAT"):
            if candidate in label:
                return candidate
        return "RAG"

    def _rag(self, question: str) -> dict[str, Any]:
        hits = [
            hit
            for hit in self.retriever.retrieve_hits(
                question, final_top_k=settings.final_top_k * 2, mode="hybrid"
            )
            if not is_low_value_chunk(hit.get("text") or "")
        ][: settings.final_top_k]
        blocks = []
        sources = []
        for i, hit in enumerate(hits, start=1):
            source_id = f"K{i}"
            header = f"[{source_id}] {hit['title']}"
            if hit.get("page"):
                header += f", s. {hit['page']}"
            blocks.append(f"{header}\n{hit['text']}")
            sources.append({
                "id": source_id,
                "title": hit["title"],
                "page": hit.get("page"),
            })
        context = "\n\n---\n\n".join(blocks) or "Kaynak bulunamadı."
        answer = finish_answer(
            _chat(
                RAG_SYSTEM,
                f"SORU:\n{question}\n\nKAYNAK BAĞLAMI:\n{context}",
                num_predict=settings.llm_num_predict,
            )
        )
        return {
            "answer": ensure_veterinary_disclaimer(answer),
            "sources": sources,
        }

    def _sql(self, question: str, ciftlik_id: int | None) -> str:
        templated = _templated_sql_answer(question)
        if templated:
            return templated
        farm_hint = (
            f"Sorguda ilgili tablolara AND COALESCE(ciftlik_id, 1) = {int(ciftlik_id)} ekle."
            if ciftlik_id is not None
            else "ciftlik_id süzgeci ekleme."
        )
        raw = _chat(
            "PostgreSQL için yalnızca bir SELECT veya WITH ... SELECT yaz. "
            "Markdown, açıklama ve noktalı virgül yok. "
            f"Şema:\n{SCHEMA}\n{farm_hint}",
            question,
            num_predict=400,
        )
        sql = _extract_sql(raw)
        blocked = reject_unsafe_sql(sql)
        if blocked or _sql_incomplete(sql):
            return (
                "Bu çiftlik sorusunu güvenli bir okuma sorgusuna çeviremedim. "
                "Sürü ortalaması, inek sayısı, bugünkü toplam süt veya "
                "en verimli inekler olarak sorabilirsin."
            )
        try:
            rows = _run_select(sql)
            payload = json.dumps(rows, ensure_ascii=False, default=str)
            return _chat(
                "Sen süt çiftliği asistanısın. SQL sonucunu kısa Türkçe açıkla. "
                "Sayıları değiştirme. Tanı veya ilaç önerme. "
                "Süt sığırcılığını hastalık gibi anlatma.",
                f"SORU:\n{question}\n\nSONUÇ:\n{payload}",
            )
        except Exception as exc:
            return f"Sorgu çalıştırılamadı: {exc}"

    def _hybrid(self, question: str, ciftlik_id: int | None) -> dict[str, Any]:
        templated = _templated_sql_answer(question)
        cow_row = _find_cow(_normalize(question))
        if templated:
            farm_answer = templated
            cow_name = str(cow_row["isim"]) if cow_row else "ilgili hayvan"
        else:
            farm_data = self.farm.get_latest_milk_drop(question, ciftlik_id)
            if farm_data:
                sagim_zamani = "akşam" if farm_data["sagim_zamani"] == "e" else "sabah"
                tarih = farm_data["tarih"].strftime("%d.%m.%Y")
                eski = f'{farm_data["eski_ortalama"]:.2f}'.replace(".", ",")
                son = f'{farm_data["son_verim"]:.2f}'.replace(".", ",")
                dusus = f'{farm_data["dusus_yuzdesi"]:.2f}'.replace(".", ",")
                farm_answer = (
                    f'Çiftlik kayıtlarına göre {farm_data["isim"]} '
                    f'({farm_data["kupe_no"]}) için {tarih} tarihli '
                    f'{sagim_zamani} sağımında süt verimi, önceki sağım '
                    f'ortalaması olan {eski} litreden {son} litreye düşmüştür. '
                    f'Bu değişim yaklaşık %{dusus} oranında bir süt verimi '
                    f'düşüşüne karşılık gelmektedir.'
                )
                cow_name = farm_data["isim"]
            else:
                farm_answer = self._sql(question, ciftlik_id)
                cow_name = "ilgili hayvan"
        rag_result = self._rag(
            f"{question}\n\nSorunun bilimsel kısmını genel süt sığırcılığı "
            "kaynaklarına göre yanıtla. Belirli bir hayvana kesin tanı koyma."
        )
        answer = (
            f"{farm_answer}\n\n"
            f"Kaynaklara göre genel değerlendirme:\n"
            f"{rag_result['answer']}\n\n"
            f"Bu kaynak bilgileri {cow_name} için kesin bir neden veya tanı "
            f"göstermez.\n\n{VETERINARY_DISCLAIMER}"
        )
        return {"answer": answer, "sources": rag_result.get("sources", [])}

    def ask(
        self,
        question: str,
        ciftlik_id: int | None = None,
        include_debug: bool = False,
    ) -> dict[str, Any]:
        ciftlik_id = _resolve_farm_id(ciftlik_id)
        token = current_farm_id.set(ciftlik_id)
        try:
            route = self._route(question)
            if is_diagnosis_or_treatment_request(question) and route != "CHAT":
                result = {
                    "route": route,
                    "answer": refuse_diagnosis_answer(),
                    "sources": [],
                }
            elif route == "SQL":
                result = {
                    "route": route,
                    "answer": self._sql(question, ciftlik_id),
                    "sources": [],
                }
            elif route == "RAG":
                rag_result = self._rag(question)
                result = {"route": route, **rag_result}
            elif route == "HYBRID":
                hybrid = self._hybrid(question, ciftlik_id)
                result = {"route": route, **hybrid}
            else:
                canned = _canned_chat(question)
                result = {
                    "route": "CHAT",
                    "answer": canned or _chat(
                        "Sen Süt Sihirbazı'sın. Kullanıcı selamlaşıyor. "
                        "1-2 kısa Türkçe cümle yaz. Süt sığırcılığını hastalık "
                        "gibi anlatma. Bakteri, mastitis, tanı veya antibiyotik yazma. "
                        "Ne yapabileceğini kısaca söyle.",
                        question,
                    ),
                    "sources": [],
                }
            if include_debug:
                result["debug"] = {
                    "ciftlik_id": ciftlik_id,
                    "runtime": "torch_free_ollama",
                }
            return result
        finally:
            current_farm_id.reset(token)
