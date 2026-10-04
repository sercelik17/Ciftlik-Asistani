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
- `e2e_report.json` — SQL execution, sayısal doğruluk, HYBRID uçtan uca, latency dağılımı
- `reproducibility.json` — model, paket, donanım, prompt/config dökümü
