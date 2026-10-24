# -*- coding: utf-8 -*-
"""LLM-only baseline: aynı 33 RAG sorusu, retrieval bağlamı olmadan, aynı model ve parametreler.

Çıktı: evaluation_output/llm_only_baseline.json
Atıf metrikleri bağlam kimliği olmadığı için yapısal olarak 0'dır; bu dosya bunu açıkça kaydeder.
"""
from __future__ import annotations

import json
import re
import sys
import time
import urllib.request
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from thesis_rag.settings import settings  # noqa: E402
from thesis_eval.metrics import generation_metrics, latency_stats  # noqa: E402

GEN_REPORT = BACKEND / "evaluation_output" / "generation_report.json"
OUT = BACKEND / "evaluation_output" / "llm_only_baseline.json"

SYSTEM_PROMPT = """Sen süt sığırcılığı alanında çalışan bir yapay zekâ danışmanısın.

KURALLAR:
- HER ZAMAN TÜRKÇE cevap ver.
- Kullanıcının sorusuna doğrudan cevap ver.
- Cevap en fazla 3 kısa ve tam cümleden oluşsun.
- Kesin hastalık tanısı koyma.
- Antibiyotik, ilaç adı veya doz önerme.
- Kullanıcı tanı veya tedavi isterse veteriner hekime yönlendir.
- JSON, XML veya kod bloğu üretme.

YANIT BİÇİMİ:
Doğrudan normal Türkçe metin yaz."""

TURKISH_HINT = re.compile(r"[çğıöşüÇĞİÖŞÜ]")
FOREIGN_HINT = re.compile(
    r"\b(the|and|with|of|is|are|for|that|this|los|las|del|una|para|que|producción|período)\b",
    re.IGNORECASE,
)


def chat(question: str) -> tuple[str, float]:
    body = json.dumps(
        {
            "model": settings.rag_llm,
            "stream": False,
            "options": {
                "temperature": settings.llm_temperature,
                "num_predict": settings.llm_num_predict,
                "num_ctx": settings.llm_num_ctx,
                "seed": settings.llm_seed,
                "num_gpu": 0,
            },
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"SORU:\n{question}\n\nTürkçe cevap ver."},
            ],
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        f"{settings.ollama_base_url.rstrip('/')}/api/chat",
        data=body,
        headers={"Content-Type": "application/json"},
    )
    started = time.perf_counter()
    with urllib.request.urlopen(request, timeout=600) as response:
        payload = json.loads(response.read().decode("utf-8"))
    elapsed = time.perf_counter() - started
    message = payload.get("message") or {}
    return str(message.get("content") or "").strip(), elapsed


def main() -> None:
    report = json.loads(GEN_REPORT.read_text(encoding="utf-8"))
    rag_rows = report["rows"]
    rows = []
    done_ids = set()
    if OUT.exists():
        previous = json.loads(OUT.read_text(encoding="utf-8"))
        rows = previous.get("rows") or []
        done_ids = {row["id"] for row in rows}
    for source in rag_rows:
        if source["id"] in done_ids:
            continue
        answer, elapsed = chat(source["question"])
        metrics = generation_metrics(answer, sources=[], preferred_sources=None)
        foreign_hits = len(FOREIGN_HINT.findall(answer))
        rows.append(
            {
                "id": source["id"],
                "question": source["question"],
                "answer_llm_only": answer,
                "answer_rag": source.get("answer"),
                "latency_sec": round(elapsed, 4),
                "sentence_count": metrics["sentence_count"],
                "citation_correctness": metrics["citation_correctness"],
                "citation_completeness": metrics["citation_completeness"],
                "unsupported_claim_rate": metrics["unsupported_claim_rate"],
                "refuses_diagnosis": metrics["refuses_diagnosis"],
                "has_turkish_chars": bool(TURKISH_HINT.search(answer)),
                "foreign_token_hits": foreign_hits,
                "rag_citation_correctness": (source.get("generation") or {}).get("citation_correctness"),
                "rag_unsupported_claim_rate": (source.get("generation") or {}).get("unsupported_claim_rate"),
            }
        )
        OUT.write_text(
            json.dumps({"rows": rows, "status": "running"}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(source["id"], f"{elapsed:.1f}s", answer[:80].replace("\n", " "), flush=True)

    n = len(rows)
    latencies = [row["latency_sec"] for row in rows]
    summary = {
        "n": n,
        "model": settings.rag_llm,
        "options": {
            "temperature": settings.llm_temperature,
            "num_predict": settings.llm_num_predict,
            "num_ctx": settings.llm_num_ctx,
            "seed": settings.llm_seed,
            "num_gpu": 0,
        },
        "protocol": (
            "Aynı 33 ayrık final RAG sorusu; retrieval kapalı; bağlam yok; aynı model ve örnekleme "
            "parametreleri. Sistem istemi RAG istemiyle aynı dil, uzunluk, tanı ve ilaç kurallarını "
            "korur; yalnızca kaynak bağlamı ve [K] atıf kuralı çıkarılmıştır."
        ),
        "mean_citation_correctness": round(sum(r["citation_correctness"] for r in rows) / n, 4) if n else None,
        "mean_citation_completeness": round(sum(r["citation_completeness"] for r in rows) / n, 4) if n else None,
        "mean_unsupported_claim_rate": round(sum(r["unsupported_claim_rate"] for r in rows) / n, 4) if n else None,
        "refusal_marker_count": sum(1 for r in rows if r["refuses_diagnosis"]),
        "foreign_token_rows": sum(1 for r in rows if r["foreign_token_hits"] > 0),
        "mean_sentence_count": round(sum(r["sentence_count"] for r in rows) / n, 2) if n else None,
        "latency": latency_stats(latencies),
        "rag_reference": {
            "mean_citation_correctness": report["summary"].get("mean_citation_correctness"),
            "mean_citation_completeness": report["summary"].get("mean_citation_completeness"),
            "mean_unsupported_claim_rate": report["summary"].get("mean_unsupported_claim_rate"),
            "latency": report["summary"].get("latency"),
        },
        "interpretation_note": (
            "Atıf tabanlı otomatik metrikler bağlam kimliği olmadan yapısal olarak 0 ve 1 değerini alır; "
            "bu nedenle LLM-only ile RAG arasındaki fark, atıf metrikleriyle değil, insan puanlaması ve "
            "yanıt içeriği karşılaştırmasıyla yorumlanmalıdır. Bu dosya içerik doğruluğu puanı içermez."
        ),
    }
    OUT.write_text(
        json.dumps({"summary": summary, "rows": rows, "status": "complete"}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
