-- Daha önce aynı test verileri eklenmişse temizle
DELETE FROM sagim_kayitlari
WHERE kupe_no IN ('TR0001', 'TR0002', 'TR0003', 'TR0004', 'TR0005')
  AND tarih BETWEEN DATE '2026-08-30' AND DATE '2026-09-05';

WITH cows(kupe_no, sabah_ortalama, aksam_ortalama) AS (
    VALUES
        ('TR0001', 15.5::numeric, 12.8::numeric), -- Serap
        ('TR0002', 14.8::numeric, 12.2::numeric), -- Beyza
        ('TR0003', 13.7::numeric, 11.5::numeric), -- Boncuk
        ('TR0004', 16.2::numeric, 13.4::numeric), -- Papatya
        ('TR0005', 14.1::numeric, 11.8::numeric)  -- Lale
),
days AS (
    SELECT generate_series(
        DATE '2026-08-30',
        DATE '2026-09-05',
        INTERVAL '1 day'
    )::date AS tarih
),
times(sagim_zamani) AS (
    VALUES ('m'::char(1)), ('e'::char(1))
),
veriler AS (
    SELECT
        c.kupe_no,
        d.tarih,
        t.sagim_zamani,

        CASE
            -- Serap'ın son akşam sağımında bilinçli anomali
            WHEN c.kupe_no = 'TR0001'
             AND d.tarih = DATE '2026-09-05'
             AND t.sagim_zamani = 'e'
            THEN 7.8::numeric

            WHEN t.sagim_zamani = 'm'
            THEN
                c.sabah_ortalama +
                CASE ((d.tarih - DATE '2026-08-30') % 4)
                    WHEN 0 THEN -0.3
                    WHEN 1 THEN  0.2
                    WHEN 2 THEN  0.4
                    ELSE -0.1
                END

            ELSE
                c.aksam_ortalama +
                CASE ((d.tarih - DATE '2026-08-30') % 4)
                    WHEN 0 THEN -0.2
                    WHEN 1 THEN  0.3
                    WHEN 2 THEN  0.1
                    ELSE -0.1
                END
        END AS sut_miktari

    FROM cows c
    CROSS JOIN days d
    CROSS JOIN times t
),
numarali AS (
    SELECT
        ROW_NUMBER() OVER (
            ORDER BY
                tarih,
                kupe_no,
                CASE WHEN sagim_zamani = 'm' THEN 1 ELSE 2 END
        ) AS rn,
        *
    FROM veriler
),
max_id AS (
    SELECT COALESCE(MAX(id), 0) AS mevcut_max
    FROM sagim_kayitlari
)
INSERT INTO sagim_kayitlari
(id, ciftlik_id, kupe_no, tarih, sagim_zamani, sut_miktari)
SELECT
    max_id.mevcut_max + numarali.rn,
    1,
    kupe_no,
    tarih,
    sagim_zamani,
    ROUND(sut_miktari, 2)
FROM numarali
CROSS JOIN max_id;