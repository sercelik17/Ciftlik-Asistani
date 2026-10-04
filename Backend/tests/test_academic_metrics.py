from thesis_eval.metrics import (
    classification_report,
    dcg,
    generation_metrics,
    latency_stats,
    ndcg_at_k,
    numbers_match,
    retrieval_metrics_for_query,
)
from thesis_rag.sql_guard import is_read_only_sql, reject_unsafe_sql
from thesis_rag.safety import is_diagnosis_or_treatment_request


def test_classification_report_includes_chat_and_macro_f1():
    y_true = ["RAG", "SQL", "HYBRID", "CHAT", "RAG"]
    y_pred = ["RAG", "SQL", "HYBRID", "CHAT", "SQL"]
    report = classification_report(y_true, y_pred)
    assert report["exact_counts"]["correct"] == 4
    assert report["confusion_matrix"]["RAG"]["SQL"] == 1
    assert report["macro_f1"] is not None
    assert "CHAT" in report["per_class"]
    assert report["accuracy_ci95"]["low"] <= report["accuracy"] <= report["accuracy_ci95"]["high"]


def test_retrieval_metrics_known_ranking():
    titles = [
        "FAO_Mastitis_Dairy_Manual.pdf",
        "other.pdf",
        "Kurt_2019_Mastitis_Kuru_Gecis_Donemi.pdf",
    ]
    preferred = [
        "FAO_Mastitis_Dairy_Manual.pdf",
        "Kurt_2019_Mastitis_Kuru_Gecis_Donemi.pdf",
    ]
    metrics = retrieval_metrics_for_query(titles, preferred, k=3)
    assert metrics["mrr"] == 1.0
    assert metrics["p_at_k"] == round(2 / 3, 4)
    assert metrics["r_at_k"] == 1.0
    assert 0 < metrics["ndcg_at_k"] <= 1


def test_ndcg_perfect_ranking_is_one():
    assert ndcg_at_k([1, 1, 0], 3) == 1.0
    assert dcg([1, 0], 2) > 0


def test_latency_stats_include_p95():
    stats = latency_stats([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
    assert stats["n"] == 10
    assert stats["mean"] == 5.5
    assert stats["p95"] is not None
    assert stats["min"] == 1
    assert stats["max"] == 10


def test_sql_guard_blocks_mutations():
    assert is_read_only_sql("SELECT * FROM inekler")
    assert is_read_only_sql("WITH x AS (SELECT 1) SELECT * FROM x")
    assert not is_read_only_sql("DELETE FROM inekler")
    assert not is_read_only_sql("DROP TABLE alarmlar")
    assert reject_unsafe_sql("UPDATE inekler SET isim='x'") is not None


def test_diagnosis_detector_and_generation_refusal():
    assert is_diagnosis_or_treatment_request(
        "Bu inekte mastitis var mı, antibiyotik vermeli miyim?"
    )
    metrics = generation_metrics(
        "Mastitis süt verimini azaltabilir. [K1]\n\nBu sistem veteriner hekim tanısının yerine geçmez.",
        [{"id": "K1", "title": "FAO_Mastitis_Dairy_Manual.pdf"}],
        ["FAO_Mastitis_Dairy_Manual.pdf"],
    )
    assert metrics["citation_correctness"] == 1.0
    assert metrics["refuses_diagnosis"] is True


def test_numeric_match_accepts_comma_decimals():
    assert numbers_match([7.8], [7, 8, 7.8])


def test_deterministic_chat_and_hybrid_routing():
    from thesis_rag.route_rules import deterministic_route

    assert deterministic_route("Merhaba") == "CHAT"
    assert deterministic_route("Teşekkürler") == "CHAT"
    assert deterministic_route("Nasılsın?") == "CHAT"
    assert deterministic_route("Mastitis nedir?") == "RAG"
    assert deterministic_route("Bugün toplam kaç litre süt aldım?") == "SQL"
    assert deterministic_route("Serap'ın sütü neden düştü?") == "HYBRID"
