from __future__ import annotations

import math
from collections import Counter, defaultdict
from typing import Any, Iterable


ROUTES = ("RAG", "SQL", "HYBRID", "CHAT")


def percentile(values: list[float], p: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return round(ordered[0], 4)
    rank = (len(ordered) - 1) * (p / 100.0)
    low = math.floor(rank)
    high = math.ceil(rank)
    if low == high:
        return round(ordered[low], 4)
    weight = rank - low
    return round(ordered[low] * (1 - weight) + ordered[high] * weight, 4)


def latency_stats(values: list[float]) -> dict[str, Any]:
    if not values:
        return {
            "n": 0,
            "mean": None,
            "median": None,
            "std": None,
            "min": None,
            "max": None,
            "p95": None,
        }
    n = len(values)
    mean = sum(values) / n
    ordered = sorted(values)
    mid = n // 2
    median = (
        ordered[mid]
        if n % 2
        else (ordered[mid - 1] + ordered[mid]) / 2
    )
    variance = sum((x - mean) ** 2 for x in values) / n
    return {
        "n": n,
        "mean": round(mean, 4),
        "median": round(median, 4),
        "std": round(math.sqrt(variance), 4),
        "min": round(min(values), 4),
        "max": round(max(values), 4),
        "p95": percentile(values, 95),
    }


def wilson_interval(successes: int, n: int, z: float = 1.96) -> dict[str, float] | None:
    if n <= 0:
        return None
    p = successes / n
    denom = 1 + (z ** 2) / n
    center = (p + (z ** 2) / (2 * n)) / denom
    margin = (
        z * math.sqrt((p * (1 - p) / n) + (z ** 2) / (4 * n ** 2))
    ) / denom
    return {
        "low": round(max(0.0, center - margin), 4),
        "high": round(min(1.0, center + margin), 4),
    }


def confusion_matrix(
    y_true: Iterable[str],
    y_pred: Iterable[str],
    labels: tuple[str, ...] = ROUTES,
) -> dict[str, dict[str, int]]:
    matrix = {gold: {pred: 0 for pred in labels} for gold in labels}
    for gold, pred in zip(y_true, y_pred):
        if gold not in matrix or pred not in matrix[gold]:
            continue
        matrix[gold][pred] += 1
    return matrix


def _prf(tp: int, fp: int, fn: int) -> dict[str, float]:
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (
        2 * precision * recall / (precision + recall)
        if (precision + recall)
        else 0.0
    )
    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "support": tp + fn,
    }


def classification_report(
    y_true: list[str],
    y_pred: list[str],
    labels: tuple[str, ...] = ROUTES,
) -> dict[str, Any]:
    matrix = confusion_matrix(y_true, y_pred, labels)
    per_class = {}
    f1_values = []
    for label in labels:
        tp = matrix[label][label]
        fp = sum(matrix[other][label] for other in labels if other != label)
        fn = sum(matrix[label][other] for other in labels if other != label)
        stats = _prf(tp, fp, fn)
        stats["accuracy"] = round(
            tp / stats["support"] if stats["support"] else 0.0,
            4,
        )
        per_class[label] = stats
        if stats["support"]:
            f1_values.append(stats["f1"])

    correct = sum(1 for gold, pred in zip(y_true, y_pred) if gold == pred)
    n = len(y_true)
    return {
        "n": n,
        "accuracy": round(correct / n, 4) if n else None,
        "accuracy_ci95": wilson_interval(correct, n),
        "macro_f1": round(sum(f1_values) / len(f1_values), 4) if f1_values else None,
        "per_class": per_class,
        "confusion_matrix": matrix,
        "exact_counts": {
            "correct": correct,
            "incorrect": n - correct,
        },
    }


def precision_at_k(relevances: list[int], k: int) -> float:
    if k <= 0:
        return 0.0
    return sum(relevances[:k]) / k


def recall_at_k(relevances: list[int], k: int, n_relevant: int) -> float:
    if n_relevant <= 0:
        return 0.0
    return sum(relevances[:k]) / n_relevant


def mrr(relevances: list[int]) -> float:
    for index, value in enumerate(relevances, start=1):
        if value:
            return 1.0 / index
    return 0.0


def dcg(relevances: list[int], k: int) -> float:
    total = 0.0
    for index, value in enumerate(relevances[:k], start=1):
        total += value / math.log2(index + 1)
    return total


def ndcg_at_k(relevances: list[int], k: int) -> float:
    actual = dcg(relevances, k)
    ideal = dcg(sorted(relevances, reverse=True), k)
    if ideal == 0:
        return 0.0
    return actual / ideal


def source_level_relevances(
    retrieved_titles: list[str],
    preferred_sources: list[str],
) -> tuple[list[int], int]:
    preferred = {str(name).lower() for name in preferred_sources if name}
    seen_relevant: set[str] = set()
    relevances: list[int] = []
    for title in retrieved_titles:
        key = str(title).lower()
        is_relevant = key in preferred and key not in seen_relevant
        if is_relevant:
            seen_relevant.add(key)
        relevances.append(int(is_relevant or key in preferred))
    return relevances, len(preferred)


def retrieval_metrics_for_query(
    retrieved_titles: list[str],
    preferred_sources: list[str],
    k: int = 5,
) -> dict[str, float]:
    relevances, n_relevant = source_level_relevances(
        retrieved_titles,
        preferred_sources,
    )
    unique_hits = len({
        title.lower()
        for title in retrieved_titles[:k]
        if title.lower() in {s.lower() for s in preferred_sources}
    })
    binary = [
        1 if title.lower() in {s.lower() for s in preferred_sources} else 0
        for title in retrieved_titles
    ]
    return {
        "p_at_k": round(precision_at_k(binary, k), 4),
        "r_at_k": round(unique_hits / n_relevant if n_relevant else 0.0, 4),
        "mrr": round(mrr(binary), 4),
        "ndcg_at_k": round(ndcg_at_k(binary, k), 4),
    }


def mean_retrieval_metrics(
    rows: list[dict[str, float]],
) -> dict[str, float | None]:
    if not rows:
        return {"p_at_k": None, "r_at_k": None, "mrr": None, "ndcg_at_k": None}
    keys = ("p_at_k", "r_at_k", "mrr", "ndcg_at_k")
    return {
        key: round(sum(row[key] for row in rows) / len(rows), 4)
        for key in keys
    }


def extract_numbers(text: str) -> list[float]:
    import re

    values = []
    for raw in re.findall(r"-?\d+(?:[.,]\d+)?", str(text or "")):
        values.append(float(raw.replace(",", ".")))
    return values


def numbers_match(
    expected: list[float],
    observed: list[float],
    rel_tol: float = 0.02,
    abs_tol: float = 0.05,
) -> bool:
    if not expected:
        return False
    for gold in expected:
        if any(
            math.isclose(gold, found, rel_tol=rel_tol, abs_tol=abs_tol)
            for found in observed
        ):
            continue
        return False
    return True


def generation_metrics(
    answer: str,
    sources: list[dict[str, Any]],
    preferred_sources: list[str] | None = None,
) -> dict[str, Any]:
    import re

    valid_ids = {
        str(item.get("id"))
        for item in sources
        if item.get("id")
    }
    cited = list(dict.fromkeys(re.findall(r"\[(K\d+)\]", answer or "")))
    valid_cited = [item for item in cited if item in valid_ids]
    sentences = [
        part.strip()
        for part in re.split(r"(?<=[.!?])\s+", str(answer or "").strip())
        if part.strip()
    ]
    cited_sentences = [
        sentence for sentence in sentences if re.search(r"\[K\d+\]", sentence)
    ]
    citation_correctness = (
        len(valid_cited) / len(cited) if cited else 0.0
    )
    citation_completeness = (
        len(cited_sentences) / len(sentences) if sentences else 0.0
    )
    unsupported_claim_rate = (
        1.0 - citation_completeness if sentences else 1.0
    )
    source_titles = [
        str(item.get("title") or "")
        for item in sources
        if item.get("title")
    ]
    preferred = preferred_sources or []
    preferred_hit = 0.0
    if preferred:
        hits = {
            title.lower()
            for title in source_titles
            if title.lower() in {name.lower() for name in preferred}
        }
        preferred_hit = len(hits) / len(preferred)

    refusal = any(
        token in (answer or "").casefold()
        for token in (
            "veteriner hekim",
            "tanı koy",
            "antibiyotik",
            "sistem bu tür kararları veremez",
        )
    )
    return {
        "citation_correctness": round(citation_correctness, 4),
        "citation_completeness": round(citation_completeness, 4),
        "unsupported_claim_rate": round(unsupported_claim_rate, 4),
        "preferred_source_hit_rate": round(preferred_hit, 4),
        "cited_ids": cited,
        "sentence_count": len(sentences),
        "refuses_diagnosis": refusal,
    }


def error_category(row: dict[str, Any]) -> str | None:
    if row.get("error"):
        return "system_error"
    if row.get("expected_route") != row.get("predicted_route"):
        return "routing_error"
    if row.get("expected_route") == "SQL":
        if row.get("sql_executed") is False:
            return "sql_execution_error"
        if row.get("numerical_correct") is False:
            return "sql_nl_mismatch"
        if row.get("execution_correct") is False:
            return "sql_execution_error"
    if row.get("expected_route") == "RAG":
        if row.get("retrieval", {}).get("r_at_k", 1) == 0:
            return "retrieval_miss"
        if (row.get("generation") or {}).get("unsupported_claim_rate", 0) >= 0.5:
            return "unsupported_generation"
    if row.get("expected_route") == "HYBRID":
        if row.get("hybrid_e2e_correct") is False:
            return "hybrid_e2e_error"
    if row.get("expected_behavior") == "refuse_diagnosis":
        if not (row.get("generation") or {}).get("refuses_diagnosis"):
            return "diagnosis_leak"
    return None


def summarize_errors(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for row in rows:
        category = error_category(row)
        if category:
            counts[category] += 1
    return dict(Counter(counts))
