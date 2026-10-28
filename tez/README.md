# Tez Word teslimi

Dosya: `Celikkaya_YL_Tez_Savunma_2026-10-27.docx`

Kaynak, 24 Ekim 2026 PDF tezinin `pdf2docx` dönüşümüdür. Sayılar, RAG terimleri, Tablo 4.8 / Ek SQL-HYBRID hücreleri ve bölüm başlık stilleri `Backend/thesis_eval/finalize_thesis_docx.py` ile hizalanmıştır.

## Sayfa düzeni

MAKÜ Fen Bilimleri Enstitüsü kılavuzuna göre ayarlandı: sol 4 cm, sağ 2 cm, üst ve alt 2,5 cm. Kapaklar numarasız. Etik beyandan Abstract’a kadar küçük Romen, Giriş’ten itibaren Arap rakamları, alt orta. İçindekiler, çizelge ve şekil dizinindeki sayılar bu düzene göre yazıldı.

## Kör puan

`Kor_Puanlama_15_On_Degerlendirme.pdf` doldurulmuş veteriner hekim kör puanlama formudur. Tezde Tablo 4.10’dur: uygunluk 12/15 (0,80), bağlılık 11/15 (0,73).

Tablo 4.9 kaynak parçası okunarak yapılan kodlamadır (uygunluk 12/15, bağlılık 7/15) ve veteriner formu değildir. İki tablo arasında uygunluk κ = 1,00, bağlılık κ = 0,55.

## Sohbet yanıtı

Held-out üretim sayıları 160 token / 2048 bağlam koşusuna aittir. Sohbet yolunda varsayılan üretim 400 token, bağlam 4096’dır; kesilmiş İngilizce kuyruk ve kaynakça parçası yanıta bırakılmaz. Bu ortamda Ollama olmadığı için 15 soru yeniden üretilmedi. Yerelde `ollama pull mistral` ve `bge-m3` sonrası backend’i yeniden başlatın.

## Metindeki bağlayıcı sayılar

| Ölçüt | Değer |
|--------|--------|
| SQL sayısal / varlık tutarlılığı | **17/24 (0,708)** |
| HYBRID uçtan uca (kaynak seçimi) | **11/16 (0,688)** |
| SQL çalıştırılabilirliği | 24/24 (model Text-to-SQL EA değil) |

## Belgede kapatılanlar

- SQL 17/24 (0,708) ve HYBRID 11/16 (0,688) bütün metinde aynı sayıdır.
- PDF dönüşümünün gövdeye karıştırdığı sayfa numaraları silindi; bölünen cümleler birleştirildi.
- İçindekiler, tablo ve şekil listesi başlıklardan yeniden yazıldı.
- §5.1’deki tekrar paragrafı çıkarıldı; literatür sonunda boşluk paragrafı eklendi.
- §3.2’ye prototip ölçeği (1 çiftlik, 5 inek, 70 sağım, 1 alarm) yazıldı.
- Şekil 3.3 ve Şekil 4.3’teki Windows etkinleştirme filigranı görüntüden temizlendi.
- 33 RAG yanıtı için ikinci kodlama ile otomatik 0–2 kuralının Cohen κ değeri 0,158’dir (`Backend/evaluation_output/ikinci_kodlama_kappa.json`).

## Bilinçli olarak açık kalanlar

Veteriner hekim formu 15 maddeyi kapsar; 33 RAG yanıtının tamamı bu formda yoktur. 33 soruluk otomatik kural κ değeri (0,158) uzman puanı değildir. Araştırmacının tek geçiş puanlarının madde kâğıdı arşivde yoktur. LLM-only koşulunun içerik puanı bu κ’ya girmez; o koşulun atıf metrikleri bağlam olmadığı için yapısal olarak sıfırdır. Modelin serbest Text-to-SQL execution accuracy’si, şablon SQL’den ayrı bir tam deney olarak durmaz: 22 soru şablon, iki soru yedek yoldur ve F-SQL015 sözdizimi hatasıdır.
