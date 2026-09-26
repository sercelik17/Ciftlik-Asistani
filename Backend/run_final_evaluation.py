from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from statistics import mean, median

from thesis_rag.thesis_service import ThesisAssistantService

DEFAULT_TEST_SET = Path("tez_test_seti_100.json")
DEFAULT_RESULTS = Path("evaluation_results.jsonl")
DEFAULT_SUMMARY = Path("evaluation_summary.json")


def load_questions(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_completed_ids(path: Path):
    ids = set()
    if not path.exists():
        return ids

    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
                ids.add(row["id"])
            except Exception:
                pass
    return ids


def append_result(path: Path, row: dict):
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def read_results(path: Path):
    rows = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def build_summary(rows: list[dict]):
    valid = [r for r in rows if not r.get("error")]
    latencies = [r["latency_sec"] for r in valid]

    route_total = len(valid)
    route_correct = sum(
        1 for r in valid
        if r.get("predicted_route") == r.get("expected_route")
    )

    by_route = {}
    for route in ("RAG", "SQL", "HYBRID"):
        subset = [r for r in valid if r["expected_route"] == route]
        if not subset:
            continue

        correct = sum(
            1 for r in subset
            if r.get("predicted_route") == route
        )
        route_lat = [r["latency_sec"] for r in subset]

        by_route[route] = {
            "count": len(subset),
            "route_correct": correct,
            "route_accuracy": round(correct / len(subset), 4),
            "mean_latency_sec": round(mean(route_lat), 3),
            "median_latency_sec": round(median(route_lat), 3),
        }

    return {
        "completed": len(rows),
        "successful": len(valid),
        "errors": len(rows) - len(valid),
        "route_accuracy": (
            round(route_correct / route_total, 4)
            if route_total else None
        ),
        "mean_latency_sec": (
            round(mean(latencies), 3)
            if latencies else None
        ),
        "median_latency_sec": (
            round(median(latencies), 3)
            if latencies else None
        ),
        "by_expected_route": by_route,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--test-set",
        default=str(DEFAULT_TEST_SET),
        help="100 soruluk JSON test seti",
    )
    parser.add_argument(
        "--results",
        default=str(DEFAULT_RESULTS),
        help="Satır satır sonuç dosyası",
    )
    parser.add_argument(
        "--summary",
        default=str(DEFAULT_SUMMARY),
        help="Özet sonuç dosyası",
    )
    parser.add_argument(
        "--ciftlik-id",
        type=int,
        default=1,
        help="Test çiftliği ID'si",
    )
    parser.add_argument(
        "--route",
        choices=["RAG", "SQL", "HYBRID"],
        default=None,
        help="Yalnızca seçilen beklenen rota üzerinde test yap",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="İlk N uygun soruyu çalıştır",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Daha önce tamamlanan soruları atla",
    )
    args = parser.parse_args()

    test_path = Path(args.test_set)
    results_path = Path(args.results)
    summary_path = Path(args.summary)

    questions = load_questions(test_path)

    if args.route:
        questions = [
            q for q in questions
            if q["route"] == args.route
        ]

    completed_ids = (
        load_completed_ids(results_path)
        if args.resume else set()
    )

    questions = [
        q for q in questions
        if q["id"] not in completed_ids
    ]

    if args.limit is not None:
        questions = questions[:args.limit]

    print(f"Çalıştırılacak soru sayısı: {len(questions)}")
    print(f"Çiftlik ID: {args.ciftlik_id}")
    print("-" * 70)

    service = ThesisAssistantService()

    for index, item in enumerate(questions, start=1):
        qid = item["id"]
        question = item["question"]
        expected_route = item["route"]

        print(
            f"[{index}/{len(questions)}] "
            f"{qid} | Beklenen: {expected_route}"
        )
        print(question)

        started = time.perf_counter()

        try:
            response = service.ask(
                question=question,
                ciftlik_id=args.ciftlik_id,
            )
            latency = time.perf_counter() - started

            predicted_route = response.get("route")
            answer = response.get("answer", "")
            sources = response.get("sources", []) or []

            row = {
                "id": qid,
                "expected_route": expected_route,
                "predicted_route": predicted_route,
                "route_correct": predicted_route == expected_route,
                "category": item.get("category"),
                "question": question,
                "answer": answer,
                "sources": sources,
                "source_titles": [
                    s.get("title")
                    for s in sources
                    if isinstance(s, dict)
                ],
                "preferred_sources": item.get(
                    "preferred_sources", []
                ),
                "latency_sec": round(latency, 4),
                "error": None,
            }

            print(
                f"Rota: {predicted_route} | "
                f"Süre: {latency:.2f} sn | "
                f"Kaynak: {len(sources)}"
            )

        except Exception as exc:
            latency = time.perf_counter() - started
            row = {
                "id": qid,
                "expected_route": expected_route,
                "predicted_route": None,
                "route_correct": False,
                "category": item.get("category"),
                "question": question,
                "answer": "",
                "sources": [],
                "source_titles": [],
                "preferred_sources": item.get(
                    "preferred_sources", []
                ),
                "latency_sec": round(latency, 4),
                "error": repr(exc),
            }

            print(f"HATA: {exc}")

        append_result(results_path, row)
        print("-" * 70)

    rows = read_results(results_path)
    summary = build_summary(rows)

    with summary_path.open("w", encoding="utf-8") as f:
        json.dump(
            summary,
            f,
            ensure_ascii=False,
            indent=2,
        )

    print("\nTEST ÖZETİ")
    print("=" * 70)
    print(json.dumps(
        summary,
        ensure_ascii=False,
        indent=2,
    ))


if __name__ == "__main__":
    main()
