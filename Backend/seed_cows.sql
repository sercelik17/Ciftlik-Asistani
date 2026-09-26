INSERT INTO inekler
(kupe_no, ciftlik_id, isim, irk, dogum_tarihi, laktasyon_no)
VALUES
('TR0001', 1, 'Serap', 'Holstein', '2021-03-12', 2),
('TR0002', 1, 'Beyza', 'Holstein', '2020-07-21', 3),
('TR0003', 1, 'Boncuk', 'Simental', '2022-01-14', 1),
('TR0004', 1, 'Papatya', 'Holstein', '2019-11-02', 4),
('TR0005', 1, 'Lale', 'Simental', '2021-08-19', 2)
ON CONFLICT (kupe_no) DO NOTHING;