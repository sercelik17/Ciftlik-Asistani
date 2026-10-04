# Akademik değerlendirme setleri

## Pilot / geliştirme seti

`../tez_test_seti_100.json`

- 50 RAG + 30 SQL + 20 HYBRID
- Sistem geliştirilirken kullanıldığı için **final performans** olarak sunulmamalıdır
- Fusion ağırlığı (50/50, 60/40, 70/30) ablation bu set üzerinde yapılır

## Held-out final set

`final_heldout_set.json`

- RAG, SQL, HYBRID ve CHAT sınıflarının tamamını içerir
- Geliştirme sırasında kullanılmamış sorulardan oluşur
- Frozen sistem (prompt, model, ağırlık, Top-K) üzerinde bir kez çalıştırılmalıdır

## İnsan değerlendirme şeması

`human_eval_template.json`

- 0 = yanlış / kanıtsız
- 1 = kısmen doğru veya eksik destekli
- 2 = doğru ve kaynakla destekli
- İki bağımsız değerlendirici; uyum için Cohen's κ raporlanabilir
