# 🐄 Süt Sihirbazı - Kullanım Kılavuzu

> **Süt Sihirbazı**, süt çiftçiliğiyle uğraşan çiftçiler için geliştirilmiş yapay zekâ destekli bir mobil asistan uygulamasıdır. İnek sağlığı, çiftlik verimi, yemleme, süt üretimi gibi konularda doğal dilde sorular sorarak anında yanıt alabilirsiniz.

---

## 📱 Uygulama Özellikleri

| Özellik | Açıklama |
|---------|----------|
| 💬 **Sohbet (Chat)** | Metin yazarak çiftlik ve hayvancılık hakkında soru sorun |
| 🎤 **Sesli Soru Sorma** | Mikrofon butonuna basıp sesinizle soru sorun, uygulama sizi dinler |
| 🔊 **Sesli Yanıt (TTS)** | Botun verdiği cevapları hoparlör simgesine dokunarak sesli dinleyin |
| 📊 **Veri Sorgulama** | SQL veritabanındaki güncel çiftlik verilerini sorgulayın |
| 📝 **Markdown Desteği** | Yanıtlar tablolar, kalın yazı ve listelerle zengin biçimde sunulur |
| ⏱️ **Yanıt Süresi** | Her cevabın sonunda yanıt süresi gösterilir |
| 🔄 **Adım Göstergesi** | Sorgu işlenirken hangi aşamada olduğunuz canlı olarak gösterilir |

---

## 🚀 İlk Başlangıç

### Uygulamayı Açma
Uygulamayı açtığınızda sizi yeşil temalı bir ahır ikonu ve aşağıdaki karşılama mesajı karşılar:

> *"Merhaba, Çiftçi Dostum! Bugün çiftliğin verimi veya ineklerin sağlığı hakkında ne öğrenmek istersin?"*

### Ekran Düzeni

<img width="313" height="587" alt="image" src="https://github.com/user-attachments/assets/cb6e2e05-bbad-4737-ad98-f63a6555be88" />


## 📖 Adım Adım Kullanım

### 1️⃣ Yazılı Soru Sorma

1. Alt kısımdaki **"Sihirbaza sorun..."** yazan alana dokunun.
2. Sormak istediğiniz soruyu yazın (örn: *"Bu ayki süt verimi ne kadar?"*).
3. Klavyenizin yanındaki **ok (➤) butonuna** basın.
4. Bot düşünürken ekranda bir **adım göstergesi** (Step Indicator) görürsünüz.
5. Yanıt geldiğinde mesaj baloncuğu içinde görüntülenir.

### 2️⃣ Sesli Soru Sorma

1. Giriş alanının sağ tarafındaki **mikrofon (🎤) butonuna** dokunun.
2. Mikrofon butonu **kırmızıya** döner → Artık kayıt yapılıyor demektir.
3. Sorunuzu net bir şekilde söyleyin.
4. Kaydı bitirmek için tekrar **mikrofon (durdur ⏹) butonuna** dokunun.
5. Uygulama sesinizi metne çevirir ve ekranda gösterir.
6. Ardından sorunuz işlenir ve yanıt gelir.

> 💡 **İpucu:** Sesli soru sorma özelliği ilk kez kullanıldığında mikrofon izni istenir. "İzin Ver" seçeneğini onaylayın.

### 3️⃣ Yanıtları Sesli Dinleme (TTS)

1. Botun verdiği herhangi bir yanıtın sağ üstündeki **hoparlör (🔊) simgesine** dokunun.
2. Yanıt sesli olarak okunmaya başlar; ikon değişerek okunduğunu belirtir.
3. Durdurmak için **tekrar aynı simgeye** dokunun.

### 4️⃣ Tablo ve Zengin İçerik Okuma

Bot yanıtları **Markdown** formatında gelir. Tablolar, listeler ve başlıklar otomatik olarak biçimlendirilir:

- **Tablolar:** Yatay kaydırılabilir kartlar halinde gösterilir.
- **Kalın yazılar:** Önemli bilgiler vurgulanır.
- **Listeler:** Maddeler halinde sıralanır.

---

## 💡 Örnek Sorular

Aşağıdaki soruları deneyerek uygulamanın gücünü keşfedin:

| Kategori | Örnek Sorular |
|----------|---------------|
| 🥛 **Süt Verimi** | *"Bu ay toplam süt verimi ne kadar?"* |
| 🐄 **Hayvan Sağlığı** | *"Küpe no 1042 olan ineğin durumu nedir?"* |
| 📈 **Raporlama** | *"Son bir haftadaki süt üretim grafiği nasıl?"* |
| 📊 **Genel Analiz** | *"En çok süt veren 5 ineği listele."* |

---

## ⚙️ Sistem Gereksinimleri

| Bileşen | Gereksinim |
|---------|------------|
| **Mobil Uygulama** | Expo Go veya Development Build (Android / iOS) |
| **Backend** | Python 3.x, FastAPI |
| **Veritabanı** | SQL Veritabanı + CSV Veri Dosyaları |
| **Ağ** | Backend sunucusuna erişim (varsayılan: `localhost:8000`) |
| **İzinler** | Mikrofon izni (sesli soru sorma için) |

---

## 🛠️ Geliştirici Kurulumu

### Backend Başlatma

```bash
cd Backend
pip install -r requirements.txt
docker-compose up --build
```

> Backend `http://localhost:8000` adresinde çalışır.

### Mobil Uygulamayı Başlatma

```bash
cd mobileapp
npm install
npx expo start
```

Açılan QR kodu **Expo Go** uygulamasıyla tarayarak cihazınızda test edebilirsiniz.

### Ortam Değişkenleri

`Backend/.env` dosyasında gerekli API anahtarlarını ve veritabanı ayarlarını yapılandırın.

---

## 🏗️ Proje Yapısı

```
Sut_Sihirbazi_Bitirme_Projesi/
├── Backend/
│   ├── api.py              # FastAPI ana uygulama
│   ├── sql_rag.py          # SQL RAG sorgu motoru
│   ├── csv_rag.py          # CSV RAG analiz motoru
│   ├── requirements.txt    # Python bağımlılıkları
│   ├── Dockerfile          # Docker yapılandırması
│   └── docker-compose.yml  # Docker Compose
├── mobileapp/
│   ├── app/
│   │   ├── index.tsx       # Ana giriş ekranı
│   │   └── _layout.tsx     # Uygulama düzeni
│   ├── components/
│   │   ├── Chat.tsx        # Sohbet bileşeni
│   │   └── StepIndicator.tsx # Adım göstergesi
│   ├── hooks/              # Özel React hook'ları
│   └── assets/             # Görseller ve ikonlar
└── README.md
```

---

## 🎨 Tema Renkleri

Uygulama, doğa ve çiftçilik temalı yeşil tonlarla tasarlanmıştır:

| Renk | Kod | Kullanım |
|------|-----|----------|
| 🟢 Ana Yeşil | `#1B5E20` | Başlıklar, marka rengi |
| 🌿 Açık Yeşil | `#2E7D32` | İkonlar, vurgular |
| 🍃 Arka Plan | `#F1F8E9` | Yumuşak yüzeyler |
| 🫧 Kullanıcı Balonu | `#E0F2F1` | Kullanıcı mesajları |
| ⚪ Bot Balonu | `#FFFFFF` | Bot mesajları |

---

## 🔌 API Endpoint'leri

| Endpoint | Metod | Açıklama |
|----------|-------|----------|
| `/` | GET | API durum kontrolü |
| `/query/sql/` | POST | SQL veritabanı sorgusu |
| `/query/sql/stream` | POST | SQL sorgusu (canlı akış) |
| `/query/csv/` | POST | CSV veri analizi |
| `/query/csv/stream` | POST | CSV analizi (canlı akış) |
| `/transcribe` | POST | Ses → Metin dönüştürme |
| `/tts` | GET | Metin → Ses dönüştürme |

---

## ❓ Sık Karşılaşılan Sorunlar

| Sorun | Çözüm |
|-------|-------|
| **Mikrofon çalışmıyor** | Cihaz ayarlarından uygulamaya mikrofon izni verin |
| **Bağlantı hatası** | Backend sunucusunun çalıştığından emin olun |
| **Sesli yanıt çalmıyor** | Cihazınızın sesinin açık olduğunu kontrol edin |
| **Yanıt gelmiyor** | İnternet bağlantınızı ve API sunucusunu kontrol edin |
