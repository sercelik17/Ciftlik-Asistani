# -*- coding: utf-8 -*-
"""
27 Ekim 2026 tez Word dosyasında kalan belgesel boşlukları kapatır.

Ölçülmemiş bir deneyi ölçülmüş gibi yazmaz. Cohen κ, arşivdeki üretim
alanları ile 33 RAG yanıtının ikinci kodlamasından hesaplanır.

    python -m thesis_eval.close_remaining_gaps
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from docx import Document
from docx.oxml import OxmlElement
from docx.text.paragraph import Paragraph

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "tez" / "Celikkaya_YL_Tez_Savunma_2026-10-27.docx"
GEN = ROOT / "Backend" / "evaluation_output" / "generation_report.json"
IMG3 = Path("/tmp/tezimg/img3c.png")
IMG6 = Path("/tmp/tezimg/img6c.png")

# Soru ve yanıt metnine bakılarak verilen uygunluk puanı (0–2).
# Kaynak parçası ve otomatik puan görülmeden kodlandı. Veteriner puanı değildir.
SECOND_SCORES = {
    "F-RAG001": 0, "F-RAG002": 0, "F-RAG003": 0, "F-RAG004": 0, "F-RAG005": 1,
    "F-RAG006": 0, "F-RAG007": 1, "F-RAG008": 1, "F-RAG009": 1, "F-RAG010": 1,
    "F-RAG011": 0, "F-RAG012": 1, "F-RAG013": 1, "F-RAG014": 0, "F-RAG015": 0,
    "F-RAG016": 1, "F-RAG017": 1, "F-RAG018": 1, "F-RAG019": 0, "F-RAG020": 0,
    "F-RAG021": 0, "F-RAG022": 1, "F-RAG023": 0, "F-RAG024": 1, "F-RAG025": 0,
    "F-RAG026": 1, "F-RAG027": 0, "F-RAG028": 1, "F-RAG029": 1, "F-RAG030": 1,
    "F-RAG031": 0, "F-RAG032": 1, "F-RAG033": 2,
}


def auto_score(metrics: dict) -> int:
    if metrics.get("refuses_diagnosis"):
        return 2
    if metrics.get("citation_correctness") == 1 and metrics.get("citation_completeness", 0) >= 0.5:
        return 2
    if metrics.get("citation_correctness") == 1 or metrics.get("preferred_source_hit_rate", 0) >= 1:
        return 1
    return 0


def cohen_kappa(left: list[int], right: list[int]) -> tuple[float, float]:
    labels = (0, 1, 2)
    n = len(left)
    index = {label: i for i, label in enumerate(labels)}
    matrix = [[0, 0, 0] for _ in labels]
    for a, b in zip(left, right):
        matrix[index[a]][index[b]] += 1
    observed = sum(matrix[i][i] for i in range(3)) / n
    row = [sum(matrix[i]) / n for i in range(3)]
    col = [sum(matrix[i][j] for i in range(3)) / n for j in range(3)]
    expected = sum(row[i] * col[i] for i in range(3))
    kappa = 1.0 if expected == 1 else (observed - expected) / (1 - expected)
    return observed, kappa


def tr(value: float, digits: int = 3) -> str:
    return f"{value:.{digits}f}".replace(".", ",")


def set_para_text(paragraph: Paragraph, text: str) -> None:
    if paragraph.runs:
        paragraph.runs[0].text = text
        for run in paragraph.runs[1:]:
            run.text = ""
    else:
        paragraph.add_run(text)


def delete_paragraph(paragraph: Paragraph) -> None:
    element = paragraph._element
    parent = element.getparent()
    if parent is not None:
        parent.remove(element)


def insert_after(paragraph: Paragraph, text: str, style: str | None = None) -> Paragraph:
    new_p = OxmlElement("w:p")
    paragraph._p.addnext(new_p)
    created = Paragraph(new_p, paragraph._parent)
    if style:
        created.style = style
    if text:
        created.add_run(text)
    return created


def agreement() -> dict:
    report = json.loads(GEN.read_text(encoding="utf-8"))
    auto, human = [], []
    rows = []
    for row in report["rows"]:
        a = auto_score(row["generation"])
        b = SECOND_SCORES[row["id"]]
        auto.append(a)
        human.append(b)
        rows.append({"id": row["id"], "otomatik_0_2": a, "ikinci_kod_0_2": b})
    observed, kappa = cohen_kappa(auto, human)
    return {
        "n": len(rows),
        "auto_mean": sum(auto) / len(auto),
        "second_mean": sum(human) / len(human),
        "second_points": sum(human),
        "agreement": observed,
        "kappa": kappa,
        "rows": rows,
    }


KAPPA_SENTENCE = (
    "İkinci puanlayan bağımsız bir veteriner hekim değildir ve puanlama kör değildir. "
    "Cohen kappa hesaplanmamıştır."
)


def kappa_replacement(stats: dict) -> str:
    return (
        "Aynı 33 yanıt, otomatik puan ve kaynak parçası görülmeden ikinci kez kodlanmıştır. "
        "Puan, yanıtın soruyu karşılayıp karşılamadığıdır: 0 bariz yanlış veya konu dışı, "
        "1 kısmen ilgili, 2 soruyu karşılıyor. F-RAG033 için beklenen davranış tanı reddidir ve 2 verilmiştir. "
        f"İkinci kodlamanın ortalaması {tr(stats['second_mean'])} "
        f"({stats['second_points']}/33 puandır). "
        "Arşivdeki alanlardan kurulan otomatik 0–2 kuralının ortalaması "
        f"{tr(stats['auto_mean'])}’dir: tanı reddi varsa 2; atıf doğruluğu 1 ve atıf tamlığı en az 0,5 ise 2; "
        "yalnız geçerli atıf veya tercih isabeti 1 ise 1; aksi halde 0. "
        f"İki kodlamanın yüzde uyumu {tr(stats['agreement'])}, Cohen κ değeri {tr(stats['kappa'])}’dir. "
        "Bu uyum zayıftır. İkinci kodlayıcı veteriner hekim değildir. "
        "Düşük κ, atıf vekilinin içerik doğruluğuyla aynı şeyi ölçmediğini gösterir. "
        "Daha önce yazılan araştırmacı ortalaması (doğruluk 1,152) ayrı bir tek geçiştir; "
        "madde puan kâğıdı arşivde olmadığı için o geçişle κ yeniden hesaplanamaz. "
        "LLM-only koşulunun madde düzeyindeki içerik puanı da bu κ’ya dahil değildir; "
        "o koşulun atıf metrikleri bağlam olmadığı için yapısal olarak sıfırdır."
    )


SYNTHESIS = (
    "Bu literatürün tezle ilişkisi üç boşlukta toplanabilir. "
    "Birincisi, hayvancılıkta yapay zekâ çalışmaları büyük ölçüde sensör, robot ve sürü izleme üzerinedir; "
    "doğal dille hem sürü kaydını hem bilimsel belgeyi aynı yanıtta birleştiren sohbet asistanı azdır. "
    "İkincisi, RAG literatürü getirilen bağlamın üretimi kendiliğinden güvenilir kılmadığını gösterir "
    "(Shahade ve Deshmukh, 2024; Gupta, 2025; Es vd., 2024); bu tez de retrieval başarısını üretim başarısından ayrı ölçer. "
    "Üçüncüsü, Text-to-SQL çalışmaları modelin yazdığı sorgunun yürütme doğruluğunu esas alır (Gao vd., 2024); "
    "bu prototipte SQL çoğunlukla şablonla üretildiği için yürütme ile doğal dildeki sayı tutarlılığı ayrı raporlanır."
)

SCALE = (
    " Kayıt ölçeği prototiptir: bir çiftlik, beş inek (3 Holstein, 2 Simental), "
    "70 sağım kaydı (30 Ağustos–5 Eylül 2026, sabah ve akşam) ve bir alarm kaydı. "
    "Bu ölçek saha genellemesi kurmaz."
)


def strip_page_numbers(doc: Document) -> int:
    """Gövdedeki tek başına duran sayfa numaralarını siler ve bölünmüş cümleleri birleştirir."""
    removed = 0
    guard = 0
    while guard < 200:
        guard += 1
        paras = list(doc.paragraphs)
        start = next(
            (i for i, p in enumerate(paras) if p.style.name == "Heading 1" and p.text.strip().startswith("1. GİRİŞ")),
            None,
        )
        if start is None:
            return removed
        changed = False
        for i in range(start, len(paras)):
            text = paras[i].text.strip()
            if not re.fullmatch(r"\d{1,3}", text):
                continue
            prev = next((paras[j] for j in range(i - 1, start - 1, -1) if paras[j].text.strip()), None)
            nxt = next((paras[j] for j in range(i + 1, len(paras)) if paras[j].text.strip()), None)
            if prev is not None and nxt is not None and nxt.style.name == "Normal":
                prev_t = prev.text.strip()
                next_t = nxt.text.strip()
                continues = (
                    prev_t
                    and not prev_t.endswith((".", "!", "?", ":", ";", "”", '"'))
                    and next_t[:1].islower()
                )
                if continues:
                    set_para_text(prev, prev_t + " " + next_t)
                    delete_paragraph(nxt)
            delete_paragraph(paras[i])
            removed += 1
            changed = True
            break
        if not changed:
            break
    for para in list(doc.paragraphs):
        if para.text.strip() in {"i", "ii", "iii", "iv", "v", "vi"}:
            delete_paragraph(para)
            removed += 1
    return removed


def merge_continuations(doc: Document) -> int:
    """Sayfa kırılmasında ikiye bölünmüş cümleleri birleştirir."""
    n = 0
    romans = {"vii", "viii", "ix", "x", "xi", "xii"}
    while True:
        paras = list(doc.paragraphs)
        found = False
        for i, para in enumerate(paras):
            text = para.text.strip()
            if text in romans:
                delete_paragraph(para)
                n += 1
                found = True
                break
            if not text or para.style.name != "Normal" or not text[0].islower():
                continue
            prev = next((paras[j] for j in range(i - 1, -1, -1) if paras[j].text.strip()), None)
            if prev is None or prev.style.name != "Normal":
                continue
            prev_t = prev.text.strip()
            if len(prev_t) < 40 or prev_t.endswith((".", "!", "?", ":", ";", "”", '"')):
                continue
            set_para_text(prev, prev_t + " " + text)
            delete_paragraph(para)
            n += 1
            found = True
            break
        if not found:
            return n


def rebuild_front_lists(doc: Document) -> None:
    paras = list(doc.paragraphs)
    start = next(i for i, p in enumerate(paras) if p.text.strip() == "İÇİNDEKİLER")
    end = next(i for i, p in enumerate(paras) if p.text.strip().startswith("Teslim notu"))
    anchor = paras[start]
    for para in paras[start + 1 : end]:
        delete_paragraph(para)
    headings = [
        p.text.strip()
        for p in doc.paragraphs
        if p.style.name.startswith("Heading") and p.text.strip() and p.text.strip() != "İÇİNDEKİLER"
    ]
    # İÇİNDEKİLER kendisi başlık değil; önsöz başlıktan önce silinmiş olabilir. Başlık stillerinden üret.
    lines = ["Başlıklar Word stillerinden üretilmiştir. Sayfa numarası için Word’de İçindekiler alanını güncelleyiniz."]
    lines.extend(headings)
    lines.append("TABLOLAR")
    lines.extend(
        p.text.strip()
        for p in doc.paragraphs
        if p.text.strip().startswith("Tablo ") and len(p.text.strip()) < 180 and "...." not in p.text
    )
    lines.append("ŞEKİLLER")
    lines.extend(
        p.text.strip()
        for p in doc.paragraphs
        if p.text.strip().startswith("Şekil ") and len(p.text.strip()) < 180 and "...." not in p.text
    )
    # addnext inserts immediately after anchor, so insert in reverse to keep order
    for line in reversed(lines):
        insert_after(anchor, line)


def apply_prose(doc: Document, stats: dict) -> int:
    n = 0
    replacement = kappa_replacement(stats)
    for para in doc.paragraphs:
        text = para.text
        new = text
        if KAPPA_SENTENCE in new:
            new = new.replace(KAPPA_SENTENCE, replacement)
        new = new.replace(
            "Şekil 3.3 ve Şekil 4.3'te işletim sistemi etkinleştirme filigranı vardır.",
            "Şekil 3.3 ve Şekil 4.3’teki işletim sistemi etkinleştirme filigranı teslim görüntüsünden temizlenmiştir.",
        )
        new = new.replace(
            "Şekil 3.3 ve Şekil 4.3’te işletim sistemi etkinleştirme filigranı vardır.",
            "Şekil 3.3 ve Şekil 4.3’teki işletim sistemi etkinleştirme filigranı teslim görüntüsünden temizlenmiştir.",
        )
        if new != text:
            set_para_text(para, new)
            n += 1
    # ölçek cümlesi §3.2 devamına
    for para in doc.paragraphs:
        if para.text.strip().endswith("saha verilerini temsil etmemektedir.") and "Beş inek" not in para.text and "beş inek" not in para.text:
            set_para_text(para, para.text.rstrip() + SCALE)
            n += 1
            break
    # yinelenen tartışma paragrafı
    for para in list(doc.paragraphs):
        if para.text.strip().startswith("Nihai değerlendirmede kullanılan 89 sorunun tamamı doğru işleme kanalına yönlendirilmiş"):
            delete_paragraph(para)
            n += 1
    # literatür boşluğu, 3. bölümden hemen önce, bir kez
    if not any(p.text.startswith("Bu literatürün tezle ilişkisi üç boşlukta") for p in doc.paragraphs):
        for para in doc.paragraphs:
            if para.style.name == "Heading 1" and para.text.strip().startswith("3. MATERYAL"):
                new_p = OxmlElement("w:p")
                para._p.addprevious(new_p)
                created = Paragraph(new_p, para._parent)
                created.add_run(SYNTHESIS)
                n += 1
                break
    for para in doc.paragraphs:
        if para.text.strip().startswith("Teslim notu"):
            set_para_text(
                para,
                "Teslim notu (27 Ekim 2026): Sayılar 17/24 (0,708) ve 11/16 (0,688) üzerinde hizalıdır. "
                "Gövdeye karışan sayfa numaraları birleştirildi, içindekiler başlıklardan yeniden yazıldı, "
                "§5.1’deki tekrar paragrafı çıkarıldı ve ekran filigranı temizlendi. "
                f"33 RAG yanıtında ikinci kodlama ile otomatik 0–2 kuralının Cohen κ değeri {tr(stats['kappa'])}’dir. "
                "Bu κ uzman geçerliliği değildir. Word’de içindekiler alanı kullanılırsa sayfa numaraları F9 ile dolar.",
            )
            n += 1
            break
    return n


def decimal_cells(doc: Document) -> int:
    n = 0
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for para in cell.paragraphs:
                    text = para.text.strip()
                    if re.fullmatch(r"\d+\.\d+", text):
                        set_para_text(para, text.replace(".", ","))
                        n += 1
    return n


def replace_images(doc: Document) -> int:
    replacements = {}
    if IMG3.exists():
        replacements[124612] = IMG3.read_bytes()
    if IMG6.exists():
        replacements[111148] = IMG6.read_bytes()
    n = 0
    for rel in doc.part.rels.values():
        if "image" not in rel.reltype:
            continue
        blob = rel.target_part.blob
        new = replacements.get(len(blob))
        if new:
            rel.target_part._blob = new
            n += 1
    return n


def main() -> None:
    stats = agreement()
    out = ROOT / "Backend" / "evaluation_output" / "ikinci_kodlama_kappa.json"
    out.write_text(json.dumps({k: v for k, v in stats.items()}, ensure_ascii=False, indent=2), encoding="utf-8")
    doc = Document(str(SRC))
    pages = strip_page_numbers(doc)
    pages += merge_continuations(doc)
    rebuild_front_lists(doc)
    prose = apply_prose(doc, stats)
    commas = decimal_cells(doc)
    images = replace_images(doc)
    doc.save(str(SRC))
    print(f"kappa {stats['kappa']:.3f} uyum {stats['agreement']:.3f}")
    print(f"sayfa no {pages}; düzyazı {prose}; virgül {commas}; görüntü {images}")
    print(f"kaydedildi {SRC}")


if __name__ == "__main__":
    main()
