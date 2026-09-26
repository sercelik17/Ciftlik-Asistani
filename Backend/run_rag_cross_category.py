import json
import time
from pathlib import Path

from thesis_rag.thesis_service import ThesisAssistantService

TARGET_IDS = {
    "RAG001",
    "RAG008",
    "RAG015",
    "RAG021",
    "RAG027",
    "RAG033",
    "RAG039",
    "RAG045",
}

TEST_FILE = Path("tez_test_seti_100.json")
OUT_FILE = Path("rag_cross_category_pilot.jsonl")

with TEST_FILE.open(encoding="utf-8") as f:
    data = json.load(f)

if isinstance(data, dict):
    data = data.get("questions", data.get("tests", data.get("items", [])))

questions = [
    item for item in data
    if str(item.get("id", "")) in TARGET_IDS
]

questions.sort(key=lambda x: x["id"])

assistant = ThesisAssistantService()

with OUT_FILE.open("w", encoding="utf-8") as out:
    for i, item in enumerate(questions, start=1):
        test_id = item["id"]
        question = item["question"]
        category = item.get("category")

        print("-" * 70)
        print(f"[{i}/{len(questions)}] {test_id} | {category}")
        print(question)

        start = time.perf_counter()

        try:
            result = assistant.ask(
                question=question,
                ciftlik_id=1,
            )

            latency = time.perf_counter() - start

            row = {
                "id": test_id,
                "category": category,
                "question": question,
                "route": result.get("route"),
                "answer": result.get("answer"),
                "sources": result.get("sources", []),
                "latency_sec": round(latency, 4),
                "error": None,
            }

            print(
                f"Rota: {row['route']} | "
                f"Süre: {latency:.2f} sn | "
                f"Kaynak: {len(row['sources'])}"
            )

        except Exception as e:
            latency = time.perf_counter() - start

            row = {
                "id": test_id,
                "category": category,
                "question": question,
                "route": None,
                "answer": None,
                "sources": [],
                "latency_sec": round(latency, 4),
                "error": str(e),
            }

            print("HATA:", e)

        out.write(
            json.dumps(
                row,
                ensure_ascii=False
            )
            + "\n"
        )

print("-" * 70)
print("Tamamlandı:", OUT_FILE)
