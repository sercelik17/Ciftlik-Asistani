# 🐄 Çiftlik Asistanı

> **Çiftlik Asistanı**, süt sığırcılığı alanında çiftçilere yönelik geliştirilmiş yapay zekâ destekli bir karar destek ve sohbet asistanıdır. Sistem; kullanıcının kendi çiftliğine ait PostgreSQL verileri ile bilimsel ve veterinerlik kaynaklarından oluşturulan RAG bilgi tabanını birlikte kullanarak doğal dilde sorulara yanıt verir.

Çiftlik Asistanı; **LangChain, RAG (Retrieval-Augmented Generation), PostgreSQL, FAISS, BM25, Ollama ve Mistral** teknolojilerini bir araya getirir.

---

## 📱 Uygulama Özellikleri

| Özellik | Açıklama |
|---------|----------|
| 💬 **Yapay Zekâ Sohbet Asistanı** | Süt sığırcılığı ve çiftlik yönetimiyle ilgili sorular doğal dilde sorulabilir |
| 🗄️ **Çiftlik Verisi Sorgulama** | PostgreSQL veritabanındaki inek, sağım, süt üretimi ve alarm kayıtları sorgulanabilir |
| 📚 **Kaynak Temelli RAG Yanıtları** | Bilimsel ve veterinerlik PDF kaynaklarından ilgili bilgiler getirilerek kaynaklandırılmış yanıtlar oluşturulur |
| 🔀 **Akıllı Sorgu Yönlendirme** | Sorular otomatik olarak SQL, RAG, HYBRID veya CHAT rotalarından uygun olana yönlendirilir |
| 🔎 **Hibrit Arama** | Bilgi erişiminde FAISS vektör araması ile BM25 anahtar kelime araması birlikte kullanılır |
| 📌 **Kaynak Gösterimi** | RAG yanıtlarında kullanılan bilimsel kaynaklar `[K1]`, `[K2]` biçiminde gösterilir |
| 🎤 **Sesli Soru Sorma** | Desteklenen ortamlarda kullanıcı sorusunu mikrofon aracılığıyla iletebilir |
| 🔊 **Sesli Yanıt** | Asistan yanıtları sesli olarak dinlenebilir |
| 🐄 **Sürü Görüntüleme** | İneklerin ve sürü durumunun kullanıcı arayüzünden görüntülenmesi sağlanır |
| 🚨 **Alarm Takibi** | Süt verimindeki önemli değişimler ve oluşturulan alarm kayıtları görüntülenebilir |
| ⏱️ **Yanıt Süresi** | Asistanın yanıt üretme süresi sohbet ekranında gösterilir |

---

## 🧠 Sistem Nasıl Çalışır?

Kullanıcının gönderdiği soru öncelikle **Query Router** tarafından analiz edilir.

Soru dört farklı işlem türünden birine yönlendirilir:

| Rota | Kullanım Amacı |
|------|----------------|
| **SQL** | Kullanıcının kendi çiftlik kayıtlarıyla ilgili sayısal veya veri tabanı sorguları |
| **RAG** | Genel süt sığırcılığı, hayvan sağlığı, besleme ve süt kalitesi gibi bilimsel bilgi gerektiren sorular |
| **HYBRID** | Hem çiftlik verisinin hem de bilimsel kaynak bilgisinin birlikte gerektiği sorular |
| **CHAT** | Selamlaşma ve kısa genel sohbetler |

### Örnek

**Kullanıcı:**

> Süt verimi en yüksek olan 10 ineği getir.

Bu soru **SQL** rotasına yönlendirilir ve PostgreSQL veritabanındaki çiftlik kayıtları kullanılır.

---

**Kullanıcı:**

> Somatik hücre sayısının artması süt kalitesini nasıl etkiler?

Bu soru **RAG** rotasına yönlendirilir. Sistem bilimsel dokümanlardan ilgili bölümleri bulur ve kaynaklandırılmış yanıt oluşturur.

---

**Kullanıcı:**

> Sütü en fazla düşen ineğin olası nedenleri nelerdir?

Bu tür bir soru çiftlik verisi ile bilimsel bilgiyi birlikte gerektirdiğinden **HYBRID** rotası kullanılır.

---

## 📖 Kullanım

### 1️⃣ Sisteme Giriş

Uygulama açıldığında kullanıcıyı **Çiftlik Asistanı giriş ekranı** karşılar.

Kullanıcı kayıtlı e-posta adresi ve parolası ile sisteme giriş yapar.

Başarılı giriş sonrasında kullanıcı kendi çiftliğine ait verilere erişebilir.

---

## 💬 2️⃣ Yazılı Soru Sorma

1. **Asistan** sekmesine girin.
2. Alt bölümde bulunan **"Çiftlik Asistanına sorun..."** alanına sorunuzu yazın.
3. **Enter** tuşuna veya gönder butonuna basın.
4. Soru backend sistemine iletilir.
5. Query Router soruyu uygun işlem rotasına yönlendirir.
6. Yanıt oluşturulduktan sonra sohbet ekranında görüntülenir.
7. RAG kullanılan yanıtlarda yararlanılan bilimsel kaynaklar ayrıca gösterilir.

### Örnek Sorular

```text
Süt verimi en yüksek olan 10 ineği getir.
```

```text
Bugünkü toplam süt üretimim ne kadar?
```

```text
Somatik hücre sayısının artması süt kalitesini nasıl etkiler?
```

```text
Mastitis nedir ve süt kalitesini nasıl etkileyebilir?
```

```text
Sütü azalan ineklerimi göster.
```

---

## 🎤 3️⃣ Sesli Soru Sorma

Desteklenen cihazlarda kullanıcı mikrofon butonu aracılığıyla sesli soru gönderebilir.

1. Mikrofon simgesine dokunun.
2. Mikrofon erişimine izin verin.
3. Sorunuzu sesli olarak ifade edin.
4. Kaydı sonlandırın.
5. Ses kaydı metne dönüştürülerek sorgu sistemine aktarılır.

> Ses özelliklerinin kullanılabilmesi için cihazın mikrofon erişimine izin verilmiş olması gerekir.

---

## 🔊 4️⃣ Yanıtı Sesli Dinleme

Asistan tarafından oluşturulan yanıtlar desteklenen cihazlarda sesli olarak dinlenebilir.

Yanıtın yanında bulunan hoparlör simgesi kullanılarak metin seslendirme işlemi başlatılabilir veya durdurulabilir.

---

## 📚 RAG Bilgi Tabanı

Çiftlik Asistanı yalnızca büyük dil modelinin önceden öğrendiği bilgilere dayanmaz.

Sistem için süt sığırcılığıyla ilgili bilimsel ve teknik dokümanlardan özel bir bilgi tabanı oluşturulmuştur.

Bilgi tabanı aşağıdaki konu kategorilerini içerir:

| Kategori | İçerik |
|----------|--------|
| 🦠 **Mastitis** | Mastitis, meme sağlığı ve hastalık yönetimi |
| 🥛 **Süt Kalitesi** | Somatik hücre sayısı ve süt kalite göstergeleri |
| 🌾 **Besleme** | Rasyon, kuru madde tüketimi ve dengeli besleme |
| ⚕️ **Metabolik Hastalıklar** | Geçiş dönemi, süt humması ve metabolik problemlere ilişkin kaynaklar |
| 🐄 **Buzağı Sağlığı** | Kolostrum ve buzağı besleme yönetimi |
| 🧬 **Üreme** | Süt sığırlarında üreme ve fertilite yönetimi |
| ❤️ **Hayvan Refahı** | Süt sığırlarında hayvan refahı |
| 🧼 **Süt Hijyeni** | Süt hijyeni ve iyi süt çiftçiliği uygulamaları |

Dokümanlar parçalar hâline getirilerek indekslenir ve sorguya en uygun bölümler geri getirilir.

---

## 🔎 Hibrit Bilgi Erişimi

RAG altyapısında iki farklı arama yaklaşımı birlikte kullanılmaktadır:

### FAISS

Anlamsal olarak soruya benzeyen doküman parçalarını bulmak için vektör tabanlı arama gerçekleştirir.

### BM25

Soruda geçen kelimeler ve terimler üzerinden klasik metin tabanlı arama gerçekleştirir.

Sistem bu iki yöntemin sonuçlarını birleştirerek en ilgili doküman parçalarını büyük dil modeline aktarır.

```text
Kullanıcı Sorusu
       │
       ▼
 Query Router
       │
 ┌─────┼─────────┬─────────┐
 ▼     ▼         ▼         ▼
SQL   RAG      HYBRID     CHAT
 │     │          │
 │   FAISS       PostgreSQL
 │     +          +
 │   BM25        RAG
 │     │          │
 └─────┴──────────┘
       │
       ▼
     Mistral
       │
       ▼
Kaynaklandırılmış Yanıt
```

---

## 🧩 Kullanılan Yapay Zekâ Teknolojileri

| Bileşen | Kullanılan Teknoloji |
|---------|----------------------|
| **LLM** | Mistral |
| **LLM Çalıştırma Ortamı** | Ollama |
| **Embedding Modeli** | BGE-M3 |
| **Vektör Veritabanı / İndeks** | FAISS |
| **Anahtar Kelime Araması** | BM25 |
| **RAG Framework** | LangChain |
| **Akış / Orkestrasyon** | LangGraph / LangChain |
| **Backend** | FastAPI |
| **Veritabanı** | PostgreSQL |
| **Mobil/Web Arayüzü** | React Native + Expo |
| **Programlama Dili** | Python / TypeScript |

---

## ⚙️ Sistem Gereksinimleri

| Bileşen | Gereksinim |
|---------|------------|
| **Python** | Python 3.12 veya uyumlu sürüm |
| **Node.js** | Node.js 20 veya uyumlu sürüm |
| **Veritabanı** | PostgreSQL |
| **Yerel LLM Servisi** | Ollama |
| **LLM Modeli** | `mistral:latest` |
| **Embedding Modeli** | `bge-m3:latest` |
| **Frontend** | Expo / React Native |
| **Backend Portu** | `8001` |
| **Frontend Web Portu** | Genellikle `8081` |

---

# 🛠️ Geliştirici Kurulumu

## 1. Projeyi Klonlama

```bash
git clone https://github.com/sercelik17/Ciftlik-Asistani.git
cd Ciftlik-Asistani
```

Proje geliştirme branch'i:

```bash
git checkout thesis-rag
```

---

## 2. Ollama Kurulumu

Sistemde Ollama kurulu olmalıdır.

Gerekli modeller:

```bash
ollama pull mistral
ollama pull bge-m3
```

Kurulu modelleri kontrol etmek için:

```bash
ollama list
```

---

## 3. Backend Ortamını Hazırlama

```bash
cd Backend
```

Sanal ortam oluşturun:

### Windows

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

Bağımlılıkları yükleyin:

```bash
pip install -r requirements.txt
```

---

## 4. PostgreSQL Veritabanını Başlatma

Proje PostgreSQL veritabanını kullanmaktadır.

Docker yapılandırması mevcutsa:

```bash
docker compose up -d
```

Veritabanı bağlantı bilgileri `Backend/.env` dosyasında yapılandırılır.

> `.env` dosyası kullanıcı adı, parola ve bağlantı bilgileri içerebileceğinden GitHub'a yüklenmemelidir.

---

## 5. Ortam Değişkenleri

`Backend/.env` içerisinde RAG ve veritabanı yapılandırmaları tanımlanır.

Örnek RAG yapılandırması:

```env
RAG_KNOWLEDGE_BASE=knowledge_base
RAG_INDEX_DIR=rag_index

RAG_EMBED_MODEL=bge-m3
RAG_LLM=mistral
RAG_ROUTER_LLM=mistral

RAG_CHUNK_SIZE=900
RAG_CHUNK_OVERLAP=150

RAG_VECTOR_TOP_K=8
RAG_BM25_TOP_K=8
RAG_FINAL_TOP_K=5

RAG_DENSE_WEIGHT=0.60
RAG_SPARSE_WEIGHT=0.40
```

PostgreSQL için ayrıca aşağıdaki değişkenler yapılandırılmalıdır:

```env
DB_HOST=localhost
DB_PORT=5433
DB_NAME=...
DB_USER=...
DB_PASSWORD=...
```

---

## 6. RAG İndeksini Oluşturma

Bilgi tabanı indeksleri mevcut değilse aşağıdaki komut kullanılabilir:

```bash
python -m thesis_rag.build_index
```

Bu işlem bilgi tabanındaki dokümanları işler ve FAISS/BM25 tabanlı RAG indekslerini oluşturur.

---

## 7. Backend'i Başlatma

Backend klasöründe:

```bash
python -m uvicorn api:app --host 127.0.0.1 --port 8001
```

Başarılı olduğunda:

```text
Uvicorn running on http://127.0.0.1:8001
```

mesajı görüntülenir.

### Swagger API Arayüzü

```text
http://127.0.0.1:8001/docs
```

### RAG Sağlık Kontrolü

```text
http://127.0.0.1:8001/query/thesis/health
```

Beklenen yanıt:

```json
{
  "status": "ok",
  "module": "LangChain + BM25 + FAISS Hybrid RAG"
}
```

---

## 8. Frontend'i Başlatma

Yeni bir terminal açın:

```bash
cd mobileapp
npm install
npm run web
```

Web arayüzü genellikle:

```text
http://localhost:8081
```

adresinde açılır.

Mobil cihaz üzerinden test için:

```bash
npx expo start
```

komutu kullanılabilir.

---

# 🏗️ Proje Yapısı

```text
Ciftlik-Asistani/
│
├── Backend/
│   ├── api.py
│   │
│   ├── thesis_rag/
│   │   ├── api_router.py
│   │   ├── query_router.py
│   │   ├── thesis_service.py
│   │   ├── rag_chain.py
│   │   ├── hybrid_retriever.py
│   │   ├── farm_adapter.py
│   │   ├── index_builder.py
│   │   ├── build_index.py
│   │   └── settings.py
│   │
│   ├── knowledge_base/
│   │   ├── 01_mastitis/
│   │   ├── 02_sut_kalitesi/
│   │   ├── 03_besleme/
│   │   ├── 04_metabolik_hastaliklar/
│   │   ├── 05_buzagi_sagligi/
│   │   ├── 06_ureme/
│   │   ├── 07_hayvan_refahi/
│   │   └── 08_sut_hijyeni/
│   │
│   ├── rag_index/
│   ├── requirements.txt
│   └── .env
│
├── mobileapp/
│   ├── app/
│   │   ├── (tabs)/
│   │   │   ├── chat.tsx
│   │   │   ├── herd.tsx
│   │   │   ├── index.tsx
│   │   │   └── stats.tsx
│   │   ├── login.tsx
│   │   ├── signup.tsx
│   │   └── _layout.tsx
│   │
│   ├── assets/
│   ├── package.json
│   └── tsconfig.json
│
└── README.md
```

---

# 🔌 API Endpoint'leri

Tez kapsamında geliştirilen temel yapay zekâ endpoint'i:

| Endpoint | Metod | Açıklama |
|----------|-------|----------|
| `/` | GET | Backend servis durumunu kontrol eder |
| `/query/thesis/health` | GET | RAG modülünün çalışıp çalışmadığını kontrol eder |
| `/query/thesis/` | POST | SQL / RAG / HYBRID / CHAT yönlendirmeli Çiftlik Asistanı sorgusu |
| `/cows` | GET | Çiftliğe ait inekleri getirir |
| `/alarms` | GET | Alarm kayıtlarını getirir |
| `/summaries` | GET | Çiftlik özet verilerini getirir |

`/query/thesis/` endpoint'i aşağıdaki örnekte olduğu gibi bir soru alır:

```json
{
  "question": "Somatik hücre sayısının artması süt kalitesini nasıl etkiler?"
}
```

Örnek cevap yapısı:

```json
{
  "route": "RAG",
  "answer": "Somatik hücre sayısının artması süt kalitesini azaltır [K1].",
  "sources": [
    {
      "id": "K1",
      "title": "Darbaz_Ergene_2015_Somatik_Hucre_Sayisi.pdf",
      "page": 2
    }
  ]
}
```

> Korumalı endpoint'lerde kullanıcı kimlik doğrulaması için yetkilendirme bilgisi gereklidir.

---

# 🔐 Veri Güvenliği

Çiftlik Asistanı'nda kullanıcıların kendi çiftlik verilerine erişebilmesi için kullanıcı ve çiftlik ilişkisi kullanılmaktadır.

Sorgular kullanıcının bağlı olduğu çiftliğin `ciftlik_id` bilgisine göre işlenir.

`.env` içerisinde bulunan:

- Veritabanı kullanıcı adı
- Veritabanı parolası
- Bağlantı bilgileri
- Gizli uygulama değerleri

GitHub'a yüklenmemelidir.

---

# ❓ Sık Karşılaşılan Sorunlar

| Sorun | Çözüm |
|-------|-------|
| **Frontend backend'e bağlanmıyor** | Backend'in `127.0.0.1:8001` üzerinde çalıştığını kontrol edin |
| **RAG yanıtı oluşturulamıyor** | Ollama servisinin ve `mistral` modelinin çalıştığını kontrol edin |
| **Embedding hatası oluşuyor** | `bge-m3` modelinin Ollama içerisinde kurulu olduğunu kontrol edin |
| **RAG indeksi bulunamadı** | `python -m thesis_rag.build_index` komutunu çalıştırın |
| **Veritabanı bağlantı hatası** | PostgreSQL container'ını ve `.env` veritabanı ayarlarını kontrol edin |
| **401 Unauthorized** | Kullanıcının oturum açtığını ve token bilgisinin geçerli olduğunu kontrol edin |
| **500 Internal Server Error** | Backend terminalindeki Python traceback çıktısını kontrol edin |
| **Mikrofon çalışmıyor** | Uygulama için mikrofon izninin etkin olduğundan emin olun |
| **Ollama bellek hatası** | Kullanılmayan modelleri `ollama stop` ile kapatın ve sistem belleğini kontrol edin |

---

# 🎓 Tez Kapsamı

Bu proje aşağıdaki yüksek lisans tez çalışması kapsamında geliştirilmiştir:

**Hayvancılık Sektöründe Yapay Zekâ Destekli Sohbet Robotu Geliştirme: LangChain ve RAG (Retrieval-Augmented Generation) Teknolojileriyle Uygulamalı Bir Model**

Çalışmanın temel amacı; yapılandırılmış çiftlik verileri ile bilimsel ve veterinerlik dokümanlarından elde edilen yapılandırılmamış bilgileri aynı sohbet sistemi içerisinde birleştirerek çiftçilere yönelik kaynak temelli bir karar destek asistanı geliştirmektir.
