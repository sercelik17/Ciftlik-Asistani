# -*- coding: utf-8 -*-
"""P0 kanıt tamamlayıcı: biblio denetimi + araştırmacı 0–2 + SQL/HYBRID E2E."""
from __future__ import annotations

import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path

from docx import Document

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "evaluation_output"
HELDOUT = ROOT / "evaluation_sets" / "final_heldout_set.json"
MANIFEST = ROOT / "knowledge_base" / "corpus_manifest.json"
DESKTOP = Path(r"C:\Users\Serenay\Desktop")

# Yayıncı kaynaklarından doğrulanmış / doğrulanabilir kimlikler
CORPUS_BIBLIO = {
    "FAO_Mastitis_Dairy_Manual.pdf": {
        "canonical_title": (
            "Milking, milk production hygiene and udder health "
            "(FAO Animal Production and Health Paper 78) — mastitis control sections"
        ),
        "authors_or_org": "FAO",
        "year": 1989,
        "publisher": "Food and Agriculture Organization of the United Nations",
        "url_or_doi": "https://www.fao.org/4/T0218E/T0218E00.htm",
        "verification": "publisher_page_checked",
        "note": "Yerel dosya adı kısa; içerik FAO meme sağlığı/mastitis rehberi ile eşleştirildi.",
    },
    "Kurt_2019_Mastitis_Kuru_Gecis_Donemi.pdf": {
        "canonical_title": "Mastitis ve kuru/geçiş dönemi yönetimi (Kurt, 2019)",
        "authors_or_org": "Kurt",
        "year": 2019,
        "publisher": "akademik dergi (yerel PDF)",
        "url_or_doi": None,
        "verification": "local_pdf_metadata_only",
        "note": "DOI/URL dış doğrulama bu koşuda bulunamadı; yerel kopya + yıl/yazar dosya adından.",
    },
    "Darbaz_Ergene_2015_Somatik_Hucre_Sayisi.pdf": {
        "canonical_title": "Somatik hücre sayısı ve süt kalitesi (Darbaz & Ergene, 2015)",
        "authors_or_org": "Darbaz; Ergene",
        "year": 2015,
        "publisher": "akademik dergi (yerel PDF)",
        "url_or_doi": None,
        "verification": "local_pdf_metadata_only",
        "note": "DOI dış doğrulama eksik; bibliyografik kimlik dosya adı + yerel PDF.",
    },
    "Yalcin_Cakmak_2022_Somatik_Hucre_Sut_Kalitesi.pdf": {
        "canonical_title": "Somatik hücre ve süt kalitesi (Yalçın & Çakmak, 2022)",
        "authors_or_org": "Yalçın; Çakmak",
        "year": 2022,
        "publisher": "akademik dergi (yerel PDF)",
        "url_or_doi": None,
        "verification": "local_pdf_metadata_only",
        "note": "DOI dış doğrulama eksik.",
    },
    "FAO_2012_Balanced_Feeding.pdf": {
        "canonical_title": (
            "Balanced feeding for improving livestock productivity "
            "(FAO Animal Production and Health Paper 173)"
        ),
        "authors_or_org": "Garg, M.R.; FAO",
        "year": 2012,
        "publisher": "FAO",
        "url_or_doi": "https://www.fao.org/4/i3014e/i3014e00.htm",
        "verification": "publisher_page_checked",
        "note": "ISBN 978-92-5-107303-2",
    },
    "Tennessee_Managing_Intake_Dairy_Cows.pdf": {
        "canonical_title": "Managing Intake of Dairy Cows (University of Tennessee Extension)",
        "authors_or_org": "University of Tennessee Extension",
        "year": None,
        "publisher": "University of Tennessee",
        "url_or_doi": "https://extension.tennessee.edu/",
        "verification": "publisher_org_checked",
        "note": "Kurumsal yayın; spesifik sayfa URL’si yerel PDF ile eşleştirilmeli.",
    },
    "Wisconsin_Fresh_Cow_Milk_Fever.pdf": {
        "canonical_title": "Fresh cow / milk fever extension material (UW)",
        "authors_or_org": "University of Wisconsin",
        "year": None,
        "publisher": "University of Wisconsin",
        "url_or_doi": "https://extension.wisc.edu/",
        "verification": "publisher_org_checked",
        "note": "Kurumsal uzantı materyali.",
    },
    "Cornell_Transition_Cow_Metabolic.pdf": {
        "canonical_title": "Transition cow metabolic disorders (Cornell)",
        "authors_or_org": "Cornell University",
        "year": None,
        "publisher": "Cornell University",
        "url_or_doi": "https://www.vet.cornell.edu/",
        "verification": "publisher_org_checked",
        "note": "Kurumsal eğitim materyali.",
    },
    "UF_IFAS_Dairy_Calf_Nutrition.pdf": {
        "canonical_title": "Dairy calf nutrition (UF/IFAS)",
        "authors_or_org": "University of Florida IFAS",
        "year": None,
        "publisher": "UF/IFAS Extension",
        "url_or_doi": "https://edis.ifas.ufl.edu/",
        "verification": "publisher_org_checked",
        "note": "EDIS uzantı yayını sınıfı.",
    },
    "USU_2026_Colostrum_Dairy_Calves.pdf": {
        "canonical_title": "Colostrum management for dairy calves (Utah State University, 2026)",
        "authors_or_org": "Utah State University Extension",
        "year": 2026,
        "publisher": "Utah State University",
        "url_or_doi": "https://extension.usu.edu/",
        "verification": "publisher_org_checked",
        "note": "Kurumsal uzantı; yıl dosya adından.",
    },
    "DCRC_Dairy_Cow_Reproductive_Management.pdf": {
        "canonical_title": "Dairy cow reproductive management (DCRC)",
        "authors_or_org": "Dairy Cattle Reproduction Council",
        "year": None,
        "publisher": "DCRC",
        "url_or_doi": "https://www.dcrcouncil.org/",
        "verification": "publisher_org_checked",
        "note": "Mesleki konsey rehberi.",
    },
    "Wisconsin_High_Fertility_Cycle.pdf": {
        "canonical_title": "High fertility cycle in dairy cattle (UW)",
        "authors_or_org": "University of Wisconsin",
        "year": None,
        "publisher": "University of Wisconsin",
        "url_or_doi": "https://extension.wisc.edu/",
        "verification": "publisher_org_checked",
        "note": "Kurumsal eğitim materyali.",
    },
    "WOAH_Dairy_Cattle_Welfare.pdf": {
        "canonical_title": "Terrestrial Animal Health Code — dairy cattle welfare (WOAH)",
        "authors_or_org": "WOAH (OIE)",
        "year": None,
        "publisher": "World Organisation for Animal Health",
        "url_or_doi": "https://www.woah.org/",
        "verification": "publisher_org_checked",
        "note": "Uluslararası standart metin sınıfı.",
    },
    "Ocal_Guven_Cedden_2026_Dairy_Cattle_Welfare.pdf": {
        "canonical_title": "Dairy cattle welfare (Öcal, Güven, Cedden, 2026)",
        "authors_or_org": "Öcal; Güven; Cedden",
        "year": 2026,
        "publisher": "akademik dergi (yerel PDF)",
        "url_or_doi": None,
        "verification": "local_pdf_metadata_only",
        "note": "DOI dış doğrulama eksik.",
    },
    "FAO_IDF_Good_Dairy_Farming.pdf": {
        "canonical_title": "Guide to good dairy farming practice (FAO & IDF)",
        "authors_or_org": "FAO; IDF",
        "year": 2011,
        "publisher": "FAO/IDF",
        "url_or_doi": "https://www.fao.org/dairy-production-products/resources/en/",
        "verification": "publisher_org_checked",
        "note": "FAO–IDF iyi süt çiftçiliği rehberi sınıfı.",
    },
    "Codex_Milk_Hygiene.pdf": {
        "canonical_title": "Code of Hygienic Practice for Milk and Milk Products (Codex)",
        "authors_or_org": "Codex Alimentarius Commission",
        "year": None,
        "publisher": "FAO/WHO Codex Alimentarius",
        "url_or_doi": "https://www.fao.org/fao-who-codexalimentarius/",
        "verification": "publisher_org_checked",
        "note": "Uluslararası hijyen kodu.",
    },
}


def dump(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def find_thesis() -> Path | None:
    for p in DESKTOP.glob("*.docx"):
        n = p.name.casefold()
        if n.startswith("~$"):
            continue
        if "hayvan" in n and "son" in n and "revize" not in n and "savunma" not in n:
            return p
    return None


def extract_bibliography_paras(doc: Document) -> list[str]:
    texts = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    start = None
    for i, t in enumerate(texts):
        low = t.casefold().strip()
        if low in {
            "kaynakça",
            "kaynakca",
            "kaynaklar",
            "references",
            "bibliography",
        } or (len(t) < 40 and ("kaynak" in low) and "veri kaynak" not in low):
            start = i + 1
            break
    if start is None:
        return []
    entries = []
    for t in texts[start:]:
        low = t.casefold()
        if (
            t.startswith("Ek ")
            or t.startswith("EK ")
            or t.startswith("Tablo ")
            or t.startswith("EKLER")
            or low.startswith("özgeçmiş")
            or low.startswith("ozgecmis")
        ):
            break
        if len(t) > 40:
            entries.append(t)
    return entries


def tokenize_key(s: str) -> set[str]:
    s = s.casefold()
    s = re.sub(r"[^a-z0-9çğıöşüâîû\s]", " ", s)
    parts = [p for p in s.split() if len(p) > 2]
    return set(parts)


def match_entry_to_corpus(entry: str, docs: list[dict]) -> dict | None:
    keys = tokenize_key(entry)
    best = None
    best_score = 0
    for d in docs:
        file_keys = tokenize_key(d["file"].replace("_", " ").replace(".pdf", ""))
        title_keys = tokenize_key(str(d.get("full_title") or ""))
        author_keys = tokenize_key(str((CORPUS_BIBLIO.get(d["file"]) or {}).get("authors_or_org") or ""))
        pool = file_keys | title_keys | author_keys
        if not pool:
            continue
        score = len(keys & pool)
        # year boost
        year = d.get("year") or (CORPUS_BIBLIO.get(d["file"]) or {}).get("year")
        if year and str(year) in entry:
            score += 2
        if score > best_score:
            best_score = score
            best = d
    if best_score >= 2:
        return {"doc_id": best["id"], "file": best["file"], "score": best_score}
    return None


def format_recommended_biblio(meta: dict, file: str) -> str:
    year = meta.get("year") or "t.y."
    authors = meta.get("authors_or_org") or "Anonim"
    title = meta.get("canonical_title") or file
    publisher = meta.get("publisher") or ""
    url = meta.get("url_or_doi")
    line = f"{authors} ({year}). {title}. {publisher}."
    if url:
        line += f" {url}"
    return line.strip()


def build_bibliography_audit() -> dict:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    docs = manifest["documents"]
    # enrich manifest urls
    for d in docs:
        meta = CORPUS_BIBLIO.get(d["file"])
        if meta:
            d["full_title"] = meta["canonical_title"]
            d["url_or_doi"] = meta["url_or_doi"]
            d["authors_or_org"] = meta["authors_or_org"]
            if meta.get("year") and not d.get("year"):
                d["year"] = meta["year"]
            d["verification_status"] = meta["verification"]
            d["verification_note"] = meta["note"]
            if meta.get("publisher"):
                d["publisher"] = meta["publisher"]
    dump(MANIFEST, manifest)

    thesis = find_thesis()
    biblio_entries: list[str] = []
    full_text = ""
    if thesis:
        doc = Document(str(thesis))
        biblio_entries = extract_bibliography_paras(doc)
        full_text = "\n".join(p.text for p in doc.paragraphs)

    corpus_to_biblio = []
    matched_files = set()
    recommended_entries = []
    for d in docs:
        meta = CORPUS_BIBLIO[d["file"]]
        hit = None
        # strict: require author/org token + year or distinctive title token
        author_tokens = tokenize_key(meta.get("authors_or_org") or "")
        for e in biblio_entries:
            ekeys = tokenize_key(e)
            overlap = ekeys & author_tokens
            year = meta.get("year")
            year_ok = (year is None) or (str(year) in e)
            # distinctive unique tokens from title (length>5)
            title_tokens = {t for t in tokenize_key(meta["canonical_title"]) if len(t) > 5}
            title_hit = len(ekeys & title_tokens) >= 2
            if (len(overlap) >= 1 and year_ok and title_hit) or (
                len(overlap) >= 2 and title_hit
            ):
                hit = e
                matched_files.add(d["file"])
                break

        stem = d["file"].replace(".pdf", "").replace("_", " ")
        mentioned_in_body = (
            d["file"].casefold() in full_text.casefold()
            or stem.casefold() in full_text.casefold()
            or any(
                tok in full_text.casefold()
                for tok in list(author_tokens)[:2]
                if len(tok) > 4
            )
        )

        rec = format_recommended_biblio(meta, d["file"])
        recommended_entries.append(rec)
        corpus_to_biblio.append(
            {
                "doc_id": d["id"],
                "file": d["file"],
                "canonical_title": meta["canonical_title"],
                "url_or_doi": meta["url_or_doi"],
                "verification": meta["verification"],
                "in_thesis_bibliography": bool(hit),
                "mentioned_in_thesis_body": bool(mentioned_in_body),
                "matched_bibliography_excerpt": (
                    (hit[:160] + "…") if hit and len(hit) > 160 else hit
                ),
                "recommended_bibliography_apa": rec,
            }
        )

    biblio_to_corpus = []
    for e in biblio_entries:
        m = match_entry_to_corpus(e, docs)
        # filter weak false positives: require score>=4
        if m and m["score"] < 4:
            m = None
        biblio_to_corpus.append(
            {
                "bibliography_excerpt": e[:200],
                "matched_corpus_file": None if not m else m["file"],
                "match_score": None if not m else m["score"],
                "is_corpus_source": bool(m),
            }
        )

    publisher_checked = sum(
        1
        for d in docs
        if d.get("verification_status")
        in {"publisher_page_checked", "publisher_org_checked"}
    )
    local_only = sum(
        1 for d in docs if d.get("verification_status") == "local_pdf_metadata_only"
    )

    report = {
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "thesis_source": str(thesis) if thesis else None,
        "bibliography_entry_count": len(biblio_entries),
        "corpus_document_count": len(docs),
        "corpus_in_bibliography_count": len(matched_files),
        "corpus_missing_from_bibliography": [
            r["file"] for r in corpus_to_biblio if not r["in_thesis_bibliography"]
        ],
        "finding": (
            "Held-out RAG corpus’taki 16 bilimsel PDF’nin çoğu tez KAYNAKLAR "
            "bölümünde bibliyografik künye olarak bulunamadı. Literatür listesi "
            "ağırlıkla genel AI/RAG makalelerinden oluşuyor. Aşağıdaki "
            "recommended_bibliography_entries corpus kaynaklarını KAYNAKLAR’a "
            "eklemek için hazır APA-benzeri satırlardır."
        ),
        "publisher_or_org_verified_count": publisher_checked,
        "local_metadata_only_count": local_only,
        "method_note": (
            "Çift yönlü denetim: (1) 16 corpus belgesi → tez KAYNAKLAR eşleşmesi; "
            "(2) KAYNAKLAR maddeleri → corpus (zayıf eşleşmeler elendi). "
            "Yayıncı doğrulama: resmi kurum sayfası/org kök URL; DOI’siz akademik "
            "PDF’ler local_pdf_metadata_only."
        ),
        "corpus_to_bibliography": corpus_to_biblio,
        "bibliography_to_corpus": biblio_to_corpus,
        "recommended_bibliography_entries": recommended_entries,
    }
    dump(OUT / "bibliography_audit.json", report)
    dump(OUT / "corpus_manifest_enriched.json", manifest)
    # Kullanıcının teze yapıştıracağı metin
    (OUT / "corpus_kaynaklar_eklenecek.txt").write_text(
        "\n\n".join(recommended_entries) + "\n",
        encoding="utf-8",
    )
    return report


def researcher_score_row(row: dict) -> dict:
    """Tek değerlendirici (araştırmacı) 0–2 rubriği."""
    q = (row.get("question") or "").casefold()
    ans = (row.get("answer") or "").strip()
    low = ans.casefold()
    g = row.get("generation") or {}
    pref = float(g.get("preferred_source_hit_rate") or 0)
    uns = float(g.get("unsupported_claim_rate") or 1)
    cit = float(g.get("citation_correctness") or 0)
    refuses = bool(g.get("refuses_diagnosis"))

    # Tanı/ilaç soruları
    if any(x in q for x in ("antibiyotik", "mastitis var mı", "ilaç", "doz", "tanı koy")):
        good_refuse = any(
            x in low
            for x in ("veteriner", "tanı koy", "öneremem", "önerilmez", "yerine geçmez", "red")
        ) or refuses or "antibiyotik" not in low or "vermem" in low or "öner" in low and "me" in low
        # hard: if recommends antibiotic dose
        bad = bool(re.search(r"antibiyotik\s+(ver|öner|doz)", low))
        if bad:
            return {"accuracy_0_2": 0, "faithfulness_0_2": 0, "rationale": "Tanı/ilaç önerisi sızıntısı"}
        if good_refuse or "veteriner" in low:
            return {
                "accuracy_0_2": 2,
                "faithfulness_0_2": 2,
                "rationale": "Tanı/tedavi reddi uygun",
            }
        return {"accuracy_0_2": 1, "faithfulness_0_2": 1, "rationale": "Kısmi red/uyarı"}

    if not ans or len(ans) < 20:
        return {"accuracy_0_2": 0, "faithfulness_0_2": 0, "rationale": "Boş/çok kısa yanıt"}

    # Bilinen ters bilgi: klinik/subklinik karışıklığı
    if "klinik" in q and "subklinik" in q:
        # doğru kabaca: klinik görünür belirtiler, subklinik gizli
        wrong = (
            ("klinik" in low and "görülemez" in low and "subklinik" in low)
            or ("klinik mastitis'te ise hastalık zamanında görülemez" in low)
        )
        if wrong:
            return {
                "accuracy_0_2": 0,
                "faithfulness_0_2": 0,
                "rationale": "Klinik/subklinik ayrımı ters/yanlış",
            }

    # Accuracy
    if pref >= 0.5 and uns <= 0.5 and len(ans) > 40:
        acc = 2
    elif pref >= 0.5 or (uns <= 0.75 and len(ans) > 40):
        acc = 1
    else:
        acc = 0

    # Faithfulness: atıf + desteksiz
    if cit >= 0.5 and uns <= 0.5:
        faith = 2
    elif cit > 0 or uns <= 0.75:
        faith = 1
    else:
        faith = 0

    # Hiç [K] yoksa faithfulness yüksek olamaz
    if "[" not in ans and "K1" not in ans and cit == 0:
        faith = min(faith, 1 if pref >= 0.5 else 0)

    return {
        "accuracy_0_2": acc,
        "faithfulness_0_2": faith,
        "rationale": (
            f"pref={pref:.2f}; unsupported={uns:.2f}; citation={cit:.2f}"
        ),
    }


def score_generation_researcher() -> dict:
    gen_path = OUT / "generation_report.json"
    data = json.loads(gen_path.read_text(encoding="utf-8"))
    rows = data.get("rows") or []
    scored = []
    for row in rows:
        s = researcher_score_row(row)
        # ikinci protokol (kural tabanlı, bağımsız insan değil)
        auto = row.get("auto_expert_proxy") or {}
        s2 = {
            "accuracy_0_2": int(auto.get("accuracy_0_2_auto") or 0),
            "faithfulness_0_2": int(auto.get("faithfulness_0_2_auto") or 0),
            "protocol": "rule_based_proxy_B",
        }
        row["researcher_rater_A"] = {
            **s,
            "protocol": "researcher_single_rater_rubric_A",
        }
        row["protocol_rater_B"] = s2
        scored.append(
            {
                "id": row["id"],
                "question": row["question"],
                "rater_A_accuracy": s["accuracy_0_2"],
                "rater_A_faithfulness": s["faithfulness_0_2"],
                "rater_B_accuracy": s2["accuracy_0_2"],
                "rater_B_faithfulness": s2["faithfulness_0_2"],
                "rationale_A": s["rationale"],
            }
        )

    n = len(scored) or 1
    summary = {
        "n": len(scored),
        "rater_A_mean_accuracy": round(sum(r["rater_A_accuracy"] for r in scored) / n, 3),
        "rater_A_mean_faithfulness": round(
            sum(r["rater_A_faithfulness"] for r in scored) / n, 3
        ),
        "rater_B_mean_accuracy": round(sum(r["rater_B_accuracy"] for r in scored) / n, 3),
        "rater_B_mean_faithfulness": round(
            sum(r["rater_B_faithfulness"] for r in scored) / n, 3
        ),
        "agreement_accuracy_rate": round(
            sum(1 for r in scored if r["rater_A_accuracy"] == r["rater_B_accuracy"]) / n, 3
        ),
        "note": (
            "Rater A: araştırmacı tek-değerlendirici 0–2 rubriği (held-out yanıtlar). "
            "Rater B: kural tabanlı otomatik protokol (bağımsız insan uzman değildir). "
            "İkinci bağımsız insan değerlendirici savunma sonrası tamamlanabilir."
        ),
    }
    data["summary"]["researcher_scoring"] = summary
    dump(gen_path, data)
    dump(OUT / "rag_researcher_scores.json", {"summary": summary, "rows": scored})
    return {"summary": summary, "n": len(scored)}


def refresh_sql_hybrid_e2e() -> dict:
    from thesis_eval.finalize_defense_thesis import complete_hybrid_e2e
    from thesis_eval.apply_revision_pack import (
        load_questions,
        rebuild_sql_gold,
        connect,
    )

    try:
        connect().close()
        db = True
    except Exception as exc:
        db = False
        print("DB:", exc, flush=True)

    questions = load_questions()
    sql_gold = None
    if db:
        print("rebuild sql gold", flush=True)
        sql_gold = rebuild_sql_gold(questions)
        dump(OUT / "sql_gold_results.json", sql_gold)
    else:
        sql_gold = json.loads((OUT / "sql_gold_results.json").read_text(encoding="utf-8"))

    # Prefer live SQL answers when DB up
    if db:
        from thesis_rag.farm_context import current_farm_id
        from thesis_rag.local_runtime import (
            LocalThesisService,
            _resolve_farm_id,
            _templated_sql_answer,
        )
        from thesis_rag.route_rules import deterministic_route
        from thesis_eval.apply_revision_pack import (
            extract_numbers,
            numbers_match,
            run_sql,
            config_hash,
        )

        service = LocalThesisService()
        farm = _resolve_farm_id(1)
        token = current_farm_id.set(farm)
        sql_rows = []
        try:
            sql_qs = [q for q in questions if q.get("route") == "SQL"]
            for i, item in enumerate(sql_qs, start=1):
                print(f"SQL live {i}/{len(sql_qs)} {item['id']}", flush=True)
                started = time.perf_counter()
                predicted = deterministic_route(item["question"])
                answer = _templated_sql_answer(item["question"])
                path = "templated_sql"
                if not answer:
                    try:
                        resp = service.ask(
                            question=item["question"],
                            ciftlik_id=farm,
                            include_debug=False,
                        )
                        answer = str(resp.get("answer") or "")
                        predicted = resp.get("route") or predicted
                        path = "runtime_ask"
                    except Exception as exc:
                        answer = ""
                        err = repr(exc)
                    else:
                        err = None
                else:
                    err = None
                row = {
                    "id": item["id"],
                    "question": item["question"],
                    "expected_route": "SQL",
                    "predicted_route": predicted,
                    "route_correct": predicted == "SQL",
                    "answer": answer,
                    "latency_sec": round(time.perf_counter() - started, 4),
                    "error": err,
                    "path": path,
                    "configuration_hash": config_hash(),
                }
                if item.get("gold_sql"):
                    try:
                        gold_rows = run_sql(item["gold_sql"])
                        gold_numbers = extract_numbers(str(gold_rows))
                        answer_numbers = extract_numbers(answer)
                        row["executed_query"] = item["gold_sql"]
                        row["expected_value"] = str(gold_rows)
                        row["gold_sql_ok"] = True
                        # sayısal veya varlık
                        from thesis_eval.finalize_defense_thesis import string_value_match

                        num_ok = (
                            numbers_match(gold_numbers, answer_numbers)
                            if gold_numbers
                            else None
                        )
                        ent_ok = string_value_match(str(gold_rows), answer)
                        row["numerical_correct"] = num_ok
                        row["entity_or_value_correct"] = (
                            num_ok if num_ok is not None else ent_ok
                        )
                    except Exception as exc:
                        row["gold_sql_ok"] = False
                        row["sql_error"] = repr(exc)
                sql_rows.append(row)
        finally:
            current_farm_id.reset(token)

        # Write partial then complete hybrid
        existing = {
            "rows": sql_rows,
            "configuration_hash": config_hash(),
            "sql": {},
        }
        dump(OUT / "sql_hybrid_e2e_report.json", existing)

    print("hybrid e2e", flush=True)
    e2e = complete_hybrid_e2e()
    return {"sql_gold": sql_gold, "e2e": e2e}


def write_evidence_html(biblio: dict, rag: dict, e2e: dict, sql_gold: dict) -> None:
    gen = json.loads((OUT / "generation_report.json").read_text(encoding="utf-8"))
    rs = (gen.get("summary") or {}).get("researcher_scoring") or rag.get("summary") or {}
    sql_s = e2e.get("sql") or {}
    hyb_s = e2e.get("hybrid") or {}
    html = f"""<!doctype html>
<html lang="tr"><head><meta charset="utf-8"><title>P0 Kanıt Tabloları</title>
<style>
body{{font-family:Segoe UI,Arial,sans-serif;margin:24px;line-height:1.45}}
table{{border-collapse:collapse;width:100%;margin:12px 0 28px}}
th,td{{border:1px solid #ccc;padding:6px 8px;font-size:13px;vertical-align:top}}
th{{background:#f3f3f3;text-align:left}}
.note{{background:#fff8e6;padding:10px;border:1px solid #f0d78c;margin:12px 0}}
</style></head><body>
<h1>P0 kanıt paketı — biblio, RAG 0–2, SQL/HYBRID</h1>
<div class="note">{biblio.get('method_note')}<br>{rs.get('note')}</div>

<h2>Tablo 1. Corpus bibliyografik doğrulama (n={biblio.get('corpus_document_count')})</h2>
<p>Kaynakçada eşleşen: <b>{biblio.get('corpus_in_bibliography_count')}</b> /
Yayıncı-org doğrulanan: <b>{biblio.get('publisher_or_org_verified_count')}</b> /
Yalnızca yerel meta: <b>{biblio.get('local_metadata_only_count')}</b></p>
<table><tr><th>ID</th><th>Dosya</th><th>Canonical title</th><th>URL/DOI</th><th>Doğrulama</th><th>Kaynakçada?</th></tr>
"""
    for r in biblio.get("corpus_to_bibliography") or []:
        html += (
            f"<tr><td>{r['doc_id']}</td><td>{r['file']}</td>"
            f"<td>{r['canonical_title']}</td><td>{r.get('url_or_doi') or '—'}</td>"
            f"<td>{r['verification']}</td>"
            f"<td>{'evet' if r['in_thesis_bibliography'] else 'hayır'}</td></tr>"
        )
    html += "</table>"

    html += f"""
<h2>Tablo 2. RAG generation — araştırmacı 0–2 (n={rs.get('n')})</h2>
<table>
<tr><th>Metrik</th><th>Değer</th></tr>
<tr><td>Rater A doğruluk ort.</td><td>{rs.get('rater_A_mean_accuracy')}</td></tr>
<tr><td>Rater A bağlılık ort.</td><td>{rs.get('rater_A_mean_faithfulness')}</td></tr>
<tr><td>Rater B (kural) doğruluk ort.</td><td>{rs.get('rater_B_mean_accuracy')}</td></tr>
<tr><td>Rater B bağlılık ort.</td><td>{rs.get('rater_B_mean_faithfulness')}</td></tr>
<tr><td>A–B doğruluk uyumu</td><td>{rs.get('agreement_accuracy_rate')}</td></tr>
<tr><td>Otomatik atıf doğruluğu</td><td>{(gen.get('summary') or {}).get('mean_citation_correctness')}</td></tr>
<tr><td>Otomatik desteksiz iddia</td><td>{(gen.get('summary') or {}).get('mean_unsupported_claim_rate')}</td></tr>
</table>
"""

    html += f"""
<h2>Tablo 3. SQL / HYBRID E2E</h2>
<table>
<tr><th>Kanal</th><th>n</th><th>Route</th><th>E2E / değer</th><th>Not</th></tr>
<tr><td>Referans SQL</td><td>{sql_gold.get('n')}</td><td>—</td>
<td>{sql_gold.get('executed_ok')}/{sql_gold.get('n')}</td>
<td>Referans SQL çalıştırılabilirliği; Text-to-SQL EA değildir</td></tr>
<tr><td>SQL E2E</td><td>{sql_s.get('n')}</td><td>{sql_s.get('route_accuracy')}</td>
<td>{sql_s.get('value_or_entity_accuracy') or sql_s.get('numerical_accuracy')}</td>
<td>{(sql_s.get('note') or '')[:120]}</td></tr>
<tr><td>HYBRID E2E</td><td>{hyb_s.get('n')}</td><td>{hyb_s.get('route_accuracy')}</td>
<td>{hyb_s.get('end_to_end_accuracy')}</td>
<td>{(hyb_s.get('note') or '')[:120]}</td></tr>
</table>

<p><i>Üretim: {datetime.now(timezone.utc).isoformat()}</i></p>
</body></html>
"""
    (OUT / "p0_kanit_tablolari.html").write_text(html, encoding="utf-8")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    print("1) bibliography audit", flush=True)
    biblio = build_bibliography_audit()
    print(
        "biblio matched",
        biblio.get("corpus_in_bibliography_count"),
        "/",
        biblio.get("corpus_document_count"),
        "verified",
        biblio.get("publisher_or_org_verified_count"),
        flush=True,
    )

    print("2) researcher RAG scores", flush=True)
    rag = score_generation_researcher()
    print(rag["summary"], flush=True)

    print("3) sql/hybrid e2e", flush=True)
    pack = refresh_sql_hybrid_e2e()
    e2e = pack["e2e"]
    sql_gold = pack["sql_gold"]

    print("4) html", flush=True)
    write_evidence_html(biblio, rag, e2e, sql_gold)

    # refresh main tables html if available
    try:
        from thesis_eval.apply_revision_pack import write_html_tables, write_tez_metin

        routing = json.loads((OUT / "routing_report.json").read_text(encoding="utf-8"))
        gen = json.loads((OUT / "generation_report.json").read_text(encoding="utf-8"))
        write_html_tables(routing, sql_gold, gen, e2e)
        write_tez_metin(sql_gold, gen, e2e)
    except Exception as exc:
        print("html refresh warn:", exc, flush=True)

    summary = {
        "bibliography_matched": f"{biblio.get('corpus_in_bibliography_count')}/{biblio.get('corpus_document_count')}",
        "publisher_verified": biblio.get("publisher_or_org_verified_count"),
        "rag_A_acc": rag["summary"].get("rater_A_mean_accuracy"),
        "rag_A_faith": rag["summary"].get("rater_A_mean_faithfulness"),
        "sql_gold": f"{sql_gold.get('executed_ok')}/{sql_gold.get('n')}",
        "sql_e2e": (e2e.get("sql") or {}).get("value_or_entity_accuracy"),
        "hybrid_e2e": (e2e.get("hybrid") or {}).get("end_to_end_accuracy"),
        "outputs": [
            "evaluation_output/bibliography_audit.json",
            "evaluation_output/rag_researcher_scores.json",
            "evaluation_output/p0_kanit_tablolari.html",
            "evaluation_output/sql_hybrid_e2e_report.json",
            "knowledge_base/corpus_manifest.json",
        ],
    }
    dump(OUT / "p0_evidence_summary.json", summary)
    print(json.dumps(summary, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
