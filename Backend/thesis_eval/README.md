# Akademik değerlendirme

Pilot 100 soru geliştirme setidir. Final sonuçlar held-out set ile alınır.

```bash
cd Backend

# LLM gerektirmeyen / düşük maliyetli görevler
python -m thesis_eval.run_academic_evaluation --task routing --test-set evaluation_sets/final_heldout_set.json
python -m thesis_eval.run_academic_evaluation --task retrieval
python -m thesis_eval.run_academic_evaluation --task fusion-ablation --pilot-set tez_test_seti_100.json

# Frozen sistemde uçtan uca final değerlendirme
python -m thesis_eval.run_academic_evaluation --task e2e --test-set evaluation_sets/final_heldout_set.json
```

Çıktılar `evaluation_output/` altına yazılır:

- `routing_report.json` — confusion matrix, Precision/Recall/F1, Macro-F1, %95 CI
- `retrieval_report.json` — BM25 / FAISS / Hybrid için P@5, R@5, MRR, nDCG@5
- `fusion_ablation_pilot.json` — 50/50, 60/40, 70/30
- `generation_report.json` — RAG üretim deneyi (atıf doğruluğu, desteksiz iddia, gecikme)
- `e2e_report.json` — SQL execution, sayısal doğruluk, HYBRID uçtan uca, latency dağılımı
- `reproducibility.json` — model, paket, donanım, prompt/config dökümü

## Tez belgesi revizyonu (10 Ekim 2026 raporu)

Rapordaki belge tarafı maddeleri mevcut deney kayıtlarından üretilir ve Word dosyasına uygulanır.

```bash
pip install -r requirements_rag.txt        # python-docx, pypdf, langchain-text-splitters

# 1) Paket: ek tablolar, eşleştirilmiş retrieval farkları, corpus künyeleri, Tartışma metni
python -m thesis_eval.build_thesis_revision
#    -> evaluation_output/revizyon_2026_10_10/tez_revizyon_paketi.html (+ CSV'ler, revision_data.json)

# 2) Tezi düzenle (önce --dry-run ile hangi çapaların bulunduğunu gör)
python -m thesis_eval.revise_thesis --src "C:/Users/Serenay/Downloads/hayvancılık güncel son.docx" --dry-run
python -m thesis_eval.revise_thesis --src "C:/Users/Serenay/Downloads/hayvancılık güncel son.docx" --retitle
#    -> ..._revize_2026-10-10.docx ; "UYGULANAMADI" satırları HTML paketinden elle yapıştırılır
```

`revise_thesis.py` şunları yapar: §2.6 sohbet/eksik cümle kalıntıları, RAG/AGR/Geri Alma terim birliği,
"ticari veri" → sentetik kayıt, §4.4 ve §5 çelişen cümleler, §4.3 SQL 23/24 açıklaması, §3.7 gold etiket protokolü,
§4.2 held-out–pilot örtüşme analizi, yeni §4.5–4.7 (eşleştirilmiş retrieval farkı, üretim hata tipolojisi, final gecikme),
yeni 5. TARTIŞMA bölümü (Sonuç → 6), sınırlılık eki, Ek Tablo 1 (24 satır, F-SQL019 dâhil, 8 sütun), Tablo 3.2 tam künye,
Tablo 3.4 sürüm/donanım, Ek 2–5 (89 soruluk yönlendirme logu, sorgu bazlı retrieval/üretim, prompt'lar), TABLOLAR dizini.

Betik **ölçülmemiş** bir şeyi ölçülmüş gibi yazmaz: SQL execution accuracy, HYBRID E2E ve uzman 0–2 puanı
`e2e` görevi ve insan değerlendirmesi (`evaluation_sets/human_eval_template.json`) tamamlanmadan "ölçülmedi" kalır.
