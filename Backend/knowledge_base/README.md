# Bilgi Tabanı

Bu klasör, tez RAG sisteminin **kaynak gösterilebilir** süt sığırcılığı derlemesini içerir.
Desteklenen formatlar: `.pdf`, `.txt`, `.md`.

## Belge seçim ölçütleri

1. Süt sığırcılığına doğrudan ilgili olma
2. FAO, WOAH, Codex, üniversite yayını veya hakemli makale olma
3. Sekiz tematik kategoriden en az birini kapsama
4. Kaynak kimliğinin bibliyografik olarak izlenebilir olması
5. Sistemin veteriner tanısı koymaması; belgeler yönetim ve bilimsel arka plan içindir

Tam envanter: `corpus_manifest.json`

## Tematik kategoriler

- `01_mastitis/`
- `02_sut_kalitesi/`
- `03_besleme/`
- `04_metabolik_hastaliklar/`
- `05_buzagi_sagligi/`
- `06_ureme/`
- `07_hayvan_refahi/`
- `08_sut_hijyeni/`

## Çiftlik verisinin niteliği

PostgreSQL içindeki inek, sağım ve alarm kayıtları **ticari işletme verisi değildir**.
Bu kayıtlar prototip ve deneysel değerlendirme için üretilmiş **sentetik örnek veridir**.
