# Tez Word teslimi

Dosya: `Celikkaya_YL_Tez_Savunma_2026-10-27.docx`

Kaynak, 24 Ekim 2026 PDF tezinin `pdf2docx` dönüşümüdür. Sayılar, RAG terimleri, Tablo 4.8 / Ek SQL-HYBRID hücreleri ve bölüm başlık stilleri `Backend/thesis_eval/finalize_thesis_docx.py` ile hizalanmıştır.

## Word’de sizin yapmanız gerekenler

1. İçindekiler, şekil ve tablo dizinlerini **Ctrl+A → F9** ile yenileyin.
2. Üniversite şablonunun kapak/ön sayfa stillerini (üst bilgi, sayfa numarası, kenar boşluğu) kontrol edin.
3. Ekran görüntülerindeki işletim sistemi filigranı, nitel hata örneği olarak bırakıldı; değiştirmek isterseniz yeni ekran görüntüsü alın.

## Metindeki bağlayıcı sayılar

| Ölçüt | Değer |
|--------|--------|
| SQL sayısal / varlık tutarlılığı | **17/24 (0,708)** |
| HYBRID uçtan uca (kaynak seçimi) | **11/16 (0,688)** |
| SQL çalıştırılabilirliği | 24/24 (model Text-to-SQL EA değil) |

## Belge dışı kalanlar

Bağımsız ikinci insan değerlendirici (κ), modelin yazdığı SQL execution accuracy ve benzerlik raporundaki literatür tekrarları bu dosyada kapanmış sayılmaz; raporda sınırlılık olarak durur.
