# -*- coding: utf-8 -*-
from copy import deepcopy
from pathlib import Path

from docx import Document
from docx.oxml import OxmlElement
from docx.text.paragraph import Paragraph

SRC = Path(r"c:\Users\Serenay\Downloads\hayvancılık güncel (1).docx")
DST = Path(r"c:\Users\Serenay\Downloads\hayvancılık güncel_revize.docx")


def set_para_text(paragraph, text: str) -> None:
    if paragraph.runs:
        paragraph.runs[0].text = text
        for run in paragraph.runs[1:]:
            run.text = ""
    else:
        paragraph.add_run(text)


def insert_after(paragraph, text: str, style: str | None = None) -> Paragraph:
    new_p = OxmlElement("w:p")
    paragraph._p.addnext(new_p)
    new_para = Paragraph(new_p, paragraph._parent)
    if style:
        new_para.style = style
    new_para.add_run(text)
    return new_para


def apply_phrase_map(text: str) -> str:
    pairs = [
        (
            "Transformer tabanlı öğrenme yönetim sistemleri (LLM'ler)",
            "Transformer tabanlı büyük dil modelleri (LLM'ler)",
        ),
        (
            "Transformer tabanlı öğrenme yönetim sistemleri",
            "Transformer tabanlı büyük dil modelleri",
        ),
        (
            "artırılmış üretim yoluyla bilgi alma (AGR)",
            "geri getirme destekli üretim (RAG)",
        ),
        (
            "artırılmış üretim yoluyla geri alma (AGR)",
            "geri getirme destekli üretim (RAG)",
        ),
        (
            "artırılmış üretim ve geri alma (AGR)",
            "geri getirme destekli üretim (RAG)",
        ),
        (
            "Artırılmış Veri Alımıyla Üretim (AGR)",
            "Geri Getirme Destekli Üretim (RAG)",
        ),
        (
            "Artırılmış bilgi edinme yoluyla üretim (AGR)",
            "Geri Getirme Destekli Üretim (RAG)",
        ),
        (
            "RAG (İlişkisel Toplu Veritabanı)",
            "RAG (Geri Getirme Destekli Üretim)",
        ),
        (
            "RAG (Yanıt Edinimi ve Üretken Yaklaşım)",
            "RAG (Geri Getirme Destekli Üretim)",
        ),
        (
            "RAG (Alınımı Artırılmış Üretim)",
            "RAG (Geri Getirme Destekli Üretim)",
        ),
        (
            "Bilgi Alma-Genişletilmiş Üretim (RAG)",
            "Geri Getirme Destekli Üretim (RAG)",
        ),
        (
            "Bilgi Alma Çerçevesi (RAG) tabanlı bir Bilgi Alma çerçevesinde",
            "RAG çerçevesinde",
        ),
        ("Geri Alma Destekli Üretim", "Geri Getirme Destekli Üretim"),
        ("AGR altyapısı", "RAG altyapısı"),
        ("AGR genellikle", "RAG genellikle"),
        ("AGR, üretim", "RAG, üretim"),
        ("AGR sistemlerinde", "RAG sistemlerinde"),
        (" (AGR)", " (RAG)"),
        ("AGR", "RAG"),
        ("YAPAY ZEKA", "YAPAY ZEKÂ"),
        ("Yapay zeka", "Yapay zekâ"),
        ("yapay zeka", "yapay zekâ"),
        (
            "çiftliklerde toplanan şifrelenmiş verilerin",
            "çiftliklerde toplanan yapılandırılmış verilerin",
        ),
        (
            "Belirli alanlar veya sektörler hakkında daha detaylı bir analiz "
            "isterseniz lütfen bize bildirin. ",
            "",
        ),
        (
            "veritabanındaki ticari verilere",
            "veritabanındaki sentetik çiftlik kayıtlarına",
        ),
        (
            "tescilli yapılandırılmış verilerin",
            "sentetik yapılandırılmış çiftlik verilerinin",
        ),
        (
            "ticari verilerden elde edilen sayısal sonuçların",
            "sentetik çiftlik kayıtlarından elde edilen sayısal sonuçların",
        ),
        (
            "PostgreSQL veritabanından şirket özel verilerini",
            "PostgreSQL veritabanından sentetik çiftlik verilerini",
        ),
        (
            "şirket özelindeki nicel sonuçların",
            "sentetik kayıtlardaki nicel sonuçların",
        ),
    ]
    for old, new in pairs:
        text = text.replace(old, new)
    return text


PARAGRAPH_UPDATES = {
    "Sistemin ilk değerlendirmesi, 100 sorgudan oluşan bir test veri seti": (
        "Geliştirme (pilot) değerlendirmesi 100 sorgudan oluşmuştur: 50 RAG, "
        "30 SQL ve 20 HYBRID (CHAT bu kümede yoktur). Bu kümede yönlendirme "
        "doğruluğu %97 olarak ölçülmüştür; bu oran yanıt doğruluğu değildir. "
        "Nihai değerlendirme, daha önce kullanılmamış held-out küme üzerinde "
        "yapılmıştır (n = 89: 33 RAG, 24 SQL, 16 HYBRID, 16 CHAT). Held-out "
        "kümede kural tabanlı birinci aşama yönlendirici 89/89 doğru sınıflama "
        "ve Macro-F1 = 1,00 üretmiştir (%95 Wilson aralığı yaklaşık 0,96–1,00). "
        "Bu sonuç, sorunun doğru işleme kanalına gitmesini ölçer; üretilen "
        "cevabın bilimsel doğruluğunu ölçmez. Retrieval değerlendirmesinde "
        "(n = 33 RAG, K = 5) BM25 için P@5 = 0,35 ve MRR = 0,42; BGE-M3 tabanlı "
        "anlamsal erişim için P@5 = 0,90 ve MRR = 0,91; ağırlıklı RRF hibrit "
        "(0,60/0,40) için P@5 = 0,89 ve MRR = 0,88 bulunmuştur. Hibrit birleştirme "
        "bu sette salt anlamsal erişimin çok az gerisinde kalmıştır. RAG üretim "
        "deneyinde (n = 33) ortalama atıf doğruluğu 0,33, desteksiz iddia oranı "
        "ise 0,84 olarak hesaplanmıştır. Tanı/tedavi taleplerinde sistem reddetme "
        "davranışını korumuştur. Prototipteki inek ve sağım kayıtları ticari bir "
        "işletmeden alınmış gerçek veriler değil, SQL ve HYBRID iş akışlarını "
        "sınamak üzere üretilmiş sentetik örneklerdir. Bilgi tabanı 16 açık "
        "belgeden 1.833 metin parçası içermektedir."
    ),
    "Anahtar kelimeler: Yapay zeka, hayvancılık": (
        "Anahtar kelimeler: Yapay zekâ, hayvancılık, sohbet robotu, doğal dil "
        "işleme, büyük dil modeli, geri getirme destekli üretim (RAG), sorgu "
        "yönlendirme, hibrit erişim."
    ),
    "An initial evaluation of the system was conducted using a test dataset": (
        "A development (pilot) evaluation used 100 queries (50 RAG, 30 SQL, "
        "20 HYBRID; no CHAT). Routing accuracy on this set was 97% and does "
        "not measure answer correctness. The final evaluation used a held-out "
        "set of 89 queries (33 RAG, 24 SQL, 16 HYBRID, 16 CHAT). The "
        "first-stage rule-based router classified 89/89 queries correctly "
        "(Macro-F1 = 1.00; 95% Wilson interval approximately 0.96–1.00). "
        "On RAG retrieval (n = 33, K = 5), BM25 reached P@5 = 0.35 and "
        "MRR = 0.42; BGE-M3 dense retrieval reached P@5 = 0.90 and MRR = 0.91; "
        "weighted RRF hybrid (0.60/0.40) reached P@5 = 0.89 and MRR = 0.88. "
        "Hybrid fusion was slightly below dense-only retrieval on this set. "
        "In a generation experiment (n = 33), mean citation correctness was "
        "0.33 and the unsupported-claim rate was 0.84. Farm records in the "
        "prototype are synthetic, not commercial operational data. The "
        "knowledge base comprises 1,833 chunks from 16 public documents."
    ),
    "Sohbet robotunun kullanıcı sorgularını uygun işleme akışına yönlendirme": (
        "Yönlendirme iki kümede ayrı raporlanmıştır. Geliştirme (pilot) kümesi "
        "100 sorudan oluşur: 50 RAG, 30 SQL ve 20 HYBRID. Bu kümede CHAT yoktur "
        "ve elde edilen %97 oranı yalnızca geliştirme gözlemidir. Nihai değerlendirme "
        "held-out kümede yapılmıştır (n = 89): 33 RAG, 24 SQL, 16 HYBRID ve 16 CHAT. "
        "Böylece yöntem bölümünde tanımlanan dört sınıf, bulgularla uyumludur."
    ),
    "İlk değerlendirme, genel sorgu yönlendirme doğruluğunun %97 olduğunu": (
        "Pilot kümede genel yönlendirme doğruluğu %97 bulunmuştur (RAG %98, "
        "SQL %93,3, HYBRID %100). Held-out final kümede kural tabanlı birinci "
        "aşama yönlendirici 89/89 soruyu doğru kanala atamıştır (Macro-F1 = 1,00; "
        "sınıf dağılımı köşegen karmaşıklık matrisindedir). Yüksek yönlendirme "
        "başarısı, kuralların held-out soru diline ve prototip hayvan adlarına "
        "(Serap, Beyza vb.) iyi örtüşmesinden de kaynaklanır; bu bir genelleme "
        "sınırıdır. Her iki kümede de bu oranlar yanıt doğruluğu değildir."
    ),
    "Soru sayısına göre bu oranların analizi, 50 RAG sorusunun yaklaşık 49": (
        "Tablo 4.1 held-out kümeyi göstermektedir. Pilot kümedeki yaklaşık "
        "97/100 doğru yönlendirme, dondurulmuş sistemin nihai sonucu olarak "
        "yorumlanmamalıdır."
    ),
    "Elde edilen değerlerin analizi, SQL sorgularının en kısa ortalama": (
        "Tablo 4.2’deki süreler geliştirme sürecindeki ön ölçümlerdir ve nihai "
        "held-out uçtan uca gecikmeyi temsil etmez. Ayrı bir RAG üretim deneyinde "
        "(n = 33) ortalama süre 40,59 saniye (medyan 37,35; p95 56,93) bulunmuştur. "
        "SQL kanalı daha kısadır çünkü belge gömme ve hibrit yeniden sıralama "
        "adımlarını içermez."
    ),
    "Yapay zeka tabanlı tarım asistanının performansı, sorguların uygun": (
        "Yapay zekâ tabanlı tarım asistanının performansı, (i) sorgunun doğru "
        "kanala yönlendirilmesi, (ii) ilgili belgenin getirilmesi ve (iii) üretilen "
        "metnin kaynakla uyumu ayrı ayrı ele alınarak değerlendirilmiştir. Pilot "
        "kümede yönlendirme %97 iken held-out kümede 89/89’dur. Retrieval "
        "sonuçları Bölüm 4.4 ve 4.5’te verilmiştir."
    ),
    "RAG bileşeninin ilk değerlendirmesi, 50 farklı RAG sorgusunu içermiş": (
        "Pilot kümede 50 RAG sorusunun yönlendirme başarısı %98’dir. Held-out "
        "kümede 33 RAG sorusunun tamamı RAG kanalına gitmiştir. Bu değerler "
        "üretilen cümlelerin bilimsel doğruluğunu ölçmez."
    ),
    "Teknik dokümantasyonda son değerlendirme için Precision@K": (
        "Held-out RAG kümesinde (n = 33, K = 5) BM25 için P@5 = 0,3515, "
        "R@5 = 0,2727, MRR = 0,4242 ve nDCG@5 = 0,4242; BGE-M3 anlamsal erişim "
        "için P@5 = 0,8970, R@5 = 0,7121, MRR = 0,9091 ve nDCG@5 = 0,9191; "
        "ağırlıklı RRF hibrit (0,60 yoğun / 0,40 seyrek, k = 60) için P@5 = 0,8909, "
        "R@5 = 0,7121, MRR = 0,8813 ve nDCG@5 = 0,9011 elde edilmiştir. Anlamsal "
        "erişim sözcüksel erişimden belirgin üstündür. Hibrit, BM25’i iyileştirmekle "
        "birlikte bu sette salt anlamsal erişimin biraz gerisinde kalmıştır. "
        "Bu nedenle “hibrit her zaman daha iyidir” iddiası bu derleme için "
        "desteklenmemektedir."
    ),
    "Teknik dokümantasyonda önerilen deneysel değerlendirmeler, yalnızca büyük": (
        "Geliştirme setinde (n = 50) birleştirme ağırlığı 50/50, 60/40 ve 70/30 "
        "olarak karşılaştırılmıştır. 60/40 ve 70/30, 50/50’ye göre nDCG@5 açısından "
        "biraz daha yüksek veya eşdeğer bulunmuş (0,8414’e karşı 0,8395) ve final "
        "konfigürasyon 60/40 olarak dondurulmuştur. Yalnızca LLM (erişimsiz) ile "
        "RAG arasında tam bir ablasyon bu çalışmada nicel olarak tamamlanmamıştır."
    ),
    "Genel olarak, sonuçlar geliştirilen RAG bileşeninin bilimsel belgelerden": (
        "Genel olarak RAG bileşeni ilgili belgeleri yüksek isabetle getirebilmektedir. "
        "Buna karşılık üretim (generation) deneyi, getirilen kaynağın doğru cevaba "
        "otomatik dönüşmediğini göstermektedir. n = 33 RAG sorusunda ortalama atıf "
        "doğruluğu 0,33, atıf tamlığı 0,16, desteksiz iddia oranı 0,84 ve tercih "
        "edilen kaynağa isabet 0,68 bulunmuştur. Tanı reddi beklenen maddelerde "
        "sağlanmıştır. Bu zayıf üretim sayıları, sistemin karar destek aracı olarak "
        "kaynak göstermekle yükümlü olduğunu ve veteriner tanısının yerine "
        "geçemeyeceğini pekiştirir."
    ),
    "Geliştirilen sistemin ilk deneysel değerlendirmesi için 100 sorudan": (
        "Pilot küme (n = 100; CHAT yok) geliştirme içindir ve %97 yönlendirme "
        "oranı nihai sonuç değildir. Held-out kümede (n = 89; CHAT dâhil) "
        "yönlendirme 89/89, Macro-F1 = 1,00’dır. Retrieval’de anlamsal erişim "
        "P@5 = 0,90, hibrit P@5 = 0,89, BM25 P@5 = 0,35’tir. Üretim kalitesi "
        "düşüktür (atıf doğruluğu 0,33; desteksiz iddia 0,84). SQL altın "
        "sorgularının 23/24’ü beklenen sayıyı üretmiştir. Çiftlik verisi sentetiktir."
    ),
    "Bu aşamada, çalışmanın bazı sınırlamaları vardır. Performans değerlendirmesi": (
        "Çalışmanın sınırlılıkları şunlardır. Çiftlik kayıtları gerçek işletme "
        "verisi değil sentetik örneklerdir. Yönlendirme başarısı kural tabanlı "
        "birinci aşamaya dayanır ve hayvan özel adlarını içerir; bu durum "
        "genellemeyi sınırlar. Held-out kümede hibrit erişim, salt anlamsal "
        "erişimin biraz gerisindedir. RAG üretim kalitesi (atıf uyumu) düşüktür; "
        "belge getirme ile doğru cümle üretme aynı şey değildir. Sistemin "
        "ürettiği SQL’in uçtan uca execution accuracy’si ve uzman 0/1/2 "
        "puanlaması bu teslimde tamamlanmamıştır. Windows ortamında Torch/"
        "LangChain yükleme kısıtı nedeniyle üretim ölçümü Ollama HTTP yolu ile "
        "yapılmıştır. Sistem tanı ve antibiyotik kararı vermez."
    ),
}


NEW_AFTER = {
    '"Hayvancılıktan elde edilen yapılandırılmış verileri bilimsel bilgi kaynaklarıyla': (
        "Bu soru aşağıdaki alt sorularla somutlaştırılmıştır. RQ1: SQL, RAG, "
        "HYBRID ve CHAT sorguları ne ölçüde doğru yönlendirilmektedir? RQ2: "
        "FAISS + BM25 hibrit erişim, tekil BM25 ve tekil anlamsal erişime göre "
        "daha iyi midir? RQ3: RAG yanıtları getirilen kaynaklarla ne ölçüde "
        "uyumludur (atıf doğruluğu ve desteksiz iddia)? RQ4: SQL için altın "
        "standart sayısal sonuçlar nelerdir? RQ5: Yönlendirme başarısı yanıt "
        "doğruluğu ile karıştırılmadan nasıl raporlanır?",
        "Normal",
    ),
    "Bu veriler öncelikle SQL veya hibrit sorguları yanıtlamak için kullanıldı.": (
        "PostgreSQL içindeki inek, sağım ve alarm kayıtları ticari bir süt "
        "işletmesinden alınmış gerçek veriler değildir. Bu kayıtlar SQL ve "
        "HYBRID kanallarını sınamak üzere üretilmiş sentetik örnek verilerdir "
        "ve tez boyunca bu nitelikle anılır. Bilgi tabanı ise 16 açık bilimsel/"
        "rehber belgeden oluşur; belgeler 900 karakterlik parçalara (150 karakter "
        "örtüşme) bölünerek 1.833 metin parçası elde edilmiştir.",
        "Normal",
    ),
}


SECTION_45 = [
    (
        "4.5. Held-out Retrieval, Ağırlık Seçimi ve SQL Altın Sonuçları",
        "Heading 2",
    ),
    (
        "Final retrieval sonuçları held-out RAG sorularına (n = 33, K = 5) "
        "aittir. BM25 P@5 = 0,35 ve MRR = 0,42; BGE-M3 anlamsal erişim "
        "P@5 = 0,90 ve MRR = 0,91; ağırlıklı RRF hibrit (0,60/0,40) P@5 = 0,89 "
        "ve MRR = 0,88 bulunmuştur. Literatürde hibrit erişimin iki sinyali "
        "birleştirdiği savunulur; bu derlemede anlamsal model tek başına yeterli "
        "belgesel isabet üretmiş, BM25 aynı altın belgelerde daha düşük kalmıştır. "
        "Hibritin katkısı bu sette ortalama isabeti artırmamış, sözcüksel kaçırmaya "
        "karşı bir güvenlik ağı olarak yorumlanmalıdır.",
        "Normal",
    ),
    (
        "FAISS/BM25 ağırlığı geliştirme setinde (n = 50) seçilmiştir. 50/50 için "
        "nDCG@5 = 0,8395; 60/40 ve 70/30 için nDCG@5 = 0,8414’tür. 60/40 dondurulmuş "
        "ve held-out sette yeniden taranmamıştır. SQL için 24 altın sorgunun 23’ü "
        "beklenen hücre değerini üretmiştir. Başarısız örnek, altın sorgudaki "
        "sütun adının şema ile uyuşmamasından (ciftlikler.ad) kaynaklanmıştır. "
        "Bu tablo sistemin ürettiği SQL’in execution accuracy’si değildir.",
        "Normal",
    ),
    (
        "4.6. Üretim Kalitesi ve Güvenlik",
        "Heading 2",
    ),
    (
        "Otuz üç RAG sorusunda üretilen metinler kaynak listesiyle otomatik "
        "ölçülmüştür. Ortalama atıf doğruluğu 0,33, atıf tamlığı 0,16, desteksiz "
        "iddia oranı 0,84’tür. Tercih edilen kaynağa isabet 0,68’dir. Tanı veya "
        "antibiyotik talebi içeren maddelerde sistem reddetmiş ve veteriner hekime "
        "yönlendirmiştir. Bu sonuç, “doğru PDF’yi bulmak” ile “doğru cümleyi "
        "yazmak”ın ayrılması gerektiğini gösterir ve jüri değerlendirmesinde "
        "yönlendirme Macro-F1 değerinin cevap başarısı gibi sunulmamasını "
        "zorunlu kılar.",
        "Normal",
    ),
]


SURGICAL = [
    (
        "Performans değerlendirmesi, geliştirme aşamasında oluşturulan 100 soruluk bir test veri kümesi kullanılarak gerçekleştirilmiştir; bu küme 50 RAG sorgusu, 30 SQL sorgusu ve 20 hibrit sorgu içermektedir. İlk değerlendirmede elde edilen %97'lik genel başarı oranı, sistemin kullanıcı sorgularını amaçlanan işlem yollarına yönlendirme yeteneğini yansıtmaktadır; bu, üretilen yanıtların genel doğruluğunun bir ölçüsü olarak yorumlanmamalıdır. Benzer şekilde, ölçülen yanıt süreleri, geliştirme aşamasındaki sistem koşulları ve teknik altyapı altında elde edilen değerlere dayanmaktadır. Çalışmanın bir diğer sınırlaması ise, RAG bileşeninin nihai değerlendirmesi için bazı ölçümlerin henüz yapılmamış olmasıdır. Bu çalışmada, bilgi alma performansını değerlendirmek için kullanılan Precision@K, Recall@K ve MRR (Ortalama Karşılıklı Sıralama) gibi metrikler veya yanıt kalitesini değerlendirmek için kullanılan yanıt alaka düzeyi, sadakat, bağlam hassasiyeti ve bağlam hatırlama gibi metrikler için nihai sayısal sonuçlar elde edilmemiştir. Sonuç olarak, bu metrikler temel alınarak yapılan araştırma, RAG sisteminin bilgi alma başarısı veya kaynak materyale göre üretilen yanıtların güvenilirliği konusunda kesin bir performans puanı sağlamamaktadır.",
        "Performans değerlendirmesi iki aşamalıdır. Geliştirme (pilot) kümesi 100 sorudan oluşur (50 RAG, 30 SQL, 20 HYBRID; CHAT yoktur) ve bu küme üzerindeki yönlendirme oranı nihai başarı olarak sunulmaz. Nihai sonuçlar held-out kümedendir (n = 89; 33 RAG, 24 SQL, 16 HYBRID, 16 CHAT). Held-out yönlendirme doğruluğu 1,00 (89/89) ve Macro-F1 1,00’dır; bu, yanıt doğruluğu değil kanal seçimi başarısıdır. Retrieval için P@5, R@5, MRR ve nDCG@5 raporlanmıştır. RAG üretim kalitesi için atıf doğruluğu 0,33 ve desteksiz iddia oranı 0,84 ölçülmüştür. SQL altın sorgularının 23/24’ü beklenen sayısal sonucu vermiştir.",
    ),
]


def rewrite_matching_paragraphs(doc: Document) -> int:
    n = 0
    for para in doc.paragraphs:
        raw = para.text
        stripped = raw.strip()
        if not stripped:
            continue
        changed = False
        for old, new in SURGICAL:
            if old in raw:
                raw = raw.replace(old, new)
                changed = True
        for needle, replacement in PARAGRAPH_UPDATES.items():
            if stripped.startswith(needle):
                raw = replacement
                changed = True
                break
        if changed:
            set_para_text(para, raw)
            n += 1
    return n


def insert_blocks(doc: Document) -> int:
    n = 0
    for para in list(doc.paragraphs):
        raw = para.text.strip()
        for needle, (text, style) in NEW_AFTER.items():
            if raw.startswith(needle) or needle in raw[:60]:
                if raw.startswith(needle) or raw[1:].startswith(needle.lstrip('"')):
                    insert_after(para, text, style)
                    n += 1
    # section 4.5 after last 4.4 closing paragraph
    anchor = None
    for para in doc.paragraphs:
        if para.text.startswith(
            "Genel olarak RAG bileşeni ilgili belgeleri yüksek isabetle"
        ) or para.text.startswith(
            "Genel olarak, sonuçlar geliştirilen RAG bileşeninin"
        ):
            anchor = para
    if anchor is None:
        return n
    # insert in reverse so order stays 4.5 then 4.6
    node = anchor
    for text, style in reversed(SECTION_45):
        node = insert_after(anchor, text, style)
        n += 1
    return n


def update_tables(doc: Document) -> None:
    t = doc.tables[3]
    rows = [
        ["Sorgu türü", "Test sorusu sayısı", "Doğru yönlendirilen", "Yönlendirme doğruluğu"],
        ["RAG", "33", "33", "%100"],
        ["SQL", "24", "24", "%100"],
        ["HYBRID", "16", "16", "%100"],
        ["CHAT", "16", "16", "%100"],
        ["Toplam (held-out)", "89", "89", "%100"],
    ]
    while len(t.rows) < len(rows):
        t.add_row()
    for i, rowdata in enumerate(rows):
        for j, val in enumerate(rowdata):
            t.rows[i].cells[j].text = val


def global_replace(doc: Document) -> int:
    n = 0
    for para in doc.paragraphs:
        old = para.text
        new = apply_phrase_map(old)
        if new != old:
            set_para_text(para, new)
            n += 1
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for para in cell.paragraphs:
                    old = para.text
                    new = apply_phrase_map(old)
                    if new != old:
                        set_para_text(para, new)
                        n += 1
    return n


def fix_captions(doc: Document) -> None:
    mapping = {
        "Tablo 4.1. Sorgu Türlerine Göre Yönlendirme Sonuçları": (
            "Tablo 4.1. Held-out final kümesinde sorgu türlerine göre yönlendirme sonuçları (n = 89)"
        ),
        "Doğru yönlendirilen soru sayıları, belgede verilen yüzdelerden hesaplanmıştır.": (
            "Değerler held-out kümedeki tam sayılardır. Pilot (n = 100) sonuçları metinde ayrıca belirtilmiştir ve nihai başarı olarak sunulmaz."
        ),
        "Tablo 4.2. Sorgu Türlerine Göre Ortalama Yanıt Süreleri": (
            "Tablo 4.2. Geliştirme sürecindeki ön ölçümlere göre ortalama yanıt süreleri (nihai held-out e2e değildir)"
        ),
    }
    for para in doc.paragraphs:
        if para.text.strip() in mapping:
            set_para_text(para, mapping[para.text.strip()])


def main() -> None:
    doc = Document(str(SRC))
    n_para = rewrite_matching_paragraphs(doc)
    n_ins = insert_blocks(doc)
    update_tables(doc)
    fix_captions(doc)
    n_global = global_replace(doc)
    doc.save(str(DST))
    print(f"saved {DST}")
    print(f"rewritten {n_para} inserted {n_ins} global_paras {n_global}")


if __name__ == "__main__":
    main()
