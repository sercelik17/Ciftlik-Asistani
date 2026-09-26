# Hayvancılık RAG Tez Uyarlaması — Faz 1

Bu paket, `KaanSezen1923/Sut_Sihirbazi_Bitirme_Projesi` içindeki mevcut FastAPI + PostgreSQL + LangGraph altyapısını, tez konusu olan **LangChain + RAG tabanlı hayvancılık sohbet robotuna** dönüştürmek için hazırlanmış ek katmandır.

## Yeni mimari

```text
Kullanıcı
   |
   v
LangChain Query Router
   |-------------------|-------------------|
   v                   v                   v
  SQL                  RAG              HYBRID
   |                   |                   |
Mevcut            BM25 + FAISS         SQL sonucu
Tool Agent         Hybrid Search          +
   |                   |               RAG bağlamı
PostgreSQL         Kaynak chunk'ları       |
   |                   |                   v
   |                   v               Yerel LLM
   |              Yerel LLM                |
   |                   |                   |
   --------------------+-------------------
                       |
                       v
             Kaynak gösteren Türkçe yanıt
```

## Neler eklendi?

- PDF/TXT/Markdown doküman yükleme
- `RecursiveCharacterTextSplitter` ile chunking
- Ollama `bge-m3` embedding
- FAISS dense retrieval
- BM25 sparse retrieval
- Weighted Reciprocal Rank Fusion ile gerçek hibrit retrieval
- `[K1]`, `[K2]` biçiminde kaynaklı RAG yanıtı
- RAG / SQL / HYBRID / CHAT query router
- Mevcut `tool_rag.py` ile adaptör entegrasyonu
- JWT korumalı FastAPI tez endpoint'i

## 1. Dosyaları mevcut repoya kopyalama

Bu paketteki `Backend/thesis_rag/` klasörünü mevcut projenizin `Backend/` klasörüne kopyalayın.
Ayrıca `knowledge_base/`, `requirements_rag.txt` ve `.env.rag.example` dosyalarını da kopyalayın.

## 2. Bağımlılıklar

Mevcut backend sanal ortamında:

```bash
pip install -r requirements.txt
pip install -r requirements_rag.txt
```

Ollama'da çok dilli embedding modelini çekin:

```bash
ollama pull bge-m3
```

`bge-m3`, çok dilli dense retrieval için kullanılır. BM25 ise kelime-temelli sparse arama katmanıdır.

## 3. Dokümanları ekleme

Güvenilir PDF'leri `Backend/knowledge_base/` altına koyun. Örnek:

```text
knowledge_base/
├── mastitis/
│   └── mastitis_rehberi.pdf
├── besleme/
│   └── sut_sigiri_besleme.pdf
└── sut_kalitesi/
    └── sut_kalitesi.pdf
```

## 4. İndeksi oluşturma

Backend klasöründeyken:

```bash
python -m thesis_rag.build_index
```

Başarılıysa `rag_index/faiss/`, `rag_index/chunks.json` ve `rag_index/manifest.json` oluşur.

## 5. API'ye bağlama

`api.py` içine:

```python
from thesis_rag.api_router import create_thesis_router
```

ekleyin. Mevcut `get_current_user()` fonksiyonu tanımlandıktan sonra:

```python
app.include_router(create_thesis_router(get_current_user))
```

ekleyin.

`api_integration.patch` aynı değişikliği özetler.

## 6. Test

Önce mevcut login endpoint'inden JWT alın. Sonra:

```bash
curl -X POST http://localhost:8000/query/thesis/ \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"question":"Mastitis süt verimini nasıl etkiler?"}'
```

Beklenen örnek yapı:

```json
{
  "route": "RAG",
  "answer": "... [K1] ...",
  "sources": [
    {"id":"K1","title":"mastitis_rehberi.pdf","page":12,"chunk_id":"chunk-000042"}
  ]
}
```

Karma örnek:

```json
{
  "question": "Bugün sütü en fazla düşen ineğin olası nedenlerini kaynaklara göre yorumla."
}
```

Bu soru `HYBRID` rotasına giderek mevcut çiftlik/SQL ajanı sonucu ile RAG kaynaklarını birleştirir.

## Tez açısından metodolojik katkı

Bu mimaride iki farklı bilgi türü aynı sohbet robotunda birleştirilir:

1. **Yapılandırılmış veri:** PostgreSQL'deki çiftlik/sağım kayıtları.
2. **Yapılandırılmamış bilgi:** PDF ve metin biçimindeki hayvancılık/veteriner kaynakları.

Dense FAISS retrieval ile semantik benzerlik, BM25 ile terim eşleşmesi kullanılır. Sonuçlar Weighted Reciprocal Rank Fusion ile birleştirilir. Böylece FAISS-only RAG ile Hybrid RAG deneysel olarak karşılaştırılabilir.

## Faz 2 için yapılacaklar

- Her SQL aracına zorunlu `ciftlik_id` filtresi eklemek (tenant isolation).
- Orijinal `tool_rag.py` içindeki cloud router'a ham tool verisi geri gönderme akışını kaldırmak.
- RAGAS / Recall@K / Precision@K / MRR değerlendirme setini eklemek.
- FAISS-only ve BM25+FAISS ablation karşılaştırması yapmak.
- Mobil chat ekranında kaynak kartlarını göstermek.
- Kaynak envanterini ve tez deney setini sabitlemek.

## Güvenlik notu

Orijinal projede `tool_rag.py` sorgularının tümü `ciftlik_id` ile sınırlandırılmadığı için bu Faz 1 paketi **tek çiftlikli tez prototipi** için uygundur. Çok kullanıcılı/production kullanımda SQL katmanındaki tenant isolation tamamlanmalıdır.
