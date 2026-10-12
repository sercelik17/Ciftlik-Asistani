# Çiftlik Asistanı

Yüksek Lisans Tez Projesi: Süt sığırcılığında yapılandırılmış çiftlik kayıtları ile bilimsel kaynakları aynı sohbet asistanında birleştiren RAG tabanlı karar destek sistemi.

**Geliştiren:** Serenay Çelikkaya  
**Tez:** Hayvancılık Sektöründe Yapay Zekâ Destekli Sohbet Robotu Geliştirme: LangChain ve RAG Teknolojileriyle Uygulamalı Bir Model

Sistem tanı koymaz; antibiyotik, ilaç veya doz önermez. Hayvan sağlığı kararları veteriner hekime aittir.

---

## Ne yapar?

Kullanıcı doğal dilde soru sorar. Sorgu yönlendirici isteği dört kanaldan birine alır:

| Kanal | Ne zaman |
|--------|----------|
| **SQL** | İnek sayısı, sağım, toplam süt, alarm gibi çiftlik kayıtları |
| **RAG** | Mastitis, besleme, buzağı sağlığı gibi kaynak temelli genel bilgi |
| **HYBRID** | Hem kayıt hem bilimsel arka plan gereken sorular |
| **CHAT** | Selamlaşma ve kısa sohbet |

RAG kanalında BGE-M3 (FAISS) ile BM25 birleştirilir (ağırlıklı RRF, 60/40). Yanıtlarda kaynak `[K1]`, `[K2]` biçiminde gösterilir.

PostgreSQL’deki inek, sağım ve alarm kayıtları **ticari işletme verisi değildir**; prototip ve değerlendirme için üretilmiş **sentetik** örneklerdir. Bilgi tabanı 16 açık bilimsel/rehber belgeden oluşur.

---

## Tez katkısı ve taban uygulama

Bu depodaki tez çalışması şunları kapsar:

- sorgu yönlendirme (SQL / RAG / HYBRID / CHAT)
- hibrit bilgi erişimi (FAISS + BM25 + Weighted RRF)
- SQL okuma güvenliği ve veteriner tanı reddi
- held-out akademik değerlendirme (yönlendirme, retrieval, SQL altın sonuçlar, üretim metrikleri)
- Torch’suz yerel çalışma yolu (`thesis_rag/local_runtime.py`)

Mobil arayüz, kimlik doğrulama, sürü/alarm ekranları ve temel çiftlik API’si, [Süt Sihirbazı bitirme projesi](https://github.com/KaanSezen1923/Sut_Sihirbazi_Bitirme_Projesi) üzerine kurulmuştur. Bu depo o çalışmanın çatalı değil, tez uyarlamasının kendi GitHub kopyasıdır; Git geçmişinde taban uygulamaya ait commit’ler durur.

---

## Özellikler

- Çiftlik kayıtlarına göre süt verimi, inek ve alarm sorgusu
- Kaynak gösterimli bilimsel yanıt
- Kullanıcı–çiftlik izolasyonu (`ciftlik_id`)
- Alarm ve sürü görüntüleme
- Sesli soru / sesli yanıt (desteklenen ortamlarda)
- Yanıt süresi gösterimi

---

## Teknoloji

| Bileşen | Kullanılan |
|---------|------------|
| LLM | Mistral (Ollama) |
| Gömme | BGE-M3 |
| Vektör indeksi | FAISS (L2) |
| Sözcüksel arama | BM25 |
| Birleştirme | Weighted RRF (0,60 / 0,40) |
| Backend | FastAPI, Python 3.12 |
| Veritabanı | PostgreSQL |
| Arayüz | React Native + Expo |

---

## Kurulum

### 1. Depoyu alın

```bash
git clone https://github.com/sercelik17/Ciftlik-Asistani.git
cd Ciftlik-Asistani
git checkout thesis-rag
```

### 2. Ollama

```bash
ollama pull mistral
ollama pull bge-m3
```

### 3. Backend

```bash
cd Backend
python -m venv venv
.\venv\Scripts\Activate.ps1   # Windows
pip install -r requirements.txt
```

`Backend/.env` dosyasını oluşturun (repoya **yüklemeyin**). RAG örneği: `Backend/.env.rag.example`.

```env
DB_HOST=localhost
DB_PORT=5433
DB_NAME=Sut_Sihirbazi
DB_USER=...
DB_PASSWORD=...
RAG_EMBED_MODEL=bge-m3
RAG_LLM=mistral
RAG_DENSE_WEIGHT=0.60
RAG_SPARSE_WEIGHT=0.40
```

PostgreSQL için Docker varsa:

```bash
docker compose up -d
```

İndeks yoksa:

```bash
python -m thesis_rag.build_index
```

Backend:

```bash
python -m uvicorn api:app --host 127.0.0.1 --port 8001
```

- API: http://127.0.0.1:8001  
- Swagger: http://127.0.0.1:8001/docs  
- RAG sağlık: http://127.0.0.1:8001/query/thesis/health  

### 4. Arayüz

```bash
cd mobileapp
npm install
npm run web
```

Web genelde http://localhost:8081 adresindedir.

---

## Örnek sorular

```text
Merhaba
Küpe numarası TR0001 olan Serap adlı ineğin verim durumu nasıldır?
Bugün sağılan toplam süt miktarı kaç litre?
Süt veriminde düşüş yaşayan riskli inekleri listele
Somatik hücre sayısının artması süt kalitesini nasıl etkiler?
```

---

## Akademik değerlendirme

Pilot küme (100 soru) geliştirme içindir; **final sonuç held-out settir** (89 soru: RAG, SQL, HYBRID, CHAT). Yönlendirme doğruluğu yanıt doğruluğu değildir.

```bash
cd Backend
python -m thesis_eval.run_academic_evaluation --task routing --test-set evaluation_sets/final_heldout_set.json
python -m thesis_eval.run_academic_evaluation --task retrieval
python -m thesis_eval.run_academic_evaluation --task fusion-ablation --pilot-set tez_test_seti_100.json
```

Raporlar `Backend/evaluation_output/` altındadır (`routing_report.json`, `retrieval_report.json`, `generation_report.json`, `sql_gold_results.json`, `tablolar.html`).

Özet (held-out): yönlendirme 89/89; retrieval’de BGE-M3 P@5 = 0,90, hibrit P@5 = 0,89, BM25 P@5 = 0,35. SQL referans sorgularının 24’ünden 23’ü beklenen değeri üretir (F-SQL019 şema hatası). RAG üretim kalitesi otomatik ölçütlerle düşüktür (atıf doğruluğu 0,30; desteksiz iddia 0,86); modelin SQL execution accuracy’si ve HYBRID uçtan uca doğruluk henüz ölçülmemiştir. Bu sınırlılıklar tezde açıkça raporlanır.

### Tez belgesi revizyonu

10 Ekim 2026 yeniden değerlendirme raporundaki belge maddeleri (ek tablolar, Tartışma bölümü, çelişen cümleler, terim birliği, corpus künyeleri) deney kayıtlarından üretilip Word dosyasına uygulanır:

```bash
cd Backend
python -m thesis_eval.build_thesis_revision
python -m thesis_eval.revise_thesis --src "<tez>.docx" --retitle
```

Ayrıntı: `Backend/thesis_eval/README.md`; paste edilebilir paket: `Backend/evaluation_output/revizyon_2026_10_10/tez_revizyon_paketi.html`.

---

## Proje yapısı

```text
Ciftlik-Asistani/
├── Backend/
│   ├── api.py
│   ├── thesis_rag/          # tez RAG/SQL/HYBRID/CHAT hattı
│   ├── thesis_eval/         # akademik ölçüm betikleri
│   ├── evaluation_sets/     # held-out ve şablonlar
│   ├── evaluation_output/   # raporlar ve teze yapıştırılacak tablolar
│   ├── knowledge_base/      # 16 belgelik derleme
│   └── rag_index/
├── mobileapp/               # Expo arayüz (giriş, asistan, sürü, istatistik)
└── README.md
```

---

## Sık sorunlar

| Sorun | Ne bakılır |
|-------------------|
| Arayüz API’ye bağlanmıyor | Backend `127.0.0.1:8001` |
| RAG yanıtı yok | Ollama, `mistral`, `bge-m3` |
| İndeks yok | `python -m thesis_rag.build_index` |
| Veritabanı hatası | PostgreSQL ve `Backend/.env` |
| 401 | Oturum / JWT |

---

## Lisans ve paylaşım

Öğrenci tez reposudur. `.env` ve gerçek parola GitHub’a konmaz.
