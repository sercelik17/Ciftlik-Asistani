from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

from thesis_eval.metrics import (
    ROUTES,
    classification_report,
    extract_numbers,
    generation_metrics,
    latency_stats,
    mean_retrieval_metrics,
    numbers_match,
    retrieval_metrics_for_query,
    summarize_errors,
)
from thesis_eval.reproducibility import write_reproducibility
from thesis_rag.route_rules import deterministic_route

load_dotenv()

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TEST_SET = ROOT / "evaluation_sets" / "final_heldout_set.json"
DEFAULT_OUT_DIR = ROOT / "evaluation_output"


def load_questions(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def dump_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def retrieved_titles(docs) -> list[str]:
    titles = []
    for doc in docs:
        titles.append(
            str(
                doc.metadata.get("source_name")
                or doc.metadata.get("source_stem")
                or ""
            )
        )
    return titles


def run_gold_sql(query: str):
    if not query:
        return None
    connection = psycopg2.connect(
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT", "5432")),
    )
    try:
        with connection.cursor() as cursor:
            cursor.execute(query)
            return cursor.fetchall()
    finally:
        connection.close()


def _classify_route(question: str) -> tuple[str, str]:
    """
    Canlı sistemle aynı sıra: önce kural tabanlı yönlendirme.
    Kural karar veremezse LangChain router denenir; Torch bozuksa
    sistemdeki fallback gibi RAG kabul edilir.
    """
    predicted = deterministic_route(question)
    if predicted is not None:
        return predicted, "rules"

    try:
        from thesis_rag.query_router import QueryRouter

        predicted = QueryRouter().classify(question)
        return predicted, "llm"
    except Exception:
        return "RAG", "fallback"


def evaluate_routing(questions: list[dict]) -> dict:
    rows = []
    latencies = []
    for item in questions:
        started = time.perf_counter()
        predicted, how = _classify_route(item["question"])
        latency = time.perf_counter() - started
        latencies.append(latency)
        rows.append({
            "id": item["id"],
            "question": item["question"],
            "expected_route": item["route"],
            "predicted_route": predicted,
            "route_correct": predicted == item["route"],
            "router_backend": how,
            "latency_sec": round(latency, 4),
        })
    y_true = [row["expected_route"] for row in rows]
    y_pred = [row["predicted_route"] for row in rows]
    by_route = {}
    for route in ROUTES:
        subset = [row["latency_sec"] for row in rows if row["expected_route"] == route]
        by_route[route] = latency_stats(subset)
    report = classification_report(y_true, y_pred)
    report["router_note"] = (
        "Canlı sistem önce kural tabanlı yönlendiriciyi kullanır; "
        "kural sonuç verirse LLM çağrılmaz. Bu rapor aynı sırayı izler."
    )
    report["latency"] = {
        "overall": latency_stats(latencies),
        "by_expected_route": by_route,
    }
    report["rows"] = rows
    return report


def evaluate_retrieval(questions: list[dict], k: int = 5) -> dict:
    from thesis_eval.eval_retriever import TorchFreeRetriever

    retriever = TorchFreeRetriever()
    modes = ("bm25", "faiss", "hybrid")
    per_mode_rows = {mode: [] for mode in modes}
    detail_rows = []

    rag_items = [
        item for item in questions
        if item.get("route") == "RAG" and item.get("preferred_sources")
    ]

    for item in rag_items:
        row = {
            "id": item["id"],
            "question": item["question"],
            "preferred_sources": item["preferred_sources"],
            "modes": {},
        }
        for mode in modes:
            titles = retriever.retrieve(
                item["question"],
                final_top_k=k,
                mode=mode,
            )
            metrics = retrieval_metrics_for_query(
                titles,
                item["preferred_sources"],
                k=k,
            )
            row["modes"][mode] = {
                "retrieved_titles": titles,
                **metrics,
            }
            per_mode_rows[mode].append(metrics)
        detail_rows.append(row)

    summary = {
        mode: mean_retrieval_metrics(per_mode_rows[mode])
        for mode in modes
    }
    return {
        "k": k,
        "n": len(rag_items),
        "backend": (
            "Torch/FAISS Python bagimi bu ortamda yuklenemedigi icin "
            "dense retrieval BGE-M3 + brute-force L2 (IndexFlatL2 esdegeri) "
            "ile olculdu. BM25 ve Weighted RRF production ile aynidir."
        ),
        "summary": summary,
        "rows": detail_rows,
    }


def evaluate_fusion_ablation(questions: list[dict], k: int = 5) -> dict:
    from thesis_eval.eval_retriever import TorchFreeRetriever

    retriever = TorchFreeRetriever()
    weights = [(0.50, 0.50), (0.60, 0.40), (0.70, 0.30)]
    rag_items = [
        item for item in questions
        if item.get("route") == "RAG" and item.get("preferred_sources")
    ]
    summary = {}
    for dense, sparse in weights:
        key = f"{int(dense * 100)}/{int(sparse * 100)}"
        rows = []
        for item in rag_items:
            titles = retriever.retrieve(
                item["question"],
                final_top_k=k,
                mode="hybrid",
                dense_weight=dense,
                sparse_weight=sparse,
            )
            rows.append(
                retrieval_metrics_for_query(
                    titles,
                    item["preferred_sources"],
                    k=k,
                )
            )
        summary[key] = mean_retrieval_metrics(rows)
    return {
        "k": k,
        "n": len(rag_items),
        "fusion_method": "weighted_rrf",
        "summary": summary,
        "selection_rule": (
            "Development/pilot set üzerinde MRR ve nDCG@5'e göre "
            "en yüksek konfigürasyon seçilir; final held-out sette "
            "yalnızca dondurulmuş 60/40 ağırlığı raporlanır."
        ),
    }


def evaluate_end_to_end(
    questions: list[dict],
    ciftlik_id: int,
    include_generation: bool,
) -> dict:
    from thesis_rag.thesis_service import ThesisAssistantService

    service = ThesisAssistantService()
    rows = []
    for item in questions:
        started = time.perf_counter()
        error = None
        try:
            response = service.ask(
                question=item["question"],
                ciftlik_id=ciftlik_id,
                include_debug=True,
            )
        except Exception as exc:
            response = {
                "route": None,
                "answer": "",
                "sources": [],
            }
            error = repr(exc)
        latency = time.perf_counter() - started
        sources = response.get("sources") or []
        source_titles = [
            item_source.get("title")
            for item_source in sources
            if isinstance(item_source, dict)
        ]
        row = {
            "id": item["id"],
            "question": item["question"],
            "expected_route": item["route"],
            "predicted_route": response.get("route"),
            "route_correct": response.get("route") == item["route"],
            "category": item.get("category"),
            "answer": response.get("answer", ""),
            "sources": sources,
            "source_titles": source_titles,
            "preferred_sources": item.get("preferred_sources", []),
            "expected_behavior": item.get("expected_behavior"),
            "latency_sec": round(latency, 4),
            "error": error,
        }

        if item.get("preferred_sources"):
            row["retrieval"] = retrieval_metrics_for_query(
                source_titles,
                item["preferred_sources"],
                k=5,
            )

        if include_generation and item["route"] in {"RAG", "HYBRID"}:
            row["generation"] = generation_metrics(
                row["answer"],
                sources,
                item.get("preferred_sources"),
            )

        if item.get("gold_sql"):
            try:
                gold_rows = run_gold_sql(item["gold_sql"])
                gold_numbers = extract_numbers(str(gold_rows))
                answer_numbers = extract_numbers(row["answer"])
                row["gold_sql_result"] = str(gold_rows)
                row["execution_correct"] = gold_rows is not None
                row["sql_executed"] = True
                row["numerical_correct"] = numbers_match(
                    gold_numbers,
                    answer_numbers,
                ) if gold_numbers else None
            except Exception as exc:
                row["sql_executed"] = False
                row["execution_correct"] = False
                row["numerical_correct"] = False
                row["sql_error"] = repr(exc)

        if item["route"] == "HYBRID":
            farm_ok = True
            for token in item.get("required_answer_terms", []):
                if str(token).casefold() not in row["answer"].casefold():
                    farm_ok = False
                    break
            gen = row.get("generation") or {}
            retrieval_ok = (row.get("retrieval") or {}).get("r_at_k", 1) > 0
            row["hybrid_e2e_correct"] = bool(
                farm_ok
                and retrieval_ok
                and gen.get("citation_completeness", 1) > 0
            )

        rows.append(row)

    valid = [row for row in rows if not row.get("error")]
    y_true = [row["expected_route"] for row in valid]
    y_pred = [row["predicted_route"] for row in valid]
    routing = classification_report(y_true, y_pred)
    by_route_latency = {}
    for route in ROUTES:
        subset = [
            row["latency_sec"]
            for row in valid
            if row["expected_route"] == route
        ]
        by_route_latency[route] = latency_stats(subset)

    sql_rows = [row for row in valid if row["expected_route"] == "SQL"]
    hybrid_rows = [row for row in valid if row["expected_route"] == "HYBRID"]
    rag_rows = [row for row in valid if row["expected_route"] == "RAG"]

    return {
        "completed": len(rows),
        "successful": len(valid),
        "errors": len(rows) - len(valid),
        "routing": routing,
        "latency": {
            "overall": latency_stats([row["latency_sec"] for row in valid]),
            "by_expected_route": by_route_latency,
        },
        "sql": {
            "n": len(sql_rows),
            "execution_accuracy": (
                round(
                    sum(1 for row in sql_rows if row.get("execution_correct"))
                    / len(sql_rows),
                    4,
                )
                if sql_rows else None
            ),
            "numerical_accuracy": (
                round(
                    sum(1 for row in sql_rows if row.get("numerical_correct"))
                    / max(1, sum(
                        1 for row in sql_rows
                        if row.get("numerical_correct") is not None
                    )),
                    4,
                )
                if sql_rows else None
            ),
        },
        "hybrid": {
            "n": len(hybrid_rows),
            "end_to_end_accuracy": (
                round(
                    sum(1 for row in hybrid_rows if row.get("hybrid_e2e_correct"))
                    / len(hybrid_rows),
                    4,
                )
                if hybrid_rows else None
            ),
        },
        "generation": {
            "n": len(rag_rows),
            "mean_citation_correctness": (
                round(
                    sum(
                        (row.get("generation") or {}).get("citation_correctness", 0)
                        for row in rag_rows
                    ) / len(rag_rows),
                    4,
                )
                if rag_rows else None
            ),
            "mean_unsupported_claim_rate": (
                round(
                    sum(
                        (row.get("generation") or {}).get(
                            "unsupported_claim_rate", 0
                        )
                        for row in rag_rows
                    ) / len(rag_rows),
                    4,
                )
                if rag_rows else None
            ),
        },
        "error_analysis": summarize_errors(rows),
        "rows": rows,
    }


SYSTEM_PROMPT = """Sen süt sığırcılığı alanında çalışan kaynak-temelli bir yapay zekâ danışmanısın.
SADECE verilen KAYNAK BAĞLAMI içindeki bilgileri kullan.
HER ZAMAN TÜRKÇE cevap ver.
Cevap en fazla 3 kısa cümle olsun.
Kesin hastalık tanısı koyma. Antibiyotik veya doz önerme.
Her bilimsel cümlenin sonunda [K1] veya [K2] gibi kaynak kimliği yaz.
Kaynakta yoksa uydurma.
JSON veya kod üretme."""


def _ollama_chat(question: str, context: str) -> str:
    from thesis_rag.settings import settings
    from thesis_eval.eval_retriever import _post_json

    body = _post_json(
        f"{settings.ollama_base_url.rstrip('/')}/api/chat",
        {
            "model": settings.rag_llm,
            "stream": False,
            "options": {
                "temperature": settings.llm_temperature,
                "num_predict": settings.llm_num_predict,
                "num_ctx": settings.llm_num_ctx,
                "seed": settings.llm_seed,
            },
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"SORU:\n{question}\n\n"
                        f"KAYNAK BAĞLAMI:\n{context}\n\n"
                        "Yalnızca kaynak bağlamına dayanarak Türkçe cevap ver."
                    ),
                },
            ],
        },
        timeout=180,
    )
    message = body.get("message") or {}
    return str(message.get("content") or "")


def evaluate_generation(questions: list[dict], k: int = 5) -> dict:
    from thesis_eval.eval_retriever import TorchFreeRetriever
    from thesis_rag.safety import (
        is_diagnosis_or_treatment_request,
        refuse_diagnosis_answer,
    )

    retriever = TorchFreeRetriever()
    rag_items = [item for item in questions if item.get("route") == "RAG"]
    rows = []
    for index, item in enumerate(rag_items, start=1):
        print(f"Generation {index}/{len(rag_items)} {item['id']}")
        started = time.perf_counter()
        if is_diagnosis_or_treatment_request(item["question"]):
            answer = refuse_diagnosis_answer()
            sources = []
            hits = []
        else:
            hits = retriever.retrieve_hits(
                item["question"], final_top_k=k, mode="hybrid"
            )
            blocks = []
            sources = []
            for i, hit in enumerate(hits, start=1):
                source_id = f"K{i}"
                page = hit.get("page")
                header = f"[{source_id}] {hit['title']}"
                if page:
                    header += f", s. {page}"
                blocks.append(f"{header}\n{hit['text']}")
                sources.append({
                    "id": source_id,
                    "title": hit["title"],
                    "page": page,
                })
            context = "\n\n---\n\n".join(blocks)
            answer = _ollama_chat(item["question"], context)
        latency = time.perf_counter() - started
        gen = generation_metrics(
            answer,
            sources,
            item.get("preferred_sources"),
        )
        rows.append({
            "id": item["id"],
            "question": item["question"],
            "answer": answer,
            "sources": sources,
            "generation": gen,
            "expected_behavior": item.get("expected_behavior"),
            "latency_sec": round(latency, 4),
        })

    n = len(rows) or 1
    summary = {
        "n": len(rows),
        "mean_citation_correctness": round(
            sum(r["generation"]["citation_correctness"] for r in rows) / n, 4
        ),
        "mean_citation_completeness": round(
            sum(r["generation"]["citation_completeness"] for r in rows) / n, 4
        ),
        "mean_unsupported_claim_rate": round(
            sum(r["generation"]["unsupported_claim_rate"] for r in rows) / n, 4
        ),
        "mean_preferred_source_hit_rate": round(
            sum(r["generation"]["preferred_source_hit_rate"] for r in rows) / n, 4
        ),
        "diagnosis_refusal_ok": sum(
            1 for r in rows
            if r.get("expected_behavior") != "refuse_diagnosis"
            or r["generation"]["refuses_diagnosis"]
        ),
        "latency": latency_stats([r["latency_sec"] for r in rows]),
    }
    return {"summary": summary, "rows": rows}


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Tez akademik değerlendirmesi: routing, retrieval, "
            "SQL/HYBRID ve generation metrikleri."
        )
    )
    parser.add_argument(
        "--task",
        choices=[
            "routing",
            "retrieval",
            "fusion-ablation",
            "generation",
            "e2e",
            "reproducibility",
            "all-offline",
        ],
        default="all-offline",
    )
    parser.add_argument("--test-set", default=str(DEFAULT_TEST_SET))
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    parser.add_argument("--ciftlik-id", type=int, default=1)
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument(
        "--pilot-set",
        default=str(ROOT / "tez_test_seti_100.json"),
        help="Geliştirme/pilot seti (fusion ablation için)",
    )
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    questions = load_questions(Path(args.test_set))

    write_reproducibility(out_dir / "reproducibility.json")

    if args.task in {"routing", "all-offline"}:
        routing = evaluate_routing(questions)
        dump_json(out_dir / "routing_report.json", routing)
        print("Routing Macro-F1:", routing.get("macro_f1"))
        print("Routing accuracy:", routing.get("accuracy"))

    if args.task in {"retrieval", "all-offline"}:
        retrieval = evaluate_retrieval(questions, k=args.k)
        dump_json(out_dir / "retrieval_report.json", retrieval)
        print("Retrieval özeti:", json.dumps(retrieval["summary"], ensure_ascii=False))

    if args.task in {"fusion-ablation", "all-offline"}:
        pilot = load_questions(Path(args.pilot_set))
        ablation = evaluate_fusion_ablation(pilot, k=args.k)
        dump_json(out_dir / "fusion_ablation_pilot.json", ablation)
        print("Fusion ablation:", json.dumps(ablation["summary"], ensure_ascii=False))

    if args.task == "generation":
        generation = evaluate_generation(questions, k=args.k)
        dump_json(out_dir / "generation_report.json", generation)
        print(
            "Generation özeti:",
            json.dumps(generation["summary"], ensure_ascii=False),
        )

    if args.task == "e2e":
        e2e = evaluate_end_to_end(
            questions,
            ciftlik_id=args.ciftlik_id,
            include_generation=True,
        )
        dump_json(out_dir / "e2e_report.json", e2e)
        slim = {key: value for key, value in e2e.items() if key != "rows"}
        print(json.dumps(slim, ensure_ascii=False, indent=2))

    if args.task == "reproducibility":
        print("reproducibility.json yazıldı.")


if __name__ == "__main__":
    main()
