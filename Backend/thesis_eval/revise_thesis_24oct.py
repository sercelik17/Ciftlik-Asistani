# -*- coding: utf-8 -*-
"""24 Ekim 2026 jüri izleme raporuna göre tez metnini belgelendirme düzeyinde düzeltir.

Sayılar evaluation_output kayıtlarından ve thesis_eval/metrics.py tanımlarından alınır.
Çalıştırılmamış LLM-only deneyi ve kör uzman puanı uydurulmaz.
"""
from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

from docx import Document
from docx.oxml import OxmlElement
from docx.table import Table
from docx.text.paragraph import Paragraph

ROOT = Path(__file__).resolve().parents[2]
SRC = Path(r"C:\Users\Serenay\Downloads\hayvancilik_duzeltme_2_ozet.docx")
OUT_DOWNLOADS = Path(r"C:\Users\Serenay\Downloads\hayvancilik_revizyon_24_10_2026.docx")
OUT_PROJECT = ROOT / "hayvancilik_revizyon_24_10_2026.docx"
HELD_OUT = ROOT / "Backend" / "evaluation_sets" / "final_heldout_set.json"

OLD_TITLE = (
    "HAYVANCILIK SEKTÖRÜNDE YAPAY ZEKÂ DESTEKLİ SOHBET ROBOTU GELİŞTİRME: "
    "LangChain ve RAG (Retrieval-Augmented Generation) TEKNOLOJİLERİYLE UYGULAMALI BİR MODEL"
)
NEW_TITLE = (
    "SÜT SIĞIRCILIĞINDA YAPILANDIRILMIŞ ÇİFTLİK VERİLERİ İLE BİLİMSEL BİLGİNİN "
    "ENTEGRASYONU İÇİN RAG TABANLI SOHBET ASİSTANI"
)
OLD_EN = (
    "Development of an AI-Powered Chatbot for the Livestock Sector: "
    "An Applied Model Using LangChain and RAG (Retrieval-Augmented Generation) Technologies"
)
NEW_EN = (
    "A RAG-Based Chat Assistant for Integrating Structured Farm Records "
    "and Scientific Knowledge in Dairy Cattle Farming"
)
SECTION_21 = (
    "Süt Sığırcılığında Yapılandırılmış Çiftlik Verileri ile Bilimsel Bilginin "
    "Entegrasyonu için RAG Tabanlı Sohbet Asistanı"
)

DELETE_PREFIXES = (
    "Eğitimde, yapay zekâ tabanlı chatbot'lar",
    "Chatbot tasarımı, bağlam duyarlı",
    "Psikolojik ve manevi destek sunan yapay zekâ destekli sohbet robotları, kullanıcıların kişiselleştirilmiş",
    "Yapay zekâ destekli robotlar, hayvancılığın dönüşümünde",
    "Ancak, bu yeniliklerin hayvancılıkta yaygın olarak benimsenmesini engelleyen",
    "Yapay zekâ destekli chatbotlar, özellikle hayvan sağlığı",
    "Veritabanları ve yapay zekânın entegrasyonu, veri analizinde hız",
    "Veritabanlarının ve yapay zekânın entegrasyonu, gerçek zamanlı, bağlama uygun",
)

REPLACEMENTS = [
    (
        "Bu araştırma iş birlikleri, ",
        "Bu araştırma, ",
    ),
    (
        "(LLM'ler), yapay zekâ ve dil teknolojilerinde",
        "Büyük dil modelleri (LLM'ler), yapay zekâ ve dil teknolojilerinde",
    ),
    (
        "(Gao vd., 2024). ümesini sorgulamak yerine, erişim yalnızca kullanıcının ilgili iş verileriyle sınırlıdır.",
        "(Gao vd., 2024). Kullanıcının veri tabanının tamamını serbestçe sorgulaması yerine, erişim yalnızca ilgili işletmenin verileriyle sınırlıdır.",
    ),
    (
        "kendi kendini düzeltme ve kaynağa bağımlılık göstergeleri incelenmiştir",
        "atıf tamlığı ve tercih edilen kaynağa isabet incelenmiştir. Ayrı bir kendi kendini düzeltme ölçümü yapılmamıştır",
    ),
    (
        "Pilot değerlendirme sırasında —özellikle SQL sorguları için— yönlendirme hatalarının yaşanmamış olması, nihai test kümesi açısından olumlu bir sonuç olsa da, iki test kümesindeki soru dağılımlarının farklı olması nedeniyle bu durum, performansta yüzde üç puanlık bir iyileşme olduğuna dair doğrudan bir kanıt olarak yorumlanmamalıdır.",
        "Pilot kümede SQL yönlendirmesi 30 sorunun 28'inde doğrudur; hatasız yönlendirme final kümeye aittir (89/89). İki kümenin soru dağılımı farklı olduğu için yüzde 97'den yüzde 100'e geçiş, üç puanlık bir iyileşmenin kanıtı sayılmamalıdır.",
    ),
    (
        "başarıyla çalıştırıldığı (24/24) bildirilmiştir.",
        "başarıyla çalıştırılmıştır (24/24). Bu sonucu tezin yazarı, referans sorguları veri tabanında çalıştırarak elde etmiştir. F-SQL019 ('Çiftliğin adını söyle') için ilk altın sorguda şema uyumsuzluğu vardı. Sorgu, SELECT ciftlik_adi FROM ciftlikler WHERE id = 1 biçiminde düzeltilmiş; gözlenen değer Tez Test Çiftliği olmuştur. Düzeltme sistem yanıtını değil, hatalı referans sorgusunu değiştirmiştir. 24/24 oranı referans SQL'in çalıştırılabilirliğidir. Modelin ürettiği SQL için execution accuracy ölçülmemiştir.",
    ),
    (
        "Genişletilmiş dil modeli",
        "Büyük dil modeli",
    ),
    (
        "Rehberlik bileşeninin nihai değerlendirmesinde",
        "Yönlendirme bileşeninin nihai değerlendirmesinde",
    ),
    (
        "Yapılandırılmış ticari verilerin",
        "Yapılandırılmış çiftlik kayıtlarının",
    ),
    (
        "ticari verilere",
        "çiftlik kayıtlarına",
    ),
    (
        "ticari verilerle",
        "sentetik çiftlik kayıtlarıyla",
    ),
    (
        "Alma Destekli Üretim (RAG)",
        "RAG",
    ),
    (
        "Artırılmış Bilgi Alma ve Üretim (RAG)",
        "RAG",
    ),
    (
        "Geri alma destekli üretim (RAG)",
        "RAG",
    ),
    (
        '"Bilgi Erişim Destekli Üretim" (Retrieval-Augmented Generation - RAG)',
        "RAG",
    ),
    (
        "Bilgi Erişim Destekli Üretim",
        "RAG",
    ),
    (
        "arama destekli üretim (SAG)",
        "geri getirme destekli üretim (RAG)",
    ),
    (
        "Doğal Dil İşleme (DDİ)",
        "doğal dil işleme (NLP)",
    ),
    (
        "Tablo 3.2, RAG bilgi tabanını oluşturmak için kullanılan 16 bilimsel belgeyi",
        "Tablo 3.1, RAG bilgi tabanını oluşturmak için kullanılan 16 bilimsel belgeyi",
    ),
    (
        "ekler kısmında ayrıntılı olarak sunulacaktır",
        "Ek Tablo 2'de sunulmuştur",
    ),
    (
        " (盖振华 vd., 2024)",
        "",
    ),
    (
        "çok işlevli, çok dilli bir gömme modeli olarak geliştirilmiştir (Chen vd., 2024).",
        "çok işlevli, çok dilli bir gömme modeli olarak geliştirilmiştir (Chen vd., 2024b).",
    ),
    (
        "Chen, G., Fan, J., & Azam, M. (2024).",
        "Chen, G., Fan, J. ve Azam, M. (2024a).",
    ),
    (
        "Chen, J., Xiao, S., Zhang, P., Luo, K., Lian, D., & Liu, Z. (2024).",
        "Chen, J., Xiao, S., Zhang, P., Luo, K., Lian, D. ve Liu, Z. (2024b).",
    ),
    (
        "B, S., P, P. R., B, S. M., & S, K. (2024).",
        "Sindhu, B., Prathamesh, R. P., Sameera, M. B. ve Kumaraswamy, S. (2024).",
    ),
    (
        "R, K., & C, M. (2024).",
        "Krishnamoorthy, R. ve Manojkumar, C. (2024).",
    ),
    (
        "“Hayvancılık Yönetimi ve Sağlık İzleme için Akıllı Çözümler”, 2026",
        "Smart solutions for livestock management and health monitoring, 2026",
    ),
    (
        "2.2.Doğal Dil İşleme",
        "2.2. Doğal Dil İşleme",
    ),
    (
        "5.2 Araştırmanın Sınırlılıkları",
        "5.2. Araştırmanın Sınırlılıkları",
    ),
    (
        "25/09/2026",
        "Ekim 2026",
    ),
    (
        "Bu ek, 10 Ekim 2026 revizyon raporundaki P0 kanıt bütünlüğü maddelerini karşılamak üzere held-out değerlendirme çıktılarından üretilmiştir. Routing doğruluğu yanıt doğruluğu değildir; referans SQL çalıştırılabilirliği Text-to-SQL execution accuracy değildir.",
        "Bu ek, final değerlendirme kayıtlarının soru düzeyinde denetlenebilmesi için hazırlanmıştır. Yönlendirme doğruluğu yanıt doğruluğu değildir. Referans SQL'in çalıştırılabilirliği, modelin ürettiği SQL için execution accuracy değildir.",
    ),
    (
        "Ek – Savunma değerlendirme tabloları (P0)",
        "EKLER",
    ),
    (
        "held-out",
        "ayrık final",
    ),
    (
        "Held-out",
        "Ayrık final",
    ),
    (
        "Security smoke",
        "Güvenlik duman testi",
    ),
    (
        "Route acc.",
        "Yönlendirme doğruluğu",
    ),
    (
        "Pref. kaynak",
        "Tercih edilen kaynak",
    ),
    (
        "F-SL018",
        "F-SQL018",
    ),
    (
        "FAISS-HNSW indeksi ve çapraz kodlayıcı tabanlı yeniden sınıflandırma",
        "FAISS üzerinde HNSW yaklaşık en yakın komşu indeksi ve bundan ayrı bir çapraz kodlayıcı ile yeniden sıralama",
    ),
]


def set_run_text(paragraph: Paragraph, new_full: str) -> None:
    if paragraph.runs:
        paragraph.runs[0].text = new_full
        for run in paragraph.runs[1:]:
            run.text = ""
    else:
        paragraph.add_run(new_full)


def replace_in(paragraph: Paragraph, old: str, new: str) -> bool:
    full = paragraph.text
    if old not in full:
        return False
    set_run_text(paragraph, full.replace(old, new))
    return True


def insert_after(paragraph: Paragraph, text: str, style: str | None) -> Paragraph:
    new_p = OxmlElement("w:p")
    paragraph._p.addnext(new_p)
    new_para = Paragraph(new_p, paragraph._parent)
    if style:
        new_para.style = style
    if text:
        new_para.add_run(text)
    return new_para


def insert_block_after(paragraph: Paragraph, items: list[tuple[str, str]]) -> Paragraph:
    current = paragraph
    for style, text in items:
        current = insert_after(current, text, style)
    return current


def insert_before(paragraph: Paragraph, text: str, style: str | None) -> Paragraph:
    new_p = OxmlElement("w:p")
    paragraph._p.addprevious(new_p)
    new_para = Paragraph(new_p, paragraph._parent)
    if style:
        new_para.style = style
    if text:
        new_para.add_run(text)
    return new_para


def all_paragraphs(doc: Document) -> list[Paragraph]:
    found: list[Paragraph] = list(doc.paragraphs)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                found.extend(cell.paragraphs)
    return found


def find_paragraph(doc: Document, start: str, style: str | None = None) -> Paragraph | None:
    for paragraph in doc.paragraphs:
        style_name = paragraph.style.name if paragraph.style is not None else ""
        if style_name in {"T1", "T2", "T3"}:
            continue
        if style and style_name != style:
            continue
        if paragraph.text.strip().startswith(start):
            return paragraph
    return None


def demote_false_headings(doc: Document) -> int:
    changed = 0
    for paragraph in doc.paragraphs:
        style_name = paragraph.style.name if paragraph.style else ""
        text = paragraph.text.strip()
        if style_name not in {"Balk2", "Balk3"}:
            continue
        if len(text) < 180:
            continue
        if re.match(r"^\d+\.\d+", text):
            continue
        if text.startswith(("Tablo ", "Şekil ", "Ek Tablo")):
            continue
        paragraph.style = "Normal"
        changed += 1
    target = find_paragraph(doc, "3.4. LangChain")
    if target is not None:
        target.style = "Balk2"
        changed += 1
    return changed


def apply_replacements(doc: Document) -> int:
    count = 0
    for paragraph in all_paragraphs(doc):
        for old, new in REPLACEMENTS:
            if replace_in(paragraph, old, new):
                count += 1
    return count


def retitle(doc: Document) -> None:
    for paragraph in doc.paragraphs:
        text = paragraph.text.strip()
        style_name = paragraph.style.name if paragraph.style else ""
        if SECTION_21 in text and style_name in {"Balk2", "T2"}:
            suffix = text.replace(SECTION_21, "").strip()
            page = suffix if suffix.isdigit() else ""
            label = "2.1. Hayvancılıkta Dijitalleşme ve Bilgiye Erişim" + page
            set_run_text(paragraph, label)
    for paragraph in all_paragraphs(doc):
        if OLD_TITLE in paragraph.text:
            replace_in(paragraph, OLD_TITLE, NEW_TITLE)
        if OLD_EN in paragraph.text:
            replace_in(paragraph, OLD_EN, NEW_EN)


def delete_duplicates(doc: Document) -> int:
    removed = 0
    for paragraph in list(doc.paragraphs):
        text = paragraph.text.strip()
        if any(text.startswith(prefix) for prefix in DELETE_PREFIXES):
            element = paragraph._element
            parent = element.getparent()
            if parent is not None:
                parent.remove(element)
                removed += 1
    return removed


def clean_cell_text(text: str) -> str:
    cleaned = text
    cleaned = cleaned.replace("F-SL018", "F-SQL018")
    cleaned = re.sub(
        r"Decimal\('([0-9]+(?:\.[0-9]+)?)'\)",
        lambda match: match.group(1).replace(".", ","),
        cleaned,
    )
    cleaned = re.sub(r"\[\('([^']+)',\)\]", r"\1", cleaned)
    cleaned = re.sub(r"\[\[?\((\d+),\)\]?\]", r"\1", cleaned)
    cleaned = re.sub(r"\[\((\d+),\)\]", r"\1", cleaned)
    vague = (
        "önceki listedeki aday kayıt",
        "kesin eşleştirilemedi",
        "tam yazar, yıl ve başlık belirlenemedi",
        "olası protokol belgesi",
        "raporda",
    )
    if any(token in cleaned for token in vague):
        cleaned = re.sub(r"\[[^\]]{0,240}\]", "", cleaned)
        cleaned = re.sub(r"\([^)]*eşleştirilemedi[^)]*\)", "", cleaned)
        cleaned = re.sub(r"\s{2,}", " ", cleaned).strip(" ;")
    if re.fullmatch(r"-?\d+\.\d+", cleaned.strip()):
        cleaned = cleaned.strip().replace(".", ",")
    if cleaned.strip() in {"True", "False"}:
        cleaned = "Doğru" if cleaned.strip() == "True" else "Yanlış"
    return cleaned


def clean_tables(doc: Document) -> int:
    changed = 0
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    updated = clean_cell_text(paragraph.text)
                    if updated != paragraph.text:
                        set_run_text(paragraph, updated)
                        changed += 1
    for paragraph in doc.paragraphs:
        stripped = paragraph.text.strip()
        if re.fullmatch(r"\d+\.\d+", stripped):
            set_run_text(paragraph, stripped.replace(".", ","))
            changed += 1
    return changed


def append_if_missing(paragraph: Paragraph, sentence: str, marker: str) -> None:
    if marker in paragraph.text:
        return
    text = paragraph.text.rstrip()
    if text and not text.endswith("."):
        text += "."
    set_run_text(paragraph, text + " " + sentence)


PROTOCOL = [
    ("Balk2", "3.8. Deneysel Tasarım ve Değerlendirme Protokolü"),
    (
        "Normal",
        "Değerlendirme iki kümeye ayrılmıştır. Yüz soruluk küme (50 RAG, 30 SQL, 20 HYBRID) geliştirme ve pilot kümesidir; birleştirme ağırlıklarının karşılaştırılması bu kümede yapılmıştır. Seksen dokuz soruluk ayrık final küme 33 RAG, 24 SQL, 16 HYBRID ve 16 CHAT sorusundan oluşur. Final soruların kimliği, soru metni, altın kanalı ve RAG soruları için tercih edilen belge adları Ek Tablo F'de verilmiştir. Pilot yüzdelerden türetilen yaklaşık 49 ve yaklaşık 28 sayıları ham satır arşivi bulunmadığı için kesin sayım değildir. Final 89/89 sayımı soru düzeyinde kayıtlıdır.",
    ),
    (
        "Normal",
        "Yönlendirme önce kural eşleşmesiyle yapılır. Kural eşleşirse dil modeli çağrılmaz. Kısa selamlama CHAT; çiftlik kaydı ile bilimsel terim birlikteyse HYBRID; yalnız çiftlik kaydı veya hayvan adı SQL; yalnız bilimsel terim RAG kabul edilir. Eşleşme yoksa yönlendirme modele bırakılır. Terim listesi ve karar sırası Ek Tablo H'de özetlenmiştir. Kurallar final sorular yazılırken görülmüş olabilir. Bu nedenle yüzde 100 yönlendirme, bağımsız bir kullanıcı dağılımına genellenmez.",
    ),
    (
        "Normal",
        "Bilgi erişiminde ilgili belge, araştırmacının soru dosyasına yazdığı tercih edilen dosya adıdır. İlgililik ikili ve belge düzeyindedir; parça düzeyinde dereceli etiket, yazılı yönerge ve ikinci etiketleyen yoktur. P@5, getirilen ilk beş belgede tercih edilen dosya oranıdır. R@5, tercih edilen dosyalardan ilk beşte yakalananların oranıdır. MRR, ilk ilgili belgenin sıra tersidir. nDCG@5 ikili kazançla hesaplanır. Bu etiketler soru yazarı tarafından konduğu için retrieval başarısı, bağımsız bir ilgili-parça yargısı değildir.",
    ),
    (
        "Normal",
        "RAG üretim metrikleri ayrı bir hakem model kullanmaz. thesis_eval/metrics.py içindeki generation_metrics fonksiyonu 33 yanıtın her birine uygulanır ve ortalama alınır. Atıf, yanıtta [K1] biçiminde geçen kimliktir. Atıf doğruluğu, o yanıtta atıf varsa geçerli kimlik sayısının toplam atıf sayısına bölümüdür; atıf yoksa 0 yazılır. Payda 33 sorudur. Gözlenen ortalama 0,303'tür ve 10 yanıtta atıfların tamamı getirilen kimliklerle uyumludur. Atıf tamlığı, noktayla ayrılmış cümlelerden [K] taşıyanların oranıdır. Desteksiz iddia oranı, bu oranın tümleyeni olarak tanımlanmıştır; cümleleri ayrıca bir modelle iddiaya ayıran bir işlem yoktur. Otuz üç soruluk ortalama atıf tamlığı 0,1364, desteksiz iddia oranı 0,8636'dır. Tercih edilen kaynağa isabet, getirilen belge adlarından tercih listesinde olanların oranının soru ortalamasıdır (0,6818). Bu ölçü, yanıtta yazılan atıf değil, retrieval listesindeki dosya adıdır. P@5 ile arasındaki fark bu nedenle beklenen bir farktır: belge getirilmiş olsa da model her cümleye atıf yazmamaktadır.",
    ),
    (
        "Normal",
        "Sıfırdan ikiye doğruluk ve bağlılık proxy'leri de hakem model değildir. Otomatik kural; tercih isabeti, desteksiz iddia oranı, atıf doğruluğu ve tanı reddi sözcüklerine bakar. Otuz üç soruda otomatik doğruluk ortalaması 1,121, bağlılık ortalaması 0,606'dır. Aynı 33 yanıt araştırmacı tarafından tek geçişte puanlanmıştır: doğruluk 1,152, bağlılık 0,545, doğruluk puanı uyumu 0,939. İkinci puanlayan bağımsız bir veteriner hekim değildir ve puanlama kör değildir. Cohen kappa hesaplanmamıştır. Tanı reddi 33/33, yanıtta veteriner hekim, tanı veya antibiyotik sınırına ilişkin bir ifade aranarak sayılmıştır. RAG sorularının tamamı tanı veya ilaç istemi değildir; bu oran bir güvenlik duman testi değil, red dili taramasıdır.",
    ),
    (
        "Normal",
        "SQL için iki ayrı oran vardır. Referans SQL çalıştırılabilirliği 24/24'tür ve modelin yazdığı SQL'i ölçmez. Sayısal veya varlık tutarlılığı, doğal dil yanıtındaki değerin altın sonuçla uyumudur. Soru düzeyindeki kayıt 24 sorunun 17'sinde uyum gösterir (0,708). Daha önceki ana metindeki 15/24 (0,625) toplamı, bu satır sayımıyla değiştirilmiştir. Uyumsuz sorular F-SQL006, F-SQL010, F-SQL012, F-SQL013, F-SQL015, F-SQL020 ve F-SQL023'tür. Yirmi iki soru şablon SQL, iki soru yedek çalışma yolu kullanmıştır. Wilson yüzde 95 aralığı 17/24 için 0,508–0,853'tür. HYBRID uçtan uca bayrağı dört koşulun birleşimidir: kanal HYBRID'dir, yanıtta beklenen çiftlik varlığı vardır, tercih edilen belge retrieval listesindedir ve tanı veya antibiyotik sızıntısı yoktur. On altı sorunun 11'i bu birleşimi sağlar (0,6875; Wilson yüzde 95 aralığı yaklaşık 0,44–0,86). Kayıtlarda başarısız beş soru F-HYB001, F-HYB006, F-HYB011, F-HYB012 ve F-HYB015'tir. Ek Tablo E'de diğer bayraklar doğru kaldığı için bu oran sentez doğruluğu değil, tercih edilen kaynağın seçilme oranıdır.",
    ),
    (
        "Normal",
        "Gecikme, istek ile yanıtın tamamlanması arasındaki saniyedir. RAG final dağılımı n=33, ortalama 44,61, medyan 41,19, standart sapma 13,38, en küçük 0,002, en büyük 76,92 ve p95 60,79 saniyedir. SQL kaydı n=24, ortalama 2,29, medyan 0,015, standart sapma 7,61, en küçük 0,011, en büyük 31,02 ve p95 0,045 saniyedir; ortalama, 31 saniyelik bir gözlem tarafından çekilir. HYBRID kaydı n=16, ortalama 0,36, medyan 0,058, standart sapma 1,18, en küçük 0,040, en büyük 4,92 ve p95 0,079 saniyedir. Bu HYBRID süresi retrieval ve kural kontrolünü kapsar; dil modeli sentezinin süresini içermez. CHAT kanalı için ayrı final gecikme dağılımı kaydedilmemiştir. Güvenlik duman testi dört senaryodur: istem enjeksiyonu, yazma içeren SQL, tanı veya ilaç talebi ve çiftlik kimliği izolasyonu notu. Dördü de beklenen ret veya engel davranışını vermiştir. Bu test bir sızma testi değildir.",
    ),
    (
        "Normal",
        "Aynı 33 RAG sorusunda retrieval bağlamı kapatılarak yalnız Mistral ile üretim yapılmamıştır. Atıf metrikleri bağlam kimliklerine bağlı olduğu için, bu karşılaştırma olmadan RAG'in yanıt kalitesine katkısı olumlu, etkisiz veya olumsuz diye sayılamaz. Katkı iddiası bu nedenle ölçülen üretim açığının gösterilmesiyle sınırlıdır.",
    ),
]

DB_SCALE = (
    "Normal",
    "Sentetik PostgreSQL kayıtları bir prototip ölçeğindedir. Referans sorguların gözlenen sonuçlarına göre veri tabanında bir çiftlik (Tez Test Çiftliği), beş inek ve 1–5 Eylül 2026 arasında 50 sağım kaydı vardır. Holstein sayısı 3, Simental sayısı 2'dir. Hayvan adları Serap, Beyza, Boncuk, Papatya ve Laledir; küpe numaraları TR0001–TR0005 aralığındadır. Süt miktarı litre olarak tutulur. Beş hayvan ve yaklaşık bir haftalık kayıt, 'en yüksek on inek', çok aylık trend veya ABC segmentasyonu gibi işlevlerin genellenmesini engeller. Şekil 4.3'teki grafik yaklaşık 30 Ağustos–5 Eylül aralığını gösterir. Kayıtlar elle veya betikle kurulmuş örnek kayıtlardır; ticari bir işletmeden alınmamıştır.",
)

CONFIG = (
    "Normal",
    "Final deneyin geçerli yapılandırması Tablo 3.2'dir. Üretim modeli Ollama üzerinde mistral etiketidir; yüklü paket mistral:latest, GGUF, 7,2 milyar parametre ve Q4_K_M kuantizasyonudur. Model özeti 6577803aa9a0 ile başlar. Deney parametreleri temperature 0, seed 0, num_predict 160 ve num_ctx 2048'dir. Model kartındaki üst bağlam uzunluğu 32768'dir; deney bu üst sınırı değil, 2048 değerini kullanmıştır. Şekil 3.1'de görülen 4096 bağlam, 320 token çıktı ve mistral:latest etiketi önceki mimari çizime aittir ve final sayılar için esas alınmaz. Üretim çağrısı kodda num_gpu=0 ile yapılmıştır. Donanım Intel Core i7-11800H, 16 GB RAM ve NVIDIA GeForce RTX 3050 Ti 4 GB'dir. Ortalama 44,6 saniyelik RAG gecikmesi bu koşullarda ölçülmüştür; gecikmenin tek nedeni olduğu ayrıca ölçülmemiştir. Üretim istemi Türkçe yanıt, en fazla üç cümle, her bilimsel cümlenin sonunda [K] atıfı, bağlam dışında 'yeterli bilgi bulunamadı' deme, tanı ve antibiyotik yasağı kurallarını içerir. İstem metni Ek Tablo H'dedir. Konu kategorisi, belge klasörünü retrieval sırasında süzmek için ayrı bir doğruluk tablosuyla raporlanmamıştır.",
)

FIGURE_NOTES = [
    (
        "Normal",
        "Şekil 4.1–4.4 başarılı ürün örnekleri olarak değil, üretim katmanındaki hata örnekleri olarak okunmalıdır. Şekil 4.1'de 'en yüksek on inek' istenmesine karşın beş inek listelenmiş, yanıt bu listenin on inek içerdiğini söylemiş ve süt miktarı kilogram olarak yazılmıştır. Veri tabanı birimi litredir. Bu, sayısal sözelleştirme ve birim tutarsızlığıdır.",
    ),
    (
        "Normal",
        "Şekil 4.2'de aynı yanıtın içinde İspanyolca sözcükler ve aynı hayvan için birbiriyle çelişen değişim yüzdeleri görülmektedir. Serap için ekranda yazılan düşüş, alarm kaydındaki yüzde 39,06 değeriyle aynı cümlede uzlaştırılmamıştır. Bu örnek dil karışması ve iç tutarsızlıktır. Şekil 4.4'te küpe öneki TRTR biçiminde tekrarlanmış, Serap için yüzde 43 dalgalanma yazılmıştır. Alarm tablosundaki düşüş yüzdesi ile ekrandaki dalgalanma yüzdesi aynı tanım değildir; arayüz bu farkı açıklamaz. Şekil 4.3'ün 'son on gün' etiketi, grafikte görünen yaklaşık yedi günü (30 Ağustos–5 Eylül) aşar. Şekil 3.3 ve Şekil 4.3'te işletim sistemi etkinleştirme filigranı vardır. Bu görüntüler yeniden çekilmeden savunmada nitel hata örneği olarak kullanılmalıdır.",
    ),
]

DISCUSSION = [
    (
        "Normal",
        "Retrieval katmanı ile üretim katmanı aynı başarıyı ölçmez. FAISS P@5 0,90 ve nDCG@5 0,92 iken atıf doğruluğu 0,303 ve cümle düzeyinde atıf tamlığı 0,1364'tür. Darboğaz, belgenin bulunması değil, bulunan belgenin kısa Türkçe yanıtta kaynak kimliğiyle birlikte kullanılmasıdır. Yedi milyar parametreli model, 160 token çıktı sınırı ve atıf zorunluluğu bu açığın olası teknik nedenleridir. Bu nedenlerden hiçbiri ayrı bir ablasyonla sınanmamıştır. Lewis ve arkadaşlarının (2020) RAG çerçevesi, dış bağlamın üretimi koşullamasını amaçlar. Bu tezde bağlam getirilmiş, ancak cümlelerin büyük bölümü [K] kimliği taşımamıştır. Gao ve arkadaşlarının (2024) Text-to-SQL değerlendirmesi modelin yazdığı sorgunun çalıştırılmasını ölçer. Bu tezde ölçülen 24/24 oranı o ölçüt değildir.",
    ),
    (
        "Normal",
        "HYBRID oranı, bilimsel açıklama ile çiftlik sayısının tutarlı biçimde birleştirildiğini göstermez. Başarısız beş sorunun ortak özelliği tercih edilen belgenin seçilmemesidir. Bu yüzden Bölüm 5'teki yorum, sentez hatasından çok kaynak seçimi hatasına bağlanmalıdır. Beş inek ve 50 sağım kaydı, SQL tutarlılığının işletme ölçeğinde geçerli olduğunu göstermez.",
    ),
]

LIMITATION = (
    "Normal",
    "Üretim katmanında aynı 33 sorunun yalnız model ile, retrieval olmadan ölçülmemesi bu çalışmanın başlıca açık deneyidir. Otomatik atıf metrikleri bir hakem modelin anlamsal kararı değil, [K] kimliği ve cümle örüntüsü kuralıdır. İnsan puanı tek araştırmacıya aittir. Sentetik veri tabanı bir çiftlik, beş inek ve 50 sağım kaydından ibarettir. Yönlendirme kuralları final soru metinlerinden bağımsız dondurulduğuna dair ayrı bir tarih kaydı yoktur.",
)

CONTRIBUTION = (
    "Normal",
    "Çalışmanın savunulabilir katkısı, süt sığırcılığı için SQL, RAG, HYBRID ve CHAT kanallarını tek yönlendiricide birleştiren prototip ile bu prototipin katman katman ölçülmesidir. Ölçüm, yönlendirmenin güçlü, retrieval'ın belge düzeyinde güçlü, üretimin ise atıf bakımından zayıf olduğunu gösterir. Katkı, sahada güvenilir bilimsel yanıt üretildiğinin iddiası değil, bu güvenilirlik açığının sayısal olarak ayrıştırılmasıdır.",
)

GAP = [
    (
        "Normal",
        "Bu tezle karşılaştırıldığında literatür dört eksende durur. RAG çalışmaları dış bağlamla üretimi birleştirmeyi önerir; bu tez aynı çerçeveyi süt sığırcılığı belgelerine uygular ve atıf tamlığının düşük kaldığını ölçer. Hibrit retrieval çalışmaları yoğun ve seyrek sıralamayı birleştirir; bu tez FAISS ile BM25 sonuçlarını 0,60/0,40 ağırlıklı RRF ile birleştirir, ancak doğru belgenin yanıt cümlesine taşınmadığını ayrıca gösterir. Text-to-SQL çalışmaları modelin yazdığı sorgunun yürütme doğruluğunu ölçer; bu tez şablon SQL ve referans sorgu çalıştırılabilirliğini ölçer, model SQL'ini ölçmez. Yapılandırılmış ve yapılandırılmamış kaynağı birlikte kullanan karar destek çalışmaları sentez vaat eder; bu tezde HYBRID başarısı kaynak seçimine indirgenmiş, sentez doğruluğu ayrı puanlanmamıştır.",
    ),
]

CITATION_SENTENCE = (
    " Sohbet robotunun benimsenmesi, eğitim yazınındaki bibliyometrik dağılım ve sağlık alanında kullanıcı özelliklerine göre değişen kabul yolları ayrı çalışmalarda incelenmiştir (Le, 2023; Lin ve Yu, 2023; Liu, Ho ve Wu, 2026)."
)

BIBLIOGRAPHY = [
    "Bernard, J. K. ve Montgomery, M. J. (t.y.). Managing intake of lactating dairy cows (PB 1598). The University of Tennessee Agricultural Extension Service.",
    "Codex Alimentarius Commission. (2007). Milk and milk products (1. bs.). FAO/WHO. İçinde Code of Hygienic Practice for Milk and Milk Products.",
    "Darbaz, İ. ve Ergene, O. (2015). Sürü meme sağlığı yönetiminde somatik hücre sayısının önemi. Erciyes Üniversitesi Veteriner Fakültesi Dergisi, 12(3), 203-210.",
    "Expo. (2026). Expo documentation. https://docs.expo.dev/",
    "FAO ve IDF. (2011). Guide to good dairy farming practice (2. bs.). FAO Animal Production and Health Guidelines.",
    "FAO Regional Dairy Development and Training Team for Asia and the Pacific. (1993). Small-scale dairy farming manual (C. 5). Food and Agriculture Organization of the United Nations.",
    "Fricke, P. M. (2018). Evolution of timed AI protocols and overview of the 2018 DCRC reproductive management strategies protocol sheet for dairy cows. Dairy Cattle Reproduction Council.",
    "Fricke, P. M., Wiltbank, M. C. ve Pursley, J. R. (2023). The high fertility cycle. University of Wisconsin–Madison Division of Extension.",
    "Kurt, S., Çolakoğlu, H. E., Yazlık, M. O., Vural, M. R. ve Küplülü, Ş. (2019). Sütçü ineklerde mastitis yönünden kuru ve geçiş dönemlerinin önemi. Atatürk Üniversitesi Veteriner Bilimleri Dergisi, 14(1), 107-113. https://doi.org/10.17094/ataunivbd.407022",
    "LangChain. (2026). LangChain documentation. https://python.langchain.com/",
    "Makkar, H. P. S. (2012). Balanced feeding for improving livestock productivity (FAO Animal Production and Health Paper No. 173). Food and Agriculture Organization of the United Nations.",
    "Meta Platforms. (2026). React Native. https://reactnative.dev/",
    "Moriel, P. ve Batistel, F. (2021). Nutrition at early stages of life determines the future growth and reproductive performance of dairy calves (AN336). UF/IFAS Extension. https://doi.org/10.32473/edis-an336-2021",
    "Overton, T. R. (t.y.). Effective transition cow management to maximize internal herd growth. Cornell University, Department of Animal Science.",
    "Öcal, G. O., Güven, F. M. ve Cedden, F. (2026). Evaluation of housing and management conditions affecting animal welfare in dairy cattle farms in Ankara Province, Türkiye. ADÜ Ziraat Dergisi, 23(1), 47-53. https://doi.org/10.25308/aduziraat.1850888",
    "Ramírez, S. (2026). FastAPI documentation. https://fastapi.tiangolo.com/",
    "Snarr, A. (t.y.). The importance of colostrum. Utah State University Extension. Dosya adı 2026 yılına işaret eder; kapak metninde yıl satırı okunamamıştır.",
    "University of Wisconsin–Madison Division of Extension. (t.y.). The fresh cow: Milk fever.",
    "WOAH. (2024). Animal welfare and dairy cattle production systems. Terrestrial Animal Health Code (Bölüm 7.11).",
    "Yalçın, H. ve Çakmak, T. (2022). İnek sütlerinde somatik hücre sayısı ve bazı parametrelerin araştırılması. Manas Journal of Agriculture Veterinary and Life Sciences, 12(1), 81-87. https://doi.org/10.53518/mjavl1092994",
]

CORPUS_ROWS = [
    ("D01", "FAO küçük ölçekli sütçülük el kitabı, C. 5, 1993", "278", "326"),
    ("D02", "Kurt vd., 2019, Atatürk Üniv. Vet. Bil. Derg.", "7", "37"),
    ("D03", "Darbaz ve Ergene, 2015, Erciyes Üniv. Vet. Fak. Derg.", "8", "41"),
    ("D04", "Yalçın ve Çakmak, 2022, MJAVL", "7", "47"),
    ("D05", "Makkar, 2012, FAO Paper 173", "39", "125"),
    ("D06", "Bernard ve Montgomery, Tennessee PB 1598", "7", "23"),
    ("D07", "Wisconsin Extension, The fresh cow: Milk fever", "2", "10"),
    ("D08", "Overton, Cornell geçiş dönemi", "25", "25"),
    ("D09", "Moriel ve Batistel, 2021, UF/IFAS AN336", "6", "30"),
    ("D10", "Snarr, Utah State, kolostrum bilgi notu", "8", "33"),
    ("D11", "Fricke, 2018, DCRC protokol özeti", "19", "93"),
    ("D12", "Fricke, Wiltbank ve Pursley, 2023, High fertility cycle", "8", "31"),
    ("D13", "WOAH, 2024, Kara hayvanları sağlık kodu 7.11", "14", "72"),
    ("D14", "Öcal, Güven ve Cedden, 2026, ADÜ Ziraat Derg.", "8", "48"),
    ("D15", "FAO ve IDF, iyi süt çiftçiliği rehberi", "44", "144"),
    ("D16", "Codex, 2007, süt ve süt ürünleri", "249", "748"),
]

ROUTING_APPENDIX = (
    "Ek Tablo H. Yönlendirme kararı ve üretim istemi. Karar sırası şöyledir. Beş sözcükten kısa selamlama, teşekkür veya 'ne yapabilirsin' girdisi CHAT olur. Metinde hem çiftlik izi (bugün, küpe, sağım, litre, alarm, hayvan adı) hem bilimsel iz (mastitis, somatik, rasyon, kolostrum, refah, literatür) varsa kanal HYBRID olur. Yalnız çiftlik izi varsa SQL, yalnız bilimsel iz varsa RAG olur. Hiçbiri yoksa yönlendirme modele bırakılır. Üretim isteminin bağlayıcı kuralları şunlardır: yalnız verilen kaynak bağlamını kullan; her zaman Türkçe yaz; en fazla üç kısa cümle kur; her bilimsel cümlenin sonuna bağlamdaki [K] kimliğini yaz; tanı koyma; antibiyotik veya doz önerme; bağlam yetersizse yeterli bilginin bulunamadığını söyle; JSON veya kod üretme. SQL yolu, serbest metinden model SQL'i üretmek yerine önceden tanımlanmış şablonları doldurur. Yalnız şablon eşleşmezse yedek çalışma yolu denenir."
)

OZET_SENTENCE = (
    "Üretim katmanında atıf doğruluğu 0,303, atıf tamlığı 0,1364 ve desteksiz iddia oranı 0,8636'dır. "
    "SQL doğal dil yanıt tutarlılığı 17/24 (0,708), HYBRID uçtan uca oran 11/16 (0,6875) bulunmuştur. "
    "Bu değerler yönlendirme başarısının yanıt güvenilirliği anlamına gelmediğini gösterir."
)


def move_table_after(paragraph: Paragraph, table: Table) -> None:
    paragraph._p.addnext(table._tbl)


def add_corpus_table(doc: Document, after: Paragraph) -> Paragraph:
    caption = insert_after(
        after,
        "Ek Tablo 2. Bilgi tabanı belgelerinin sayfa ve parça dökümü. Parça sayıları toplamı 1.833'tür. Sayfa birimi, indekste tutulan sayfa kayıtlarının belge bazındaki sayısıdır.",
        "Normal",
    )
    table = doc.add_table(rows=1 + len(CORPUS_ROWS), cols=4)
    headers = ("Kod", "Künye", "Sayfa birimi", "Parça")
    for index, header in enumerate(headers):
        table.rows[0].cells[index].text = header
    for row_index, row in enumerate(CORPUS_ROWS, start=1):
        for col_index, value in enumerate(row):
            table.rows[row_index].cells[col_index].text = value
    move_table_after(caption, table)
    return caption


def add_question_appendix(doc: Document, after: Paragraph) -> Paragraph:
    questions = json.loads(HELD_OUT.read_text(encoding="utf-8"))
    heading = insert_after(
        after,
        "Ek Tablo F. Ayrık final soru listesi. Kanal, soru dosyasına yazılmış altın kanaldır. Tercih edilen belgeler RAG soruları için ilgililik etiketidir.",
        "Balk2",
    )
    current = heading
    for item in questions:
        preferred = item.get("preferred_sources") or []
        preferred_text = "; ".join(preferred) if preferred else "—"
        line = f"{item['id']} | {item['route']} | {item['question']} | {preferred_text}"
        current = insert_after(current, line, "Normal")
    return current


def insert_main_sections(doc: Document) -> None:
    ozet = find_paragraph(doc, "Bu çalışmanın amacı, süt sığırcılığı")
    if ozet is not None:
        append_if_missing(ozet, OZET_SENTENCE, "0,8636")

    chapter4 = find_paragraph(doc, "4. BULGULAR", "Balk1")
    if chapter4 is None:
        chapter4 = find_paragraph(doc, "4. BULGULAR")
    if chapter4 is not None:
        for style, text in PROTOCOL:
            insert_before(chapter4, text, style)

    corpus_note = find_paragraph(doc, "Tabloda, geliştirilen sohbet robotunun RAG")
    if corpus_note is not None:
        insert_after(corpus_note, DB_SCALE[1], DB_SCALE[0])

    config_anchor = find_paragraph(doc, "mistral; temperature")
    if config_anchor is None:
        config_anchor = find_paragraph(doc, "3.5. Büyük Dil Modeli")
    if config_anchor is not None:
        insert_after(config_anchor, CONFIG[1], CONFIG[0])

    findings = find_paragraph(doc, "4.2. Soru-Cevap")
    if findings is not None:
        for style, text in FIGURE_NOTES:
            insert_before(findings, text, style)

    discussion = find_paragraph(doc, "5.2. Araştırmanın Sınırlılıkları")
    if discussion is None:
        discussion = find_paragraph(doc, "5.2. Araştırmanın")
    if discussion is not None:
        for style, text in DISCUSSION:
            insert_before(discussion, text, style)
        insert_after(discussion, LIMITATION[1], LIMITATION[0])

    conclusion = find_paragraph(doc, "5.3. Sonuç")
    if conclusion is not None:
        # İlk gövde paragrafının ardından katkıyı ekle.
        following = conclusion._p.getnext()
        if following is not None:
            host = Paragraph(following, conclusion._parent)
            insert_after(host, CONTRIBUTION[1], CONTRIBUTION[0])

    chapter3 = find_paragraph(doc, "3. MATERYAL", "Balk1")
    if chapter3 is None:
        chapter3 = find_paragraph(doc, "3. MATERYAL")
    if chapter3 is not None:
        for style, text in GAP:
            insert_before(chapter3, text, style)

    chatbot = find_paragraph(doc, "Yapay zekâ tabanlı sohbet robotları, kullanıcıların")
    if chatbot is not None and "Le, 2023" not in chatbot.text:
        append_if_missing(chatbot, CITATION_SENTENCE.strip(), "Le, 2023")

    sources = find_paragraph(doc, "KAYNAKLAR", "Balk1")
    appendix = find_paragraph(doc, "EKLER")
    if appendix is None:
        appendix = find_paragraph(doc, "Ek Tablo A")
    anchor = appendix if appendix is not None else sources
    if anchor is not None:
        insert_before(
            anchor,
            "Bilgi tabanı ve yazılım künyeleri. Aşağıdaki kayıtlar corpus PDF'lerinin ilk sayfasından veya resmi yazılım belgesinden alınmıştır. D01 dosyası FAO Hayvan Üretimi ve Sağlığı Belgesi 78 değil, 1993 tarihli Small-scale dairy farming manual Cilt 5'tir.",
            "Normal",
        )
        for entry in BIBLIOGRAPHY:
            insert_before(anchor, entry, "Normal")

    ek_a = find_paragraph(doc, "Ek Tablo A")
    if ek_a is not None:
        add_corpus_table(doc, ek_a)
        tail = add_question_appendix(doc, ek_a)
        insert_after(tail, ROUTING_APPENDIX, "Normal")

    def find_toc(start: str) -> Paragraph | None:
        for paragraph in doc.paragraphs:
            style_name = paragraph.style.name if paragraph.style is not None else ""
            if style_name in {"T1", "T2", "T3"} and paragraph.text.strip().startswith(start):
                return paragraph
        return None

    toc_33 = find_toc("3.3. Sohbet Robotunun")
    if toc_33 is not None:
        insert_after(toc_33, "3.4. LangChain ve RAG Altyapısının Geliştirilmesi", "T2")
    toc_37 = find_toc("3.7. Kullanıcı Arayüzünün")
    if toc_37 is not None:
        insert_after(toc_37, "3.8. Deneysel Tasarım ve Değerlendirme Protokolü", "T2")


def main() -> None:
    if not SRC.exists():
        raise SystemExit(f"Kaynak tez yok: {SRC}")
    doc = Document(str(SRC))
    retitle(doc)
    heading_fixes = demote_false_headings(doc)
    replacements = apply_replacements(doc)
    removed = delete_duplicates(doc)
    cell_fixes = clean_tables(doc)
    insert_main_sections(doc)
    doc.save(str(OUT_DOWNLOADS))
    shutil.copyfile(OUT_DOWNLOADS, OUT_PROJECT)
    print(
        json.dumps(
            {
                "heading_fixes": heading_fixes,
                "replacements": replacements,
                "removed_duplicates": removed,
                "cell_fixes": cell_fixes,
                "downloads": str(OUT_DOWNLOADS),
                "project": str(OUT_PROJECT),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
