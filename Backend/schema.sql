CREATE TABLE IF NOT EXISTS ciftlikler (
    id SERIAL PRIMARY KEY,
    ciftlik_adi VARCHAR(200) NOT NULL,
    olusturulma_tarihi TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS kullanicilar (
    id SERIAL PRIMARY KEY,
    ciftlik_id INTEGER NOT NULL REFERENCES ciftlikler(id) ON DELETE CASCADE,
    ad_soyad VARCHAR(200) NOT NULL,
    eposta VARCHAR(255) NOT NULL UNIQUE,
    sifre_hash TEXT NOT NULL,
    telefon VARCHAR(50),
    olusturulma_tarihi TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS inekler (
    kupe_no VARCHAR(50) PRIMARY KEY,
    ciftlik_id INTEGER REFERENCES ciftlikler(id) ON DELETE CASCADE,
    isim VARCHAR(100) NOT NULL,
    irk VARCHAR(100),
    dogum_tarihi DATE,
    laktasyon_no INTEGER,
    olusturulma_tarihi TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sagim_kayitlari (
    id BIGINT PRIMARY KEY,
    ciftlik_id INTEGER REFERENCES ciftlikler(id) ON DELETE CASCADE,
    kupe_no VARCHAR(50) NOT NULL REFERENCES inekler(kupe_no) ON DELETE CASCADE,
    tarih DATE NOT NULL,
    sagim_zamani CHAR(1) NOT NULL CHECK (sagim_zamani IN ('m', 'e')),
    sut_miktari NUMERIC(10,2) NOT NULL CHECK (sut_miktari >= 0),
    olusturulma_tarihi TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS alarmlar (
    id SERIAL PRIMARY KEY,
    ciftlik_id INTEGER REFERENCES ciftlikler(id) ON DELETE CASCADE,
    kupe_no VARCHAR(50) NOT NULL REFERENCES inekler(kupe_no) ON DELETE CASCADE,
    tarih DATE NOT NULL,
    sagim_zamani CHAR(1) NOT NULL CHECK (sagim_zamani IN ('m', 'e')),
    eski_ortalama NUMERIC(10,2) NOT NULL,
    son_verim NUMERIC(10,2) NOT NULL,
    dusus_yuzdesi NUMERIC(10,2) NOT NULL,
    mesaj TEXT,
    okundu BOOLEAN DEFAULT FALSE,
    olusturulma_tarihi TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (kupe_no, tarih, sagim_zamani)
);

CREATE TABLE IF NOT EXISTS gunluk_ozetler (
    id SERIAL PRIMARY KEY,
    ciftlik_id INTEGER REFERENCES ciftlikler(id) ON DELETE CASCADE,
    tarih DATE NOT NULL,
    dunku_toplam_sut NUMERIC(12,2),
    bugunku_toplam_sut NUMERIC(12,2),
    en_verimli_inek_kupe_no VARCHAR(50) REFERENCES inekler(kupe_no) ON DELETE SET NULL,
    mesaj TEXT,
    olusturulma_tarihi TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (ciftlik_id, tarih)
);

CREATE TABLE IF NOT EXISTS cihaz_tokenlari (
    id SERIAL PRIMARY KEY,
    token TEXT NOT NULL UNIQUE,
    olusturulma_tarihi TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_sagim_kupe_tarih
ON sagim_kayitlari (kupe_no, tarih);

CREATE INDEX IF NOT EXISTS idx_sagim_ciftlik_tarih
ON sagim_kayitlari (ciftlik_id, tarih);

CREATE INDEX IF NOT EXISTS idx_alarmlar_okundu
ON alarmlar (okundu);