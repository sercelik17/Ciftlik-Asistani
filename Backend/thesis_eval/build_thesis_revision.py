# -*- coding: utf-8 -*-
"""
10 Ekim 2026 tarihli yeniden değerlendirme raporunun belge tarafı gereksinimlerini
mevcut deney kayıtlarından üretir.

Girdi (evaluation_output/ ve evaluation_sets/):
  routing_report.json, retrieval_report.json, generation_report.json,
  sql_gold_results.json, fusion_ablation_pilot.json, reproducibility.json,
  final_heldout_set.json, ../tez_test_seti_100.json, ../knowledge_base/*.pdf

Çıktı (evaluation_output/revizyon_2026_10_10/):
  revision_data.json          -> revise_thesis.py bu dosyayı okuyarak Word'e tablo basar
  tez_revizyon_paketi.html    -> teze yapıştırılacak metin ve tablolar (tarayıcıda açılır)
  ek_*.csv                    -> ekler için ham tablolar

Çalıştırma:
  cd Backend
  python -m thesis_eval.build_thesis_revision
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import math
import re
import statistics
from collections import Counter
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
OUT_DIR_DEFAULT = BACKEND_DIR / "evaluation_output" / "revizyon_2026_10_10"
EVAL_OUT = BACKEND_DIR / "evaluation_output"
EVAL_SETS = BACKEND_DIR / "evaluation_sets"
KB_DIR = BACKEND_DIR / "knowledge_base"

NEW_TITLE = (
    "Süt Sığırcılığında Yapılandırılmış Çiftlik Verileri ile Bilimsel Bilginin "
    "Entegrasyonu için RAG Tabanlı Sohbet Asistanı"
)

# Tam bibliyografik künye. Kaynak: PDF ilk sayfaları ve PDF üst verisi.
# "verify" alanı, PDF'den tek başına kesinleştirilemeyen bilgiyi işaretler.
CORPUS_BIBLIO = {
    "FAO_Mastitis_Dairy_Manual.pdf": {
        "citation": (
            "FAO (1993; elektronik baskı 2008). Small-scale Dairy Farming Manual, "
            "Vol. 5 (Husbandry Units 10.1–11.4; Unit 10.5: Mastitis). Regional Dairy "
            "Development and Training Team for Asia and Pacific, FAO Regional Office "
            "for Asia and the Pacific, Bangkok / FAO, Rome."
        ),
        "year": "1993/2008",
        "institution": "FAO",
        "doc_type": "uluslararası rehber",
        "verify": "",
    },
    "Kurt_2019_Mastitis_Kuru_Gecis_Donemi.pdf": {
        "citation": (
            "Kurt, S., Çolakoğlu, H. E., Yazlık, M. O., Vural, M. R., Küplülü, Ş. (2019). "
            "Sütçü ineklerde mastitis yönünden kuru ve geçiş dönemlerinin önemi. "
            "Atatürk Üniversitesi Veteriner Bilimleri Dergisi, 14(1), 107–113. "
            "DOI: 10.17094/ataunivbd.407022"
        ),
        "year": "2019",
        "institution": "Ankara Üniversitesi Veteriner Fakültesi",
        "doc_type": "hakemli derleme",
        "verify": "",
    },
    "Darbaz_Ergene_2015_Somatik_Hucre_Sayisi.pdf": {
        "citation": (
            "Darbaz, İ., Ergene, O. (2015). Sürü meme sağlığı yönetiminde somatik hücre "
            "sayısının önemi. Erciyes Üniversitesi Veteriner Fakültesi Dergisi, 12(3), 203–210."
        ),
        "year": "2015",
        "institution": "Yakın Doğu Üniversitesi Veteriner Fakültesi",
        "doc_type": "hakemli derleme",
        "verify": "",
    },
    "Yalcin_Cakmak_2022_Somatik_Hucre_Sut_Kalitesi.pdf": {
        "citation": (
            "Yalçın, H., Çakmak, T. (2022). İnek sütlerinde somatik hücre sayısı ve bazı "
            "parametrelerin araştırılması. Manas Journal of Agriculture, Veterinary and "
            "Life Sciences, 12(1), 81–87. DOI: 10.53518/mjavl.1092994"
        ),
        "year": "2022",
        "institution": "MJAVL",
        "doc_type": "hakemli araştırma makalesi",
        "verify": "",
    },
    "FAO_2012_Balanced_Feeding.pdf": {
        "citation": (
            "FAO (2012). Balanced feeding for improving livestock productivity – Increase in "
            "milk production and nutrient use efficiency and decrease in methane emission, "
            "by M. R. Garg. FAO Animal Production and Health Paper No. 173. Rome."
        ),
        "year": "2012",
        "institution": "FAO",
        "doc_type": "uluslararası teknik rapor",
        "verify": "",
    },
    "Tennessee_Managing_Intake_Dairy_Cows.pdf": {
        "citation": (
            "Bernard, J. K., Montgomery, M. J. (1997). Managing Intake of Lactating Dairy "
            "Cows. The University of Tennessee Agricultural Extension Service, PB 1598."
        ),
        "year": "1997",
        "institution": "University of Tennessee Extension",
        "doc_type": "üniversite yayım bülteni",
        "verify": "Yıl PDF üst verisinden (1997-12); basılı künyede teyit edilmeli.",
    },
    "Cornell_Transition_Cow_Metabolic.pdf": {
        "citation": (
            "Overton, T. R. (2009). Effective transition cow management to maximize Internal "
            "Herd Growth. Department of Animal Science, Cornell University (sunum notları)."
        ),
        "year": "2009",
        "institution": "Cornell University",
        "doc_type": "üniversite sunum/ders notu",
        "verify": "Yıl PDF üst verisinden (2009-07); yayın yeri teyit edilmeli.",
    },
    "Wisconsin_Fresh_Cow_Milk_Fever.pdf": {
        "citation": (
            "University of Wisconsin–Madison Division of Extension (2023). The Fresh Cow: "
            "Milk Fever. Dairy fact sheet."
        ),
        "year": "2023",
        "institution": "UW–Madison Division of Extension",
        "doc_type": "üniversite bilgi notu",
        "verify": "Yıl PDF üst verisinden (2023-09).",
    },
    "UF_IFAS_Dairy_Calf_Nutrition.pdf": {
        "citation": (
            "Moriel, P., Batistel, F. (2021). Nutrition at Early Stages of Life Determines the "
            "Future Growth and Reproductive Performance of Dairy Calves. UF/IFAS Extension, "
            "AN336. DOI: 10.32473/edis-an336-2021"
        ),
        "year": "2021",
        "institution": "University of Florida IFAS Extension",
        "doc_type": "üniversite yayım belgesi",
        "verify": "",
    },
    "USU_2026_Colostrum_Dairy_Calves.pdf": {
        "citation": (
            "Utah State University Extension (2026). Colostrum management fact sheet for "
            "dairy calves (A. Snarr vd.)."
        ),
        "year": "2026",
        "institution": "Utah State University Extension",
        "doc_type": "üniversite bilgi notu",
        "verify": "Tam başlık ve yazar listesi PDF kapak görselinden teyit edilmeli.",
    },
    "DCRC_Dairy_Cow_Reproductive_Management.pdf": {
        "citation": (
            "Fricke, P. M. (2018). Evolution of timed AI protocols and overview of the 2018 "
            "DCRC Reproductive Management Strategies protocol sheet for dairy cows. Dairy "
            "Cattle Reproduction Council (DCRC) Annual Meeting Proceedings."
        ),
        "year": "2018",
        "institution": "Dairy Cattle Reproduction Council",
        "doc_type": "mesleki bildiri/rehber",
        "verify": "",
    },
    "Wisconsin_High_Fertility_Cycle.pdf": {
        "citation": (
            "Fricke, P. M., Wiltbank, M. C., Pursley, J. R. (2023). The High Fertility Cycle. "
            "University of Wisconsin–Madison Division of Extension."
        ),
        "year": "2023",
        "institution": "UW–Madison Division of Extension",
        "doc_type": "üniversite yayım belgesi",
        "verify": "",
    },
    "Ocal_Guven_Cedden_2026_Dairy_Cattle_Welfare.pdf": {
        "citation": (
            "Öcal, G. O., Güven, F. M., Cedden, F. (2026). Evaluation of housing and management "
            "conditions affecting animal welfare in dairy cattle farms in Ankara Province, "
            "Türkiye. ADÜ Ziraat Dergisi, 23(1), 47–53. DOI: 10.25308/aduziraat.1850888"
        ),
        "year": "2026",
        "institution": "Adnan Menderes Üniversitesi",
        "doc_type": "hakemli araştırma makalesi",
        "verify": "",
    },
    "WOAH_Dairy_Cattle_Welfare.pdf": {
        "citation": (
            "WOAH (2024). Terrestrial Animal Health Code, Chapter 7.11: Animal welfare and "
            "dairy cattle production systems. World Organisation for Animal Health, Paris."
        ),
        "year": "2024",
        "institution": "WOAH (OIE)",
        "doc_type": "uluslararası standart",
        "verify": "",
    },
    "FAO_IDF_Good_Dairy_Farming.pdf": {
        "citation": (
            "FAO & IDF (2011). Guide to Good Dairy Farming Practice. FAO Animal Production and "
            "Health Guidelines No. 8. Rome."
        ),
        "year": "2011",
        "institution": "FAO / International Dairy Federation",
        "doc_type": "uluslararası rehber",
        "verify": "",
    },
    "Codex_Milk_Hygiene.pdf": {
        "citation": (
            "FAO & WHO (2007). Codex Alimentarius: Milk and Milk Products (First edition). "
            "Joint FAO/WHO Food Standards Programme, Rome. ISBN 978-92-5-105837-4"
        ),
        "year": "2007",
        "institution": "Codex Alimentarius Commission (FAO/WHO)",
        "doc_type": "uluslararası standart",
        "verify": "ISBN son hanesi PDF'de kesilmiş; künyeden teyit edilmeli.",
    },
}

THEME_TR = {
    "01_mastitis": "Mastitis",
    "02_sut_kalitesi": "Süt kalitesi",
    "03_besleme": "Besleme",
    "04_metabolik_hastaliklar": "Metabolik hastalıklar",
    "05_buzagi_sagligi": "Buzağı sağlığı",
    "06_ureme": "Üreme",
    "07_hayvan_refahi": "Hayvan refahı",
    "08_sut_hijyeni": "Süt hijyeni",
}


# ----------------------------------------------------------------------------
# yardımcılar
# ----------------------------------------------------------------------------
def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def fmt(x, nd=2) -> str:
    if x is None:
        return "—"
    if isinstance(x, float) and math.isnan(x):
        return "—"
    s = f"{x:.{nd}f}"
    return s.replace(".", ",")


def pct(values: list[float], p: float) -> float:
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    rank = (len(ordered) - 1) * p / 100
    lo, hi = math.floor(rank), math.ceil(rank)
    if lo == hi:
        return ordered[lo]
    return ordered[lo] * (hi - rank) + ordered[hi] * (rank - lo)


def dist(values: list[float]) -> dict:
    if not values:
        return {"n": 0}
    return {
        "n": len(values),
        "mean": statistics.mean(values),
        "median": statistics.median(values),
        "sd": statistics.pstdev(values) if len(values) > 1 else 0.0,
        "min": min(values),
        "max": max(values),
        "p90": pct(values, 90),
        "p95": pct(values, 95),
    }


def bootstrap_ci(diffs: list[float], n_boot: int = 10000, seed: int = 0) -> tuple[float, float]:
    import random

    rng = random.Random(seed)
    n = len(diffs)
    means = []
    for _ in range(n_boot):
        sample = [diffs[rng.randrange(n)] for _ in range(n)]
        means.append(sum(sample) / n)
    means.sort()
    return means[int(0.025 * n_boot)], means[int(0.975 * n_boot) - 1]


_TR = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU")


def tokens(text: str) -> set[str]:
    text = text.translate(_TR).casefold()
    return {t for t in re.findall(r"[a-z0-9]+", text) if len(t) > 2}


def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


# ----------------------------------------------------------------------------
# bölümler
# ----------------------------------------------------------------------------
def build_routing(routing: dict, repro: dict, config_hash: str) -> dict:
    rows = []
    for r in routing["rows"]:
        rows.append({
            "query_id": r["id"],
            "query_text": r["question"],
            "gold_label": r["expected_route"],
            "predicted_label": r["predicted_route"],
            "mechanism": "kural" if r.get("router_backend") == "rules" else "LLM fallback",
            "correct": bool(r["route_correct"]),
            "run_timestamp_utc": repro.get("captured_at_utc", ""),
            "configuration_hash": config_hash,
        })
    mech = Counter(r["mechanism"] for r in rows)
    return {
        "n": routing["n"],
        "accuracy": routing["accuracy"],
        "ci95": routing["accuracy_ci95"],
        "macro_f1": routing["macro_f1"],
        "per_class": routing["per_class"],
        "confusion_matrix": routing["confusion_matrix"],
        "mechanism_counts": dict(mech),
        "rows": rows,
    }


def build_overlap(heldout: list[dict], pilot: list[dict]) -> dict:
    pilot_tok = [(p["id"], p["question"], tokens(p["question"])) for p in pilot]
    pilot_norm = {re.sub(r"\s+", " ", p["question"].strip().casefold()) for p in pilot}
    exact = 0
    sims = []
    high = []
    for h in heldout:
        q = re.sub(r"\s+", " ", h["question"].strip().casefold())
        if q in pilot_norm:
            exact += 1
        ht = tokens(h["question"])
        best = max(((jaccard(ht, pt), pid, pq) for pid, pq, pt in pilot_tok), default=(0.0, "", ""))
        sims.append(best[0])
        if best[0] >= 0.5:
            high.append({"heldout_id": h["id"], "heldout": h["question"], "pilot_id": best[1], "pilot": best[2], "jaccard": round(best[0], 3)})
    buckets = Counter()
    for s in sims:
        if s < 0.2:
            buckets["<0,20"] += 1
        elif s < 0.35:
            buckets["0,20–0,34"] += 1
        elif s < 0.5:
            buckets["0,35–0,49"] += 1
        else:
            buckets["≥0,50"] += 1
    return {
        "heldout_n": len(heldout),
        "pilot_n": len(pilot),
        "exact_duplicates": exact,
        "max_jaccard_mean": statistics.mean(sims),
        "max_jaccard_median": statistics.median(sims),
        "max_jaccard_max": max(sims),
        "buckets": dict(buckets),
        "high_similarity_pairs": high,
    }


def build_retrieval(retrieval: dict) -> dict:
    rows = []
    identical_rankings = 0
    diffs = {"p_at_k": [], "mrr": [], "ndcg_at_k": [], "r_at_k": []}
    for r in retrieval["rows"]:
        m = r["modes"]
        if m["faiss"]["retrieved_titles"] == m["hybrid"]["retrieved_titles"]:
            identical_rankings += 1
        for key in diffs:
            diffs[key].append(m["faiss"][key] - m["hybrid"][key])
        rows.append({
            "query_id": r["id"],
            "query_text": r["question"],
            "n_relevant_docs": len(r["preferred_sources"]),
            "preferred_sources": "; ".join(r["preferred_sources"]),
            **{f"{sys}_{k}": m[sys][k] for sys in ("bm25", "faiss", "hybrid") for k in ("p_at_k", "r_at_k", "mrr", "ndcg_at_k")},
        })
    paired = {}
    for key, d in diffs.items():
        lo, hi = bootstrap_ci(d)
        wins = sum(1 for x in d if x > 0)
        losses = sum(1 for x in d if x < 0)
        ties = sum(1 for x in d if x == 0)
        paired[key] = {
            "mean_diff": sum(d) / len(d),
            "ci95_low": lo,
            "ci95_high": hi,
            "faiss_better": wins,
            "hybrid_better": losses,
            "ties": ties,
        }
    # BM25'e karşı hibrit (hibritin BM25'i iyileştirdiğini gösteren eşleştirilmiş fark)
    diffs_h_b = [r["hybrid_p_at_k"] - r["bm25_p_at_k"] for r in rows]
    lo, hi = bootstrap_ci(diffs_h_b)
    hybrid_vs_bm25 = {"mean_diff": sum(diffs_h_b) / len(diffs_h_b), "ci95_low": lo, "ci95_high": hi}
    return {
        "n": retrieval["n"],
        "k": retrieval["k"],
        "backend_note": retrieval.get("backend", ""),
        "summary": retrieval["summary"],
        "identical_top5_faiss_hybrid": identical_rankings,
        "paired_faiss_minus_hybrid": paired,
        "paired_hybrid_minus_bm25_p_at_k": hybrid_vs_bm25,
        "rows": rows,
    }


def build_generation(gen: dict) -> dict:
    rows = []
    cats = Counter()
    for r in gen["rows"]:
        g = r["generation"]
        ans = (r.get("answer") or "").strip()
        refusal = bool(g.get("refuses_diagnosis")) and r.get("expected_behavior") == "refuse_diagnosis"
        if refusal:
            cat = "tanı reddi (beklenen davranış)"
        elif not g.get("cited_ids"):
            cat = "atıf yok"
        elif g.get("citation_completeness", 0) >= 0.99:
            cat = "tam atıf"
        else:
            cat = "kısmi atıf"
        truncated = bool(ans) and not refusal and ans[-1] not in ".!?»\")"
        mixed_language = bool(re.search(r"\b(the|and|of|with|for|which|is|are)\b", ans))
        cats[cat] += 1
        if truncated:
            cats["kesik yanıt (token sınırı)"] += 1
        if mixed_language:
            cats["İngilizce sözcük kalıntısı (sezgisel)"] += 1
        rows.append({
            "query_id": r["id"],
            "query_text": r["question"],
            "citation_correctness": g["citation_correctness"],
            "citation_completeness": g["citation_completeness"],
            "unsupported_claim_rate": g["unsupported_claim_rate"],
            "preferred_source_hit_rate": g["preferred_source_hit_rate"],
            "cited_ids": " ".join(g.get("cited_ids") or []),
            "sentence_count": g["sentence_count"],
            "refuses_diagnosis": g["refuses_diagnosis"],
            "category": cat,
            "truncated": truncated,
            "mixed_language": mixed_language,
            "latency_sec": r["latency_sec"],
            "retrieved_sources": "; ".join(f"{s['id']}={s['title']}:{s.get('page')}" for s in r.get("sources", [])),
        })
    lat_all = [r["latency_sec"] for r in rows]
    lat_llm = [r["latency_sec"] for r in rows if not (r["refuses_diagnosis"] and r["latency_sec"] < 1)]
    return {
        "n": gen["summary"]["n"],
        "summary": gen["summary"],
        "error_categories": dict(cats),
        "latency_all": dist(lat_all),
        "latency_llm_only": dist(lat_llm),
        "rows": rows,
    }


def build_sql(sql: dict) -> dict:
    rows = []
    for r in sql["rows"]:
        ok = bool(r["ok"])
        observed = r["gold_result"]
        if ok:
            error_type = "—"
            comparison = "beklenen = gözlenen"
            expected = observed
        else:
            m = re.match(r"(\w+)\(", observed)
            error_type = f"şema uyumsuzluğu ({m.group(1) if m else 'hata'})"
            comparison = "karşılaştırılamadı"
            expected = "tanımsız (sütun şemada yok)"
        rows.append({
            "id": r["id"],
            "question": r["question"],
            "executed_query": r["gold_sql"],
            "expected_value": expected,
            "observed_value": observed if ok else observed.split("\\n")[0],
            "run_status": "çalıştı" if ok else "hata",
            "comparison_result": comparison,
            "error_type": error_type,
        })
    ids = [r["id"] for r in rows]
    return {
        "n": sql["n"],
        "executed_ok": sql["executed_ok"],
        "failed": sql["failed"],
        "ids_unique": len(ids) == len(set(ids)),
        "failed_ids": [r["id"] for r in rows if r["run_status"] != "çalıştı"],
        "rows": rows,
    }


def build_corpus(manifest: dict) -> dict:
    try:
        import pypdf
        from langchain_text_splitters import RecursiveCharacterTextSplitter
    except ImportError as exc:  # pragma: no cover
        raise SystemExit(f"pypdf ve langchain-text-splitters gerekli: {exc}")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=900, chunk_overlap=150, separators=["\n\n", "\n", ". ", " ", ""]
    )
    by_file = {}
    for p in sorted(KB_DIR.rglob("*.pdf")):
        reader = pypdf.PdfReader(str(p))
        texts = []
        for page in reader.pages:
            try:
                texts.append(page.extract_text() or "")
            except Exception:
                texts.append("")
        chunks = sum(len(splitter.split_text(t)) for t in texts if t.strip())
        by_file[p.name] = {
            "pages": len(reader.pages),
            "pages_with_text": sum(1 for t in texts if t.strip()),
            "chunks": chunks,
            "category": p.parent.name,
        }
    rows = []
    for d in manifest["documents"]:
        f = d["file"]
        bib = CORPUS_BIBLIO.get(f, {})
        stats = by_file.get(f, {})
        rows.append({
            "id": d["id"],
            "file": f,
            "citation": bib.get("citation", f),
            "year": bib.get("year", d.get("year") or "—"),
            "institution": bib.get("institution", d.get("publisher", "")),
            "doc_type": bib.get("doc_type", d.get("type", "")),
            "theme": THEME_TR.get(d["category"], d.get("theme", "")),
            "pages": stats.get("pages"),
            "chunks": stats.get("chunks"),
            "verify": bib.get("verify", ""),
        })
    return {
        "document_count": len(rows),
        "total_pages": sum(r["pages"] or 0 for r in rows),
        "total_chunks": sum(r["chunks"] or 0 for r in rows),
        "index_manifest_pages": manifest.get("page_document_count_in_index"),
        "index_manifest_chunks": manifest.get("chunk_count"),
        "selection_criteria": manifest.get("selection_criteria", []),
        "rows": rows,
    }


def build_config(repro: dict) -> tuple[list[dict], str]:
    pk = repro.get("packages", {})
    gen = repro.get("generation", {})
    ret = repro.get("retrieval", {})
    plat = repro.get("platform", {})
    models = repro.get("models", {})
    hash_src = json.dumps({"models": models, "generation": gen, "retrieval": ret}, sort_keys=True)
    config_hash = hashlib.sha256(hash_src.encode("utf-8")).hexdigest()[:12]
    rows = [
        ("Üretim LLM", f"Ollama `{models.get('rag_llm')}` (varsayılan etiket; 7B); temperature={gen.get('temperature')}, seed={gen.get('seed')}, num_predict={gen.get('num_predict')}, num_ctx={gen.get('num_ctx')}, num_gpu=0 (CPU çıkarımı)"),
        ("Yönlendirici", "1. aşama kural tabanlı (route_rules.py); eşleşme yoksa 2. aşama Ollama `mistral` (num_ctx=1024, num_predict=16, temperature=0)"),
        ("SQL kanalı LLM", f"LangGraph araç-çağrı ajanı, Ollama `{models.get('local_llm')}`; 8 parametrik SQL aracı + yalnızca SELECT üreten dinamik sorgu aracı"),
        ("Gömme modeli", f"Ollama `{models.get('embed_model')}` (BGE-M3, 1024 boyut)"),
        ("Vektör indeksi", f"FAISS {ret.get('faiss_index')} ({ret.get('faiss_metric', 'l2').upper()} uzaklık), faiss-cpu {pk.get('faiss')}"),
        ("Sözcüksel arama", f"BM25Okapi (rank_bm25), k1={ret.get('bm25_k1')}, b={ret.get('bm25_b')}"),
        ("Birleştirme", f"{ret.get('fusion_method')}; yoğun {ret.get('dense_weight')} / seyrek {ret.get('sparse_weight')}; k={int(ret.get('rrf_k', 60))}"),
        ("Top-K", f"FAISS {ret.get('vector_top_k')}, BM25 {ret.get('bm25_top_k')}, nihai {ret.get('final_top_k')}"),
        ("Parçalama", f"RecursiveCharacterTextSplitter, {ret.get('chunk_size')} karakter / {ret.get('chunk_overlap')} örtüşme; ayırıcılar: paragraf, satır, cümle, boşluk"),
        ("Bilgi tabanı", f"{repro.get('index_manifest', {}).get('document_count')} sayfa birimi, {repro.get('index_manifest', {}).get('chunk_count')} parça, 16 PDF"),
        ("Veritabanı", f"{repro.get('database', {}).get('engine')} ({repro.get('database', {}).get('name')}); kayıtlar sentetik prototip verisi; SQL muhafızı yalnızca SELECT/WITH…SELECT kabul eder (sql_guard.py)"),
        ("Python / paketler", f"Python {repro.get('python', '').split(' ')[0]}; langchain {pk.get('langchain')}, langchain-core {pk.get('langchain_core')}, langchain-community {pk.get('langchain_community')}, langchain-ollama {pk.get('langchain_ollama')}, langgraph {pk.get('langgraph')}, psycopg2 {pk.get('psycopg2')}"),
        ("İşletim sistemi / donanım", f"{plat.get('system')} {plat.get('release')} ({plat.get('machine')}); CPU: {plat.get('processor')}; GPU kullanılmadı"),
        ("İstemci / sunucu", "FastAPI (uvicorn, 127.0.0.1:8001) + React Native/Expo web istemcisi; Ollama 127.0.0.1:11434"),
        ("Deney kaydı", f"captured_at {repro.get('captured_at_utc')}; yapılandırma özeti (SHA-256/12) {config_hash}"),
        ("Model sürüm özeti (digest)", "Ollama model digest'i deney sırasında kaydedilmemiştir (sınırlılık); `ollama show mistral` / `ollama show bge-m3` çıktısı savunma öncesi eklenmelidir"),
    ]
    return [{"component": c, "value": v} for c, v in rows], config_hash


def extract_prompts() -> dict:
    prompts = {}
    rag = (BACKEND_DIR / "thesis_rag" / "rag_chain.py").read_text(encoding="utf-8")
    m = re.search(r'"system",\s*"""(.*?)"""', rag, re.S)
    if m:
        prompts["rag_system"] = m.group(1).strip()
    m = re.search(r'"human",\s*"""(.*?)"""', rag, re.S)
    if m:
        prompts["rag_human"] = m.group(1).strip()
    router = (BACKEND_DIR / "thesis_rag" / "query_router.py").read_text(encoding="utf-8")
    m = re.search(r'"system",\s*"""(.*?)"""', router, re.S)
    if m:
        prompts["router_system"] = m.group(1).strip()
    safety = (BACKEND_DIR / "thesis_rag" / "safety.py").read_text(encoding="utf-8")
    m = re.search(r'VETERINARY_DISCLAIMER = \((.*?)\)\n', safety, re.S)
    if m:
        prompts["veterinary_disclaimer"] = " ".join(
            s.strip().strip('"') for s in m.group(1).strip().splitlines()
        )
    return prompts


# ----------------------------------------------------------------------------
# metinler (teze yapıştırılacak)
# ----------------------------------------------------------------------------
def build_texts(data: dict) -> dict:
    rt = data["retrieval"]
    gn = data["generation"]
    sq = data["sql"]
    ov = data["overlap"]
    s = rt["summary"]
    pd = rt["paired_faiss_minus_hybrid"]
    lat = gn["latency_llm_only"]
    lat_all = gn["latency_all"]
    gs = gn["summary"]
    cats = gn["error_categories"]
    n_two_docs = sum(1 for r in rt["rows"] if r["n_relevant_docs"] == 2)
    n_one_doc = sum(1 for r in rt["rows"] if r["n_relevant_docs"] == 1)
    high_pairs = ov["high_similarity_pairs"]
    high_by_class = Counter(p["heldout_id"].split("-")[1][:3] for p in high_pairs)

    rq_rows = [
        ("RQ1 – Dört sınıfta yönlendirme", "Nicel olarak ölçüldü",
         "Held-out n = 89; 89/89, Macro-F1 = 1,00; %95 Wilson GA 0,96–1,00; tam soru–etiket–tahmin kaydı Ek Tablo 2'de."),
        ("RQ2 – BM25 / FAISS / RRF erişim kıyası", "Nicel olarak ölçüldü",
         "n = 33, K = 5; P@5, R@5, MRR, nDCG@5 (Tablo 4.5); eşleştirilmiş fark ve bootstrap GA Bölüm 5.2'de; gold etiket protokolü Bölüm 3.7'de."),
        ("RQ3 – Birleştirme ağırlığının etkisi", "Pilot sette ölçüldü (keşifsel)",
         "n = 50; 50/50, 60/40, 70/30; 60/40 ile 70/30 eşit; 60/40 önceden belirlenmiş eşitlik-bozma kuralıyla seçildi."),
        ("RQ4 – SQL doğal dil sorgu başarısı", "ÖLÇÜLMEDİ (yalnızca referans sorgu çalıştırılabilirliği)",
         "24 referans sorgunun 23'ü PostgreSQL'de çalıştı (Ek Tablo 1). Modelin ürettiği SQL'in execution accuracy'si ve sayısal sözelleştirme doğruluğu bu sürümde raporlanmamıştır."),
        ("RQ5 – Kaynak bağlılığı ve desteksiz iddia", "Otomatik vekil ölçütlerle ölçüldü; uzman puanı yok",
         f"n = 33; atıf doğruluğu {fmt(gs['mean_citation_correctness'])}, atıf tamlığı {fmt(gs['mean_citation_completeness'])}, desteksiz iddia oranı {fmt(gs['mean_unsupported_claim_rate'])} (Bölüm 4.6). İki değerlendiricili 0–2 puanlama ve gold cevap seti yapılmamıştır."),
        ("HYBRID uçtan uca doğruluk", "ÖLÇÜLMEDİ",
         "16 soruda yalnızca yönlendirme ölçüldü; SQL + kanıt + sentez bileşik 0/1 puanı yoktur."),
    ]

    texts = {}
    texts["title_suggestion"] = NEW_TITLE

    texts["rq_table"] = rq_rows

    texts["sec_3_7_protocol"] = (
        "Değerlendirme protokolü ve ölçülen/ölçülmeyen bileşenler. Bu çalışmada üç düzey ayrı tutulmuştur: "
        "(i) yönlendirme doğruluğu, (ii) bilgi erişimi (retrieval) kalitesi ve (iii) yanıt üretimi kalitesi. "
        "Yönlendirme ve retrieval için nihai nicel sonuçlar held-out kümede ölçülmüştür. Yanıt üretimi için yalnızca "
        "otomatik vekil ölçütler (atıf doğruluğu, atıf tamlığı, desteksiz iddia oranı) hesaplanmış; gold cevap seti, "
        "iki bağımsız değerlendiricili 0–2 puanlama ve Cohen's κ bu teslimde yapılmamıştır. Modelin ürettiği SQL'in "
        "execution accuracy'si ile HYBRID uçtan uca doğruluk ölçülmemiştir; bunlar 'planlanan' olarak sınıflandırılır. "
        "Gold relevance etiketleri belge düzeyindedir: her RAG sorusu yazılırken, soru metninden bağımsız olarak, "
        "yanıtı taşıması beklenen bir veya iki kaynak belge (preferred_sources) tez yazarı tarafından önceden "
        "atanmıştır; etiketleme tek değerlendiriciyle ve sistem çıktısı görülmeden yapılmıştır. İlgililik ikilidir; "
        "nDCG@5 ikili kazançla hesaplanmıştır. Recall@5 paydası, soru için atanmış ilgili belge sayısıdır "
        f"({rt['n']} RAG sorusunun {n_two_docs}'sinde iki, {n_one_doc}'inde bir belge). Birden fazla değerlendirici "
        "bulunmadığından değerlendiriciler arası uyum raporlanamamıştır; bu bir sınırlılıktır."
    )

    texts["sec_4_4_fix"] = (
        "Bilgi erişimi düzeyindeki nihai nicel sonuçlar (Precision@5, Recall@5, MRR ve nDCG@5) held-out RAG "
        "kümesinde üç yöntem için Tablo 4.5'te verilmiştir. Yanıt üretimi düzeyinde ise yalnızca otomatik vekil "
        "ölçütler (atıf doğruluğu, atıf tamlığı, desteksiz iddia oranı) hesaplanmış olup Bölüm 4.6'da sunulmuştur; "
        "uzman puanlı faithfulness ve yanıt alaka düzeyi ölçümleri bu çalışmada tamamlanmamıştır."
    )

    texts["sec_4_3_sql_fix"] = (
        f"SQL kanalı için {sq['n']} referans sorgu PostgreSQL üzerinde çalıştırılmış; {sq['executed_ok']} sorgu "
        f"beklenen değeri üretmiş, {sq['failed']} sorgu (F-SQL019, 'Çiftliğin adını söyle') referans sorgunun "
        "ciftlikler tablosunda bulunmayan 'ad' sütununa başvurması nedeniyle UndefinedColumn hatası vermiştir. "
        "Ek Tablo 1'de 24 kaydın tamamı benzersiz kimlik, çalıştırılan sorgu, beklenen değer, gözlenen değer, çalışma "
        "durumu, karşılaştırma sonucu ve hata türü sütunlarıyla sunulmuştur. Bu oran referans sorguların "
        "çalıştırılabilirliğini gösterir; modelin ürettiği SQL'in execution accuracy'si değildir ve bu çalışmada "
        "ölçülmemiştir."
    )

    texts["sec_4_5_paired"] = (
        f"BGE-M3 ile hibrit RRF arasındaki fark küçüktür ve örneklem (n = {rt['n']}) içinde istatistiksel üstünlük "
        f"kanıtı sayılmamalıdır. Soru bazında eşleştirilmiş farklar (FAISS − hibrit) için ortalama P@5 farkı "
        f"{fmt(pd['p_at_k']['mean_diff'], 3)} (bootstrap %95 GA {fmt(pd['p_at_k']['ci95_low'], 3)} … "
        f"{fmt(pd['p_at_k']['ci95_high'], 3)}), MRR farkı {fmt(pd['mrr']['mean_diff'], 3)} "
        f"(%95 GA {fmt(pd['mrr']['ci95_low'], 3)} … {fmt(pd['mrr']['ci95_high'], 3)}) ve nDCG@5 farkı "
        f"{fmt(pd['ndcg_at_k']['mean_diff'], 3)} (%95 GA {fmt(pd['ndcg_at_k']['ci95_low'], 3)} … "
        f"{fmt(pd['ndcg_at_k']['ci95_high'], 3)}) bulunmuştur; aralıkların alt sınırı sıfırdır ve farklar birkaç "
        f"soruda yoğunlaşmaktadır. P@5'te FAISS {pd['p_at_k']['faiss_better']} soruda, hibrit "
        f"{pd['p_at_k']['hybrid_better']} soruda daha iyi, {pd['p_at_k']['ties']} soruda eşittir; MRR'de FAISS "
        f"{pd['mrr']['faiss_better']} soruda daha iyi, {pd['mrr']['ties']} soruda eşittir. İki yöntem "
        f"{rt['identical_top5_faiss_hybrid']} soruda birebir aynı ilk beş listesini üretmiştir; kalan sorularda liste "
        "sırası değişmiş ancak belge düzeyinde ilgililik çoğunlukla aynı kalmıştır. Bu kadar az uyumsuz çift ile "
        "işaret testi anlamlı sonuç veremez; bulgu, 'hibrit bu sette ölçülebilir kazanç sağlamadı' biçiminde ifade "
        "edilmelidir. Buna karşılık hibritin BM25'e göre P@5 kazancı "
        f"{fmt(rt['paired_hybrid_minus_bm25_p_at_k']['mean_diff'], 3)} "
        f"(%95 GA {fmt(rt['paired_hybrid_minus_bm25_p_at_k']['ci95_low'], 3)} … "
        f"{fmt(rt['paired_hybrid_minus_bm25_p_at_k']['ci95_high'], 3)}) ile belirgindir. Pilot ağırlık taramasında "
        "60/40 ve 70/30 bütün ölçütlerde eşit (P@5 0,81; R@5 0,59; MRR 0,84; nDCG@5 0,84) ve 50/50'den çok az yüksek "
        "çıktığından, 60/40 'tek ve açık en iyi' değil, deney öncesi belirlenen eşitlik-bozma kuralına "
        "(eşitlikte yoğun ağırlığı 0,50'ye en yakın yapılandırma) göre seçilmiş yapılandırmadır."
    )

    texts["sec_4_6_generation"] = (
        f"Held-out RAG kümesindeki {gn['n']} soruda üretilen yanıtlar, getirilen kaynak listesine karşı otomatik "
        f"ölçütlerle değerlendirilmiştir. Ortalama atıf doğruluğu {fmt(gs['mean_citation_correctness'])}, atıf tamlığı "
        f"{fmt(gs['mean_citation_completeness'])}, desteksiz iddia oranı {fmt(gs['mean_unsupported_claim_rate'])} ve "
        f"tercih edilen kaynağa isabet {fmt(gs['mean_preferred_source_hit_rate'])} bulunmuştur. Hata tipolojisi: "
        f"{cats.get('atıf yok', 0)} yanıtta hiç kaynak kimliği yoktur, {cats.get('kısmi atıf', 0)} yanıtta kısmi atıf, "
        f"{cats.get('tam atıf', 0)} yanıtta tüm cümleler atıflıdır; {cats.get('kesik yanıt (token sınırı)', 0)} yanıt "
        f"160 token sınırı nedeniyle cümle ortasında kesilmiştir; {cats.get('İngilizce sözcük kalıntısı (sezgisel)', 0)} "
        "yanıtta İngilizce sözcük kalıntısı vardır (sezgisel sayım); tanı/antibiyotik talebi içeren tek maddede (F-RAG033) "
        "sistem beklendiği gibi yanıtı reddedip veteriner hekime yönlendirmiştir. Burada 'desteksiz iddia' ölçütü, "
        "cümlenin kaynak kimliği taşımamasını esas alan otomatik bir vekildir; cümle içeriğinin kaynakla gerçekten "
        "çeliştiğini göstermez. Uzman puanlı faithfulness ve gold cevap karşılaştırması yapılmadığından RQ5 yalnızca "
        "vekil ölçütlerle yanıtlanmıştır."
    )

    texts["sec_latency"] = (
        "Geliştirme aşamasındaki ortalama yanıt süreleri tablosunda verilen değerler (RAG 55,49 s; HYBRID 39,18 s; "
        "SQL 6,91 s) pilot koşullardan gelen ön ölçümlerdir ve nihai yapılandırmayı temsil etmez. Dondurulmuş "
        f"final yapılandırmada RAG kanalı için uçtan uca yanıt süresi {gn['n']} soruda ölçülmüştür: LLM çağrısı içeren "
        f"{lat['n']} soruda ortalama {fmt(lat['mean'])} s, medyan {fmt(lat['median'])} s, standart sapma "
        f"{fmt(lat['sd'])} s, en düşük {fmt(lat['min'])} s, en yüksek {fmt(lat['max'])} s, p90 {fmt(lat['p90'])} s, "
        f"p95 {fmt(lat['p95'])} s (tanı reddi maddesi LLM çağrılmadan {fmt(lat_all['min'], 3)} s'de yanıtlanmıştır). "
        "Ölçüm Windows 11 üzerinde, Intel 11. nesil mobil işlemci ile, GPU kullanılmadan (num_gpu = 0) ve Ollama "
        "modeli bellekte sıcakken (keep_alive = 5 dk) tek tekrarla alınmıştır; her soru için retrieval ve LLM süreleri "
        "ayrı kaydedilmemiştir. SQL ve HYBRID kanalları için final gecikme dağılımı ölçülmemiştir. Yaklaşık 40 saniyelik "
        "medyan, gerçek zamanlı sohbet beklentisinin üzerindedir; darboğaz CPU üzerinde 7B parametreli üretim modelidir "
        "ve GPU çıkarımı, daha kısa bağlam veya daha küçük nicemlenmiş model ile azaltılması beklenir."
    )

    texts["sec_test_set"] = (
        f"Held-out kümesi (n = {ov['heldout_n']}) pilot kümeden ({ov['pilot_n']} soru) bağımsız olarak, pilot deneyler "
        "tamamlandıktan sonra tez yazarı tarafından yazılmış, sınıf etiketleri soru yazımı sırasında atanmış ve küme "
        "sistem çalıştırılmadan önce dosya olarak dondurulmuştur (evaluation_sets/final_heldout_set.json). İki küme "
        f"arasında birebir aynı soru yoktur ({ov['exact_duplicates']} tekrar). Bununla birlikte küme tam anlamıyla "
        "bağımsız değil, 'şablon-yakın' bir kümedir: held-out sorularının pilot kümedeki en yakın soruya göre sözcük "
        f"kümesi Jaccard benzerliği ortalama {fmt(ov['max_jaccard_mean'])}, medyan {fmt(ov['max_jaccard_median'])}, "
        f"en yüksek {fmt(ov['max_jaccard_max'])} olup {len(high_pairs)} soru 0,50 ve üzeri benzerlik taşımaktadır "
        f"(SQL {high_by_class.get('SQL', 0)}, RAG {high_by_class.get('RAG', 0)}, HYBRID {high_by_class.get('HYB', 0)}; "
        "Ek Tablo 2 notu). Yüksek benzerlik çoğunlukla SQL kanalında aynı soru kalıbının farklı inek adı veya tarihle "
        "yeniden örneklenmesinden kaynaklanır. Bu nedenle 89/89 sonucu, kural setinin bu soru diline iyi örtüştüğünün "
        "göstergesidir; saha genellemesi veya pilot %97'ye göre nedensel bir iyileşme olarak okunmamalıdır. Sistem "
        "yapılandırması (kurallar, prompt, model, ağırlıklar, Top-K) held-out sonuçları görüldükten sonra "
        "değiştirilmemiştir. Yazım hatalı, çift anlamlı ve farklı ifadelendirilmiş sorularla ayrı bir stres testi "
        "yapılmamıştır."
    )

    texts["sec_5_claim_fix"] = (
        "Yalnızca LLM (erişimsiz) yanıt üretimi ile RAG yanıtları arasında nicel bir karşılaştırma bu çalışmada "
        "yapılmamıştır. Buna karşılık bilgi erişimi düzeyinde BM25, BGE-M3 + FAISS ve hibrit RRF için kesin sayılar "
        "held-out kümede elde edilmiş ve Tablo 4.5'te raporlanmıştır."
    )

    texts["discussion"] = [
        ("5. TARTIŞMA", "h1"),
        ("5.1. Araştırma Sorularının Yanıtlanma Düzeyi", "h2"),
        ("Bu çalışmada beş araştırma sorusu tanımlanmıştır; ancak hepsi aynı kanıt düzeyinde yanıtlanmamıştır. "
         "Tablo 5.1, her soru için ölçülen ve ölçülmeyen bileşenleri ayırmaktadır. RQ1 ve RQ2 held-out kümede nicel "
         "olarak yanıtlanmış, RQ3 pilot sette keşifsel düzeyde incelenmiş, RQ4 yalnızca referans sorgu düzeyinde "
         "ele alınmış, RQ5 ise otomatik vekil ölçütlerle sınırlı kalmıştır. Dolayısıyla sistemin 'doğru ve güvenilir "
         "bilimsel karar destek asistanı' olduğu iddiası bu tezin bulgularıyla desteklenmemekte; desteklenen iddia, "
         "sorguların doğru kanala yönlendirildiği ve ilgili belgelerin yüksek isabetle getirildiğidir.", "p"),
        ("TABLE:rq", "table"),
        ("5.2. Hibrit Erişim Neden Anlamsal Erişimi Geçmedi?", "h2"),
        ("Literatürde hibrit erişimin sözcüksel ve anlamsal sinyalleri birleştirerek tek başına yöntemlerden daha "
         "sağlam sonuç verdiği sıkça raporlanır. Bu çalışmada ise BGE-M3 tek başına P@5 = "
         f"{fmt(s['faiss']['p_at_k'])} üretirken hibrit RRF {fmt(s['hybrid']['p_at_k'])} ile çok az gerisinde kalmıştır. "
         "Üç açıklama öne çıkmaktadır. Birincisi, sorular Türkçe yazılmışken derlemenin büyük kısmı İngilizcedir; "
         "BM25 diller arası sözcük eşleşmesi yapamadığı için düşük kalmakta (P@5 = "
         f"{fmt(s['bm25']['p_at_k'])}) ve RRF içinde zayıf sıralamalar katkı yerine gürültü taşımaktadır. İkincisi, "
         "çok dilli BGE-M3 modeli bu dil uyumsuzluğunu zaten çözdüğünden hibritin ekleyeceği tamamlayıcı sinyal "
         "sınırlıdır. Üçüncüsü, gold etiket belge düzeyinde olduğundan ve çoğu soruya iki belge atandığından tavan "
         "etkisi vardır; FAISS birçok soruda zaten mükemmel skora ulaşmıştır. Eşleştirilmiş farkların bootstrap "
         "%95 güven aralıkları sıfırı kapsamaktadır; dolayısıyla bulgu 'FAISS hibritten üstündür' değil, 'bu derleme "
         "ve soru setinde hibrit birleştirme ölçülebilir bir kazanç sağlamamıştır' biçiminde ifade edilmelidir. "
         "Hibritin pratik değeri, Türkçe terim içeren belgelerde ve nadir özel adlarda sözcüksel kaçırmaya karşı bir "
         "güvenlik ağı olmasıdır; bu etkinin görülmesi için Türkçe ağırlıklı ya da terim-yoğun bir derleme gerekir.", "p"),
        ("5.3. Yönlendirmede %100 Sonucunun Anlamı ve Sınırı", "h2"),
        ("Held-out kümede 89/89 doğru yönlendirme, birinci aşama kural tabanlı sınıflandırıcının tüm soruları "
         "LLM'e başvurmadan çözdüğünü göstermektedir. Bu, tekrarlanabilirlik açısından olumludur; fakat kural seti "
         "prototipteki beş ineğin özel adlarını (Serap, Beyza, Boncuk, Papatya, Lale) ve küpe numaralarını "
         "içermektedir. Farklı bir işletmede hayvan adları değişeceğinden kuralların doğrudan taşınması mümkün "
         "değildir; adların veritabanından dinamik olarak yüklenmesi gerekir. Ayrıca held-out sorular pilot sorularla "
         "aynı tema ve sözcük dağarcığını paylaştığından (Bölüm 4.2), sonuç zor örnekler, yazım hataları ve çift "
         "anlamlı istekler içeren bir stres testine genellenemez. %95 Wilson aralığının alt sınırı 0,96 olsa da bu "
         "aralık yalnızca örneklem hatasını yansıtır; soru dağılımı kaymasını yansıtmaz. Pilot %97 ile final %100 "
         "farklı soru kümelerinden geldiği için aralarındaki fark nedensel bir iyileşme olarak yorumlanmamalıdır.", "p"),
        ("5.4. Doğru Belgeyi Getirmek ile Doğru Cümleyi Üretmek Arasındaki Boşluk", "h2"),
        (f"Retrieval ölçütleri yüksekken üretim düzeyinde atıf doğruluğu {fmt(gs['mean_citation_correctness'])} ve "
         f"desteksiz iddia oranı {fmt(gs['mean_unsupported_claim_rate'])} bulunmuştur. Bu açı, RAG literatüründe "
         "'retrieval başarısı yanıt doğruluğunu garanti etmez' uyarısının bu sistemde de geçerli olduğunu gösterir. "
         "Hata tipolojisi iki baskın örüntüye işaret etmektedir: modelin kaynak kimliklerini hiç yazmaması ve 160 "
         "token sınırı nedeniyle yanıtların kesilmesi. İlki, prompt'taki atıf talimatına rağmen 7B parametreli modelin "
         "biçim talimatına uyum zayıflığıyla; ikincisi ise gecikmeyi sınırlamak için seçilen kısa üretim penceresiyle "
         "ilgilidir. Kullanılan 'desteksiz iddia' ölçütü atıfsız cümle oranını saymaktadır; cümlenin içerik olarak "
         "kaynağa aykırı olup olmadığını ölçmez. Bu nedenle gerçek halüsinasyon oranı daha düşük ya da daha yüksek "
         "olabilir; iki bağımsız değerlendiricili 0–2 puanlama ve gold cevap seti olmadan bu belirsizlik giderilemez. "
         "Ölçülen bu zayıflık, sistemin kaynak göstermekle yükümlü bir karar destek aracı olarak konumlanmasını ve "
         "veteriner tanısının yerine geçmemesini zorunlu kılar.", "p"),
        ("5.5. Yanıt Süresi ve Kullanılabilirlik", "h2"),
        (f"Final RAG yapılandırmasında medyan {fmt(lat['median'])} s ve p95 {fmt(lat['p95'])} s gecikme, sohbet "
         "arayüzü beklentilerinin çok üzerindedir. Ölçüm CPU üzerinde ve GPU'suz yapılmıştır; darboğaz üretim "
         "modelidir, çünkü SQL kanalı aynı altyapıda belirgin biçimde kısadır. Saha kullanımında GPU çıkarımı, daha "
         "küçük nicemlenmiş model, bağlam penceresinin ilk 3 parçayla sınırlanması veya yanıtın akışlı (streaming) "
         "gösterimi gecikmeyi azaltabilir. SQL ve HYBRID kanallarının final gecikme dağılımı ölçülmediğinden bu "
         "kanallar için yalnızca pilot ortalamaları mevcuttur.", "p"),
        ("5.6. Sentetik Veri, Genellenebilirlik ve Sorumlu Kullanım Sınırı", "h2"),
        ("Çiftlik kayıtları ticari bir işletmeden alınmamış, beş inek ve kısa bir sağım dönemi için üretilmiş sentetik "
         "verilerdir. Bu, SQL ve HYBRID kanallarının veri çeşitliliği, eksik kayıt, tutarsız girdi ve ölçek açısından "
         "sınanmadığı anlamına gelir; sonuçlar gerçek sürülere genellenemez. Çok çiftlikli, gerçek kayıtlarla dış "
         "doğrulama bu tezin kapsamı dışında kalmış ve gelecek çalışma olarak önerilmiştir. Güvenlik tarafında tanı/"
         "antibiyotik taleplerinin reddi ve yalnızca okuma SQL muhafızı uygulanmış; ancak prompt-injection, yetkisiz "
         "SQL yazma girişimi ve işletmeler arası veri izolasyonu sistematik olarak test edilmemiştir. Bu özellikler "
         "'tasarlandı' düzeyinde kalmakta, 'kanıtlandı' olarak sunulmamaktadır.", "p"),
        ("5.7. Literatürdeki Boşluk ve Bu Çalışmanın Konumu", "h2"),
        ("Süt sığırcılığı alanındaki yapay zekâ çalışmaları ağırlıklı olarak sensör verisinden hastalık öngörüsü veya "
         "verim tahmini üzerine yoğunlaşmakta; RAG ve Text-to-SQL çalışmaları ise genel alan ya da tarım dışı "
         "kurumsal veri üzerinde raporlanmaktadır. Yapılandırılmış sürü kayıtları ile hakemli/kurumsal bilimsel "
         "belgeleri aynı sohbet asistanında, kaynak göstererek ve Türkçe birleştiren uçtan uca bir prototip ile bunun "
         "held-out değerlendirmesi bu çalışmanın katkısıdır. Bulgular, bu entegrasyonun mühendislik olarak mümkün "
         "olduğunu; ancak bilimsel güvenilirlik iddiasının üretim düzeyi ölçümleri tamamlanmadan ileri sürülemeyeceğini "
         "göstermektedir.", "p"),
    ]

    texts["limitations_additions"] = (
        "Ek sınırlılıklar: (1) Gold relevance etiketleri tek değerlendirici tarafından belge düzeyinde atanmıştır; "
        "değerlendiriciler arası uyum raporlanamamıştır. (2) Üretim kalitesi ölçütleri otomatik vekillerdir; uzman "
        "puanlı faithfulness, gold cevap karşılaştırması ve Cohen's κ yapılmamıştır. (3) Modelin ürettiği SQL'in "
        "execution accuracy'si ve HYBRID uçtan uca doğruluk ölçülmemiştir; Ek Tablo 1 yalnızca referans sorguların "
        "çalıştırılabilirliğini gösterir. (4) Final gecikme dağılımı yalnızca RAG kanalı için, tek tekrarla ve GPU'suz "
        "ölçülmüştür. (5) Ollama model digest'leri kaydedilmemiştir. (6) Parçalama ve Top-K değerleri için ablasyon "
        "yapılmamış; 900/150 ve K = 5 değerleri 2048 token bağlam penceresine beş parçanın sığması ve CPU gecikme "
        "kısıtıyla gerekçelendirilmiştir. (7) Prompt-injection ve işletmeler arası veri izolasyonu test edilmemiştir."
    )

    return texts


# ----------------------------------------------------------------------------
# HTML
# ----------------------------------------------------------------------------
def h(x) -> str:
    return html.escape(str(x), quote=False)


def html_table(headers: list[str], rows: list[list], caption: str = "") -> str:
    out = ["<table>"]
    out.append("<tr>" + "".join(f"<th>{h(c)}</th>" for c in headers) + "</tr>")
    for r in rows:
        out.append("<tr>" + "".join(f"<td>{h(c)}</td>" for c in r) + "</tr>")
    out.append("</table>")
    if caption:
        out.append(f'<p class="cap">{h(caption)}</p>')
    return "\n".join(out)


def write_html(data: dict, texts: dict, out: Path) -> None:
    rt, gn, sq, cp, rg, ov = data["retrieval"], data["generation"], data["sql"], data["corpus"], data["routing"], data["overlap"]
    parts = []
    parts.append("""<!DOCTYPE html><html lang="tr"><head><meta charset="utf-8">
<title>Tez revizyon paketi – 10 Ekim 2026 raporu</title>
<style>
body{font-family:Segoe UI,Arial,sans-serif;max-width:1000px;margin:32px auto;padding:0 16px;line-height:1.5;color:#222}
h1{font-size:22px}h2{font-size:18px;margin-top:34px;border-bottom:1px solid #ccc}h3{font-size:15px;margin-top:22px}
.box{background:#f7f7f7;border:1px solid #ccc;padding:12px 14px;margin:10px 0;white-space:pre-wrap}
table{border-collapse:collapse;width:100%;margin:10px 0;font-size:13px}th,td{border:1px solid #bbb;padding:5px 7px;text-align:left;vertical-align:top}
th{background:#e8f5e9}.cap{font-size:12px;color:#555}.warn{background:#fff3e0;border-left:4px solid #ef6c00;padding:8px 12px}
</style></head><body>""")
    parts.append("<h1>Tez revizyon paketi (10 Ekim 2026 yeniden değerlendirme raporuna göre)</h1>")
    parts.append('<p class="warn">Kutular doğrudan Word\'e yapıştırılabilir. Aynı içerik <code>revise_thesis.py</code> ile otomatik olarak da uygulanır. '
                 'Ölçülmeyen bileşenler (SQL execution accuracy, HYBRID E2E, uzman puanı) burada <b>ölçülmedi</b> olarak yazılmıştır; '
                 'bunlar için <code>run_academic_evaluation --task e2e</code> çalıştırılmalıdır.</p>')

    parts.append("<h2>1. Başlık önerisi</h2>")
    parts.append(f'<div class="box">{h(texts["title_suggestion"])}</div>')

    parts.append("<h2>2. Bölüm 3.7 – Değerlendirme protokolü (ekle)</h2>")
    parts.append(f'<div class="box">{h(texts["sec_3_7_protocol"])}</div>')

    parts.append("<h2>3. Bölüm 4.2/4.3 – Test seti bağımsızlığı (ekle)</h2>")
    parts.append(f'<div class="box">{h(texts["sec_test_set"])}</div>')
    parts.append(html_table(
        ["Held-out ID", "Held-out soru", "Pilot ID", "Pilot soru", "Jaccard"],
        [[p["heldout_id"], p["heldout"], p["pilot_id"], p["pilot"], fmt(p["jaccard"], 2)] for p in ov["high_similarity_pairs"]],
        f"Jaccard ≥ 0,50 çiftler (n = {len(ov['high_similarity_pairs'])}); birebir tekrar {ov['exact_duplicates']}.",
    ))

    parts.append("<h2>4. Bölüm 4.3 – SQL paragrafı (değiştir)</h2>")
    parts.append(f'<div class="box">{h(texts["sec_4_3_sql_fix"])}</div>')

    parts.append("<h2>5. Bölüm 4.4 – Çelişen cümle (değiştir)</h2>")
    parts.append(f'<div class="box">{h(texts["sec_4_4_fix"])}</div>')

    parts.append("<h2>6. Bölüm 4.5 – Eşleştirilmiş retrieval farkları ve ağırlık seçimi (ekle)</h2>")
    parts.append(f'<div class="box">{h(texts["sec_4_5_paired"])}</div>')
    pdd = rt["paired_faiss_minus_hybrid"]
    parts.append(html_table(
        ["Ölçüt", "FAISS", "Hibrit", "Ortalama fark (FAISS − hibrit)", "Bootstrap %95 GA", "FAISS daha iyi / eşit / hibrit daha iyi"],
        [[k_tr, fmt(rt["summary"]["faiss"][k]), fmt(rt["summary"]["hybrid"][k]), fmt(pdd[k]["mean_diff"], 3),
          f"{fmt(pdd[k]['ci95_low'], 3)} … {fmt(pdd[k]['ci95_high'], 3)}",
          f"{pdd[k]['faiss_better']} / {pdd[k]['ties']} / {pdd[k]['hybrid_better']}"]
         for k, k_tr in (("p_at_k", "P@5"), ("r_at_k", "R@5"), ("mrr", "MRR"), ("ndcg_at_k", "nDCG@5"))],
        f"Tablo 4.7 (öneri). Soru bazında eşleştirilmiş farklar, n = {rt['n']}, 10.000 bootstrap örneği. İki yöntem {rt['identical_top5_faiss_hybrid']} soruda aynı ilk 5 listesini üretmiştir.",
    ))

    parts.append("<h2>7. Bölüm 4.6 – Üretim kalitesi (değiştir/ekle)</h2>")
    parts.append(f'<div class="box">{h(texts["sec_4_6_generation"])}</div>')
    gs = gn["summary"]
    parts.append(html_table(
        ["Ölçüt (otomatik)", "Değer"],
        [["Atıf doğruluğu (geçerli K-id / yazılan K-id)", fmt(gs["mean_citation_correctness"])],
         ["Atıf tamlığı (atıflı cümle / cümle)", fmt(gs["mean_citation_completeness"])],
         ["Desteksiz iddia oranı (1 − atıf tamlığı)", fmt(gs["mean_unsupported_claim_rate"])],
         ["Tercih edilen kaynağa isabet", fmt(gs["mean_preferred_source_hit_rate"])],
         ["Tanı reddi (beklenen 1 madde)", f"{gs['diagnosis_refusal_ok']}/{gn['n']} maddede kural ihlali yok"]],
        f"Tablo 4.8 (öneri). Held-out RAG, n = {gn['n']}. Uzman puanı yoktur.",
    ))
    parts.append(html_table(["Hata türü", "Sayı"], [[k, v] for k, v in gn["error_categories"].items()],
                            "Tablo 4.9 (öneri). RAG üretim hata tipolojisi (otomatik sınıflama)."))

    parts.append("<h2>8. Bölüm 4.4/4.7 – Yanıt süresi (değiştir)</h2>")
    parts.append(f'<div class="box">{h(texts["sec_latency"])}</div>')
    la, ll = gn["latency_all"], gn["latency_llm_only"]
    parts.append(html_table(
        ["Küme", "n", "Ortalama", "Medyan", "SS", "Min", "Maks", "p90", "p95"],
        [["RAG final – tüm maddeler", la["n"], fmt(la["mean"]), fmt(la["median"]), fmt(la["sd"]), fmt(la["min"], 3), fmt(la["max"]), fmt(la["p90"]), fmt(la["p95"])],
         ["RAG final – LLM çağrısı içeren", ll["n"], fmt(ll["mean"]), fmt(ll["median"]), fmt(ll["sd"]), fmt(ll["min"]), fmt(ll["max"]), fmt(ll["p90"]), fmt(ll["p95"])]],
        "Tablo 4.10 (öneri). Saniye; Windows 11, Intel 11. nesil CPU, GPU yok, tek tekrar. SQL/HYBRID final gecikmesi ölçülmedi.",
    ))

    parts.append("<h2>9. Bölüm 5 (Sonuç) – LLM/FAISS/hibrit cümlesi (değiştir)</h2>")
    parts.append(f'<div class="box">{h(texts["sec_5_claim_fix"])}</div>')

    parts.append("<h2>10. Yeni Bölüm 5 – TARTIŞMA (Sonuç bölümünün önüne ekle; Sonuç 6 olur)</h2>")
    for text, kind in texts["discussion"]:
        if kind == "table":
            parts.append(html_table(["Araştırma sorusu", "Yanıtlanma düzeyi", "Dayanak / kalan iş"], [list(r) for r in texts["rq_table"]],
                                    "Tablo 5.1. Araştırma sorularının ölçülen ve ölçülmeyen bileşenleri."))
        elif kind == "h1":
            parts.append(f"<h3><b>{h(text)}</b></h3>")
        elif kind == "h2":
            parts.append(f"<h3>{h(text)}</h3>")
        else:
            parts.append(f'<div class="box">{h(text)}</div>')

    parts.append("<h2>11. Sınırlılıklara eklenecek paragraf</h2>")
    parts.append(f'<div class="box">{h(texts["limitations_additions"])}</div>')

    parts.append("<h2>12. Ek Tablo 1 – SQL referans sorguları (24 satır, F-SQL019 dâhil)</h2>")
    parts.append(html_table(
        ["ID", "Soru", "Çalıştırılan sorgu", "Beklenen", "Gözlenen", "Durum", "Karşılaştırma", "Hata türü"],
        [[r["id"], r["question"], r["executed_query"], r["expected_value"], r["observed_value"], r["run_status"], r["comparison_result"], r["error_type"]] for r in sq["rows"]],
        f"Ek Tablo 1. n = {sq['n']}; {sq['executed_ok']} çalıştı, {sq['failed']} hata ({', '.join(sq['failed_ids'])}). Bu tablo modelin Text-to-SQL execution accuracy'si değildir.",
    ))

    parts.append("<h2>13. Ek Tablo 2 – Held-out yönlendirme kaydı (89 satır)</h2>")
    parts.append(html_table(
        ["ID", "Soru", "Gold", "Tahmin", "Mekanizma", "Doğru"],
        [[r["query_id"], r["query_text"], r["gold_label"], r["predicted_label"], r["mechanism"], "evet" if r["correct"] else "hayır"] for r in rg["rows"]],
        f"Ek Tablo 2. Çalıştırma {rg['rows'][0]['run_timestamp_utc']}; yapılandırma özeti {rg['rows'][0]['configuration_hash']}; mekanizma dağılımı {rg['mechanism_counts']}.",
    ))

    parts.append("<h2>14. Ek Tablo 3 – Sorgu bazlı retrieval (33 satır)</h2>")
    parts.append(html_table(
        ["ID", "Soru", "İlgili belge sayısı", "BM25 P@5", "BM25 RR", "BM25 nDCG", "FAISS P@5", "FAISS RR", "FAISS nDCG", "Hibrit P@5", "Hibrit RR", "Hibrit nDCG"],
        [[r["query_id"], r["query_text"], r["n_relevant_docs"], fmt(r["bm25_p_at_k"]), fmt(r["bm25_mrr"]), fmt(r["bm25_ndcg_at_k"]),
          fmt(r["faiss_p_at_k"]), fmt(r["faiss_mrr"]), fmt(r["faiss_ndcg_at_k"]), fmt(r["hybrid_p_at_k"]), fmt(r["hybrid_mrr"]), fmt(r["hybrid_ndcg_at_k"])] for r in rt["rows"]],
        "Ek Tablo 3. K = 5; gold etiket belge düzeyinde (preferred_sources).",
    ))

    parts.append("<h2>15. Ek Tablo 4 – RAG üretim deneyi sorgu bazlı (33 satır)</h2>")
    parts.append(html_table(
        ["ID", "Soru", "Atıf doğ.", "Atıf taml.", "Desteksiz", "Terc. kaynak", "Yazılan K-id", "Cümle", "Kategori", "Süre (s)"],
        [[r["query_id"], r["query_text"], fmt(r["citation_correctness"]), fmt(r["citation_completeness"]), fmt(r["unsupported_claim_rate"]),
          fmt(r["preferred_source_hit_rate"]), r["cited_ids"] or "—", r["sentence_count"], r["category"] + (" + kesik" if r["truncated"] else ""), fmt(r["latency_sec"], 1)] for r in gn["rows"]],
        "Ek Tablo 4. Otomatik ölçütler; uzman puanı yoktur.",
    ))

    parts.append("<h2>16. Tablo 3.2 – Corpus manifestosu (tam künye, sayfa ve parça sayısı)</h2>")
    parts.append(html_table(
        ["ID", "Künye", "Yıl", "Tür", "Tema", "Sayfa", "Parça"],
        [[r["id"], r["citation"] + (f" [Teyit: {r['verify']}]" if r["verify"] else ""), r["year"], r["doc_type"], r["theme"], r["pages"], r["chunks"]] for r in cp["rows"]],
        f"Tablo 3.2. {cp['document_count']} belge; toplam {cp['total_pages']} sayfa birimi ve {cp['total_chunks']} parça (indeks manifestosu: {cp['index_manifest_pages']} / {cp['index_manifest_chunks']}). "
        "Sayfa ve parça sayıları aynı parçalama ayarlarıyla (900/150) yeniden hesaplanmıştır. Seçim ölçütleri: " + "; ".join(cp["selection_criteria"]) + ". Dışlanan belge: Cornell_Feeding_Dairy_Calf.pdf (buzağı temasında içerik örtüşmesi; knowledge_base_disabled/).",
    ))

    parts.append("<h2>17. Tablo 3.4 – Yapılandırma ve sürümler (genişletilmiş)</h2>")
    parts.append(html_table(["Bileşen", "Değer"], [[r["component"], r["value"]] for r in data["config"]], "Tablo 3.4. Tekrarlanabilirlik için tam yapılandırma."))

    parts.append("<h2>18. Ek – Prompt şablonları</h2>")
    for key, label in (("router_system", "Yönlendirici sistem istemi"), ("rag_system", "RAG sistem istemi"), ("rag_human", "RAG kullanıcı istemi"), ("veterinary_disclaimer", "Veteriner uyarı metni")):
        if key in data["prompts"]:
            parts.append(f"<h3>{h(label)}</h3><div class='box'>{h(data['prompts'][key])}</div>")

    parts.append("<h2>19. Ctrl+H ile düzeltilecek ifadeler</h2>")
    parts.append(html_table(["Bul", "Değiştir"], [
        ["Geri Alma Destekli Üretim / Geri Getirim Destekli Üretim / Geri Alma", "Geri Getirme Destekli Üretim (ilk geçişte) → sonrasında RAG"],
        ["AGR", "RAG"],
        ["ticari veriler / şirkete özgü veriler", "sentetik çiftlik kayıtları"],
        ["Belirli alanlar veya sektörler hakkında daha detaylı bir analiz isterseniz lütfen bize bildirin.", "(sil)"],
        ["Bu yaklaşımlar, ... daha güvenilir karar destek sistemleri oluşturur.", "Bu yaklaşımlar, yapılandırılmış çiftlik verileri ile kaynak gösterilebilir bilimsel bilginin birlikte kullanımı yoluyla daha güvenilir karar destek sistemlerinin oluşturulmasına katkı sağlar."],
        ["değerlendirildi Bu çalışmada", "değerlendirildi. Bu çalışmada"],
        ["Şekil3.2.Kullanıcı", "Şekil 3.2. Kullanıcı"],
        ["Hayvancılık Sektöründe ... (başlık)", NEW_TITLE],
    ]))
    parts.append("</body></html>")
    out.write_text("\n".join(parts), encoding="utf-8")


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()), delimiter=";")
        writer.writeheader()
        writer.writerows(rows)


# ----------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out-dir", default=str(OUT_DIR_DEFAULT))
    parser.add_argument("--skip-pdf", action="store_true", help="PDF sayfa/parça sayımını atla (corpus_manifest değerleri kullanılır)")
    args = parser.parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    routing = load_json(EVAL_OUT / "routing_report.json")
    retrieval = load_json(EVAL_OUT / "retrieval_report.json")
    generation = load_json(EVAL_OUT / "generation_report.json")
    sql = load_json(EVAL_OUT / "sql_gold_results.json")
    fusion = load_json(EVAL_OUT / "fusion_ablation_pilot.json")
    repro = load_json(EVAL_OUT / "reproducibility.json")
    heldout = load_json(EVAL_SETS / "final_heldout_set.json")
    pilot = load_json(BACKEND_DIR / "tez_test_seti_100.json")
    manifest = load_json(KB_DIR / "corpus_manifest.json")

    config_rows, config_hash = build_config(repro)
    data = {
        "generated_for": "10 Ekim 2026 yeniden değerlendirme raporu",
        "config_hash": config_hash,
        "routing": build_routing(routing, repro, config_hash),
        "overlap": build_overlap(heldout, pilot),
        "retrieval": build_retrieval(retrieval),
        "generation": build_generation(generation),
        "sql": build_sql(sql),
        "fusion": fusion,
        "config": config_rows,
        "prompts": extract_prompts(),
    }
    if args.skip_pdf:
        data["corpus"] = {
            "document_count": manifest["document_count"],
            "total_pages": manifest.get("page_document_count_in_index"),
            "total_chunks": manifest.get("chunk_count"),
            "index_manifest_pages": manifest.get("page_document_count_in_index"),
            "index_manifest_chunks": manifest.get("chunk_count"),
            "selection_criteria": manifest.get("selection_criteria", []),
            "rows": [{
                "id": d["id"], "file": d["file"],
                "citation": CORPUS_BIBLIO.get(d["file"], {}).get("citation", d["file"]),
                "year": CORPUS_BIBLIO.get(d["file"], {}).get("year", d.get("year") or "—"),
                "institution": CORPUS_BIBLIO.get(d["file"], {}).get("institution", d.get("publisher", "")),
                "doc_type": CORPUS_BIBLIO.get(d["file"], {}).get("doc_type", d.get("type", "")),
                "theme": THEME_TR.get(d["category"], d.get("theme", "")),
                "pages": None, "chunks": None,
                "verify": CORPUS_BIBLIO.get(d["file"], {}).get("verify", ""),
            } for d in manifest["documents"]],
        }
    else:
        data["corpus"] = build_corpus(manifest)
    data["texts"] = build_texts(data)

    (out_dir / "revision_data.json").write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    write_html(data, data["texts"], out_dir / "tez_revizyon_paketi.html")
    write_csv(out_dir / "ek_tablo_2_yonlendirme_logu.csv", data["routing"]["rows"])
    write_csv(out_dir / "ek_tablo_3_retrieval_sorgu_bazli.csv", data["retrieval"]["rows"])
    write_csv(out_dir / "ek_tablo_4_uretim_sorgu_bazli.csv", data["generation"]["rows"])
    write_csv(out_dir / "ek_tablo_1_sql_referans.csv", data["sql"]["rows"])
    write_csv(out_dir / "tablo_3_2_corpus_manifestosu.csv", data["corpus"]["rows"])
    write_csv(out_dir / "tablo_3_4_yapilandirma.csv", data["config"])

    print(f"yazıldı: {out_dir}")
    print(f"  yönlendirme n={data['routing']['n']} acc={data['routing']['accuracy']} mekanizma={data['routing']['mechanism_counts']}")
    print(f"  örtüşme: tekrar={data['overlap']['exact_duplicates']} jaccard_ort={data['overlap']['max_jaccard_mean']:.3f} ≥0,50: {data['overlap']['buckets'].get('≥0,50', 0)}")
    p = data["retrieval"]["paired_faiss_minus_hybrid"]["p_at_k"]
    print(f"  retrieval FAISS−hibrit P@5 fark={p['mean_diff']:.4f} GA=({p['ci95_low']:.4f},{p['ci95_high']:.4f}) aynı liste={data['retrieval']['identical_top5_faiss_hybrid']}")
    print(f"  üretim hata tipolojisi={data['generation']['error_categories']}")
    print(f"  SQL n={data['sql']['n']} ok={data['sql']['executed_ok']} hata={data['sql']['failed_ids']} benzersiz_id={data['sql']['ids_unique']}")
    print(f"  corpus sayfa={data['corpus']['total_pages']} parça={data['corpus']['total_chunks']}")


if __name__ == "__main__":
    main()
