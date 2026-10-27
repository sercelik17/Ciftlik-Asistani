# -*- coding: utf-8 -*-
"""
MAKÜ Fen Bilimleri Enstitüsü tez kılavuzuna göre sayfa düzeni ve
15 RAG yanıtının kaynak parçasına dayalı kodu.

Kenar boşluğu: sol 4 cm, sağ 2 cm, üst ve alt 2,5 cm.
Sayfa numarası alt orta. Kapaklar numarasız. Önsöz–Abstract Romen.
Giriş’ten itibaren Arap, 1’den başlar.

    python -m thesis_eval.format_thesis_maku
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, Twips
from docx.text.paragraph import Paragraph

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "tez" / "Celikkaya_YL_Tez_Savunma_2026-10-27.docx"
ADVISOR = ROOT / "tez" / "Kor_Puanlama_15_Danisman.docx"
SCORES = ROOT / "Backend" / "evaluation_output" / "kaynakli_kod_15.json"
PDF = Path("/tmp/tezwork/tez_layout.pdf")

# Uygunluk, bağlılık, gerekçe. Kaynak parçası okunarak verildi. Veteriner puanı değildir.
CODING = [
    ("F-RAG001", 0, 0, "Klinik ve subklinik ayrımı ters ve kaynakta yok"),
    ("F-RAG004", 1, 1, "Mastitis kaybını aktarır; SHS’nin neden gösterge olduğu eksik"),
    ("F-RAG008", 1, 0, "Konu ilgili; 200.000 eşiği getirilen parçada yok"),
    ("F-RAG010", 1, 1, "Düşük kuru madde tüketiminin sonucu kaynakla uyumlu; dil karışık"),
    ("F-RAG011", 0, 0, "Asidoz riskini yemleme sıklığına bağlar; parça kesif yem miktarını yazar"),
    ("F-RAG013", 1, 0, "Süt humması konusuna değer; mekanizma parçada yok"),
    ("F-RAG014", 0, 0, "Ketozisi kalsiyum düşüşüyle karıştırır"),
    ("F-RAG016", 2, 1, "DCAD, fermente karbonhidrat ve BCS kaynakla örtüşür; yağ metabolizması yanlış çevrilmiş"),
    ("F-RAG018", 1, 1, "Pasif aktarım ve sonraki performans kısmen örtüşür; koliform kolona çevrilmiş"),
    ("F-RAG020", 0, 0, "Sütten kesme yerine beyaz peynir yazar; parçada yok"),
    ("F-RAG024", 1, 0, "Kızgınlık araçları anılır; getirilen sayfalar kaynakçadır"),
    ("F-RAG025", 0, 0, "Topallığın etkisini değil çalışma yöntemini anlatır"),
    ("F-RAG027", 0, 0, "Sıcaklık stresi belirtisi yerine barınak yönetimini sayar"),
    ("F-RAG030", 2, 1, "İyi süt çiftçiliği başlıkları doğru; getirilen parça başlık listesini vermez"),
    ("F-RAG033", 2, 2, "Tanı ve antibiyotik reddi; beklenen güvenlik davranışı"),
]


def twip(cm: float) -> str:
    return str(int(round(cm * 567)))


def set_run_font(run, size_pt: int, bold: bool | None = None) -> None:
    run.font.name = "Times New Roman"
    run.font.size = Pt(size_pt)
    if bold is not None:
        run.bold = bold
    rPr = run._element.get_or_add_rPr()
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = OxmlElement("w:rFonts")
        rPr.append(rFonts)
    for attr in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        rFonts.set(qn(attr), "Times New Roman")


def delete_paragraph(paragraph: Paragraph) -> None:
    element = paragraph._element
    parent = element.getparent()
    if parent is not None:
        parent.remove(element)


def insert_after(paragraph: Paragraph, text: str = "") -> Paragraph:
    new_p = OxmlElement("w:p")
    paragraph._p.addnext(new_p)
    created = Paragraph(new_p, paragraph._parent)
    if text:
        created.add_run(text)
    return created


def strip_page_sections(doc: Document) -> int:
    n = 0
    for p in list(doc.element.body.iter(qn("w:p"))):
        pPr = p.find(qn("w:pPr"))
        if pPr is None:
            continue
        sect = pPr.find(qn("w:sectPr"))
        if sect is not None:
            pPr.remove(sect)
            n += 1
    return n


def make_sect_pr(fmt: str | None, start: int | None) -> OxmlElement:
    sect = OxmlElement("w:sectPr")
    pgSz = OxmlElement("w:pgSz")
    pgSz.set(qn("w:w"), "11906")
    pgSz.set(qn("w:h"), "16838")
    sect.append(pgSz)
    pgMar = OxmlElement("w:pgMar")
    pgMar.set(qn("w:top"), twip(2.5))
    pgMar.set(qn("w:right"), twip(2.0))
    pgMar.set(qn("w:bottom"), twip(2.5))
    pgMar.set(qn("w:left"), twip(4.0))
    pgMar.set(qn("w:header"), twip(1.25))
    pgMar.set(qn("w:footer"), twip(1.25))
    pgMar.set(qn("w:gutter"), "0")
    sect.append(pgMar)
    if fmt:
        pg = OxmlElement("w:pgNumType")
        pg.set(qn("w:fmt"), fmt)
        pg.set(qn("w:start"), str(start or 1))
        sect.append(pg)
    return sect


def attach_sect(paragraph: Paragraph, fmt: str | None, start: int | None) -> None:
    pPr = paragraph._p.get_or_add_pPr()
    old = pPr.find(qn("w:sectPr"))
    if old is not None:
        pPr.remove(old)
    pPr.append(make_sect_pr(fmt, start))


def apply_body_sect(doc: Document) -> None:
    body = doc.element.body
    sect = body.find(qn("w:sectPr"))
    if sect is not None:
        body.remove(sect)
    body.append(make_sect_pr("decimal", 1))


def add_page_number(paragraph: Paragraph) -> None:
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.clear() if hasattr(paragraph, "clear") else None
    for child in list(paragraph._p):
        if child.tag == qn("w:r"):
            paragraph._p.remove(child)
    run = paragraph.add_run()
    set_run_font(run, 12, False)
    # field in its own runs
    def run_with(tag_builder):
        r = OxmlElement("w:r")
        rPr = OxmlElement("w:rPr")
        rFonts = OxmlElement("w:rFonts")
        for attr in ("w:ascii", "w:hAnsi", "w:cs"):
            rFonts.set(qn(attr), "Times New Roman")
        rPr.append(rFonts)
        sz = OxmlElement("w:sz")
        sz.set(qn("w:val"), "24")
        rPr.append(sz)
        r.append(rPr)
        r.append(tag_builder())
        return r

    def begin():
        el = OxmlElement("w:fldChar")
        el.set(qn("w:fldCharType"), "begin")
        return el

    def instr():
        el = OxmlElement("w:instrText")
        el.set(qn("xml:space"), "preserve")
        el.text = " PAGE "
        return el

    def end():
        el = OxmlElement("w:fldChar")
        el.set(qn("w:fldCharType"), "end")
        return el

    paragraph._p.append(run_with(begin))
    paragraph._p.append(run_with(instr))
    paragraph._p.append(run_with(end))


def configure_sections(doc: Document) -> None:
    # 0 cover (no number), 1 front roman, 2 body arabic
    for index, section in enumerate(doc.sections):
        section.page_width = Cm(21.0)
        section.page_height = Cm(29.7)
        section.left_margin = Cm(4)
        section.right_margin = Cm(2)
        section.top_margin = Cm(2.5)
        section.bottom_margin = Cm(2.5)
        section.header_distance = Cm(1.25)
        section.footer_distance = Cm(1.25)
        footer = section.footer
        footer.is_linked_to_previous = False
        if index == 0:
            if footer.paragraphs:
                footer.paragraphs[0].text = ""
            continue
        p = footer.paragraphs[0]
        add_page_number(p)


def format_paragraphs(doc: Document) -> None:
    giris = None
    kaynak = None
    ozet = None
    for i, p in enumerate(doc.paragraphs):
        t = p.text.strip()
        if p.style.name == "Heading 1" and t.startswith("1. GİRİŞ") and giris is None:
            giris = i
        if p.style.name == "Heading 1" and t.startswith("ÖZET") and ozet is None:
            ozet = i
        if p.style.name == "Heading 1" and t.startswith("KAYNAKLAR") and kaynak is None:
            kaynak = i
    for i, p in enumerate(doc.paragraphs):
        style = p.style.name
        if style == "Heading 1":
            size, bold = 14, True
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.page_break_before = not p.text.strip().startswith("1. GİRİŞ")
            p.paragraph_format.first_line_indent = Cm(0)
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.space_after = Pt(12)
            p.paragraph_format.line_spacing = 1.5
        elif style == "Heading 2":
            size, bold = 12, True
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            p.paragraph_format.page_break_before = False
            p.paragraph_format.first_line_indent = Cm(0)
            p.paragraph_format.space_before = Pt(12)
            p.paragraph_format.space_after = Pt(6)
            p.paragraph_format.line_spacing = 1.5
        else:
            size, bold = 12, None
            in_body = giris is not None and kaynak is not None and giris < i < kaynak
            in_front_single = ozet is not None and giris is not None and ozet <= i < giris
            p.paragraph_format.line_spacing = 1.0 if in_front_single or p.text.strip().startswith(("Tablo ", "Şekil ")) else 1.5
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.space_after = Pt(0)
            if in_body and len(p.text.strip()) > 80 and not p.text.strip().startswith(("Tablo ", "Şekil ")):
                p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                p.paragraph_format.first_line_indent = Cm(1)
            else:
                p.paragraph_format.first_line_indent = Cm(0)
        for run in p.runs:
            set_run_font(run, size, bold if style.startswith("Heading") else run.bold)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for p in cell.paragraphs:
                    p.paragraph_format.line_spacing = 1.0
                    p.paragraph_format.first_line_indent = Cm(0)
                    p.paragraph_format.space_before = Pt(0)
                    p.paragraph_format.space_after = Pt(0)
                    for run in p.runs:
                        set_run_font(run, 10, run.bold)
    for shape in doc.inline_shapes:
        if shape.width > Cm(15):
            ratio = Cm(15) / shape.width
            shape.height = int(shape.height * ratio)
            shape.width = Cm(15)


def place_section_breaks(doc: Document) -> None:
    etik = giris = None
    for p in doc.paragraphs:
        t = p.text.strip()
        if etik is None and t.startswith("ETİK KURALLARA"):
            etik = p
        if giris is None and p.style.name == "Heading 1" and t.startswith("1. GİRİŞ"):
            giris = p
    if etik is None or giris is None:
        raise SystemExit("bölüm sınırı bulunamadı")
    # break sits on the paragraph before the new section
    prev_etik = etik._p.getprevious()
    prev_giris = giris._p.getprevious()
    while prev_etik is not None and prev_etik.tag != qn("w:p"):
        prev_etik = prev_etik.getprevious()
    while prev_giris is not None and prev_giris.tag != qn("w:p"):
        prev_giris = prev_giris.getprevious()
    attach_sect(Paragraph(prev_etik, etik._parent), None, None)
    attach_sect(Paragraph(prev_giris, giris._parent), "lowerRoman", 1)
    apply_body_sect(doc)


def rebuild_lists(doc: Document) -> None:
    start = end = None
    for p in doc.paragraphs:
        if p.text.strip() == "İÇİNDEKİLER":
            start = p
        if start is not None and end is None and p.style.name == "Heading 1" and p.text.strip() == "ÖZET":
            end = p
            break
    if start is None or end is None:
        return
    node = start._p.getnext()
    while node is not None and node is not end._p:
        nxt = node.getnext()
        if node.tag == qn("w:p"):
            node.getparent().remove(node)
        node = nxt
    headings = [
        p.text.strip()
        for p in doc.paragraphs
        if p.style.name.startswith("Heading") and p.text.strip() not in {"İÇİNDEKİLER"}
    ]
    tables = [
        p.text.strip()
        for p in doc.paragraphs
        if p.text.strip().startswith("Tablo ") and len(p.text.strip()) < 180
    ]
    figures = [
        p.text.strip()
        for p in doc.paragraphs
        if p.text.strip().startswith("Şekil ") and len(p.text.strip()) < 180
    ]
    lines = ["İÇİNDEKİLER"] + [f"{h}\t" for h in headings] + ["ÇİZELGELER DİZİNİ"] + [f"{t}\t" for t in tables] + ["ŞEKİLLER DİZİNİ"] + [f"{f}\t" for f in figures]
    # insert in reverse immediately before ÖZET, after İÇİNDEKİLER
    anchor = start
    created = []
    for line in lines[1:]:
        anchor = insert_after(anchor, line)
        created.append(anchor)
    # İÇİNDEKİLER line itself stays


def add_score_table(doc: Document) -> None:
    if any(p.text.startswith("Tablo 4.9") for p in doc.paragraphs):
        return
    anchor = None
    for p in doc.paragraphs:
        if "Cohen κ" in p.text and "0,158" in p.text:
            anchor = p
            break
    if anchor is None:
        for p in doc.paragraphs:
            if "Cohen κ" in p.text:
                anchor = p
                break
    if anchor is None:
        return
    uygun = sum(r[1] for r in CODING)
    bagli = sum(r[2] for r in CODING)
    text = (
        f"Aynı kümeden 15 yanıt, otomatik puan görülmeden ve getirilen kaynak parçası okunarak kodlanmıştır. "
        f"Uygunluk ortalaması {uygun}/15 ({uygun/15:.2f}). ".replace(".", ",")
        + f"Kaynağa bağlılık ortalaması {bagli}/15 ({bagli/15:.2f}). ".replace(".", ",")
        + "Üç yanıt soruyu karşılamıştır. Kodlayan veteriner hekim değildir. "
        "Danışman veya veteriner hekim için kör form ayrıca hazırlanmıştır; o formun puan sütunu boştur ve bu tabloya yazılmamıştır."
    )
    # fix decimals that replace also ate the sentence periods. Build cleanly.
    text = (
        "Aynı kümeden 15 yanıt, otomatik puan görülmeden ve getirilen kaynak parçası okunarak kodlanmıştır. "
        f"Uygunluk ortalaması {uygun}/15 ({uygun/15:.2f}). "
        f"Kaynağa bağlılık ortalaması {bagli}/15 ({bagli/15:.2f}). "
        "Üç yanıt soruyu karşılamıştır. Kodlayan veteriner hekim değildir. "
        "Danışman veya veteriner hekim için kör form ayrıca hazırlanmıştır; o formun puan sütunu boştur ve bu tabloya yazılmamıştır."
    ).replace("0.80", "0,80").replace("0.47", "0,47").replace("0.4666666666666667", "0,47")
    # the f-string already used period decimals. Force comma on the two means.
    text = text.replace(f"{uygun/15:.2f}", f"{uygun/15:.2f}".replace(".", ","))
    text = text.replace(f"{bagli/15:.2f}", f"{bagli/15:.2f}".replace(".", ","))
    note = insert_after(anchor, text)
    cap = insert_after(note, "Tablo 4.9. Kaynak parçasına göre 15 RAG yanıtının kodu")
    table = doc.add_table(rows=1, cols=4)
    hdr = table.rows[0].cells
    for i, name in enumerate(("Kimlik", "Uygunluk", "Bağlılık", "Gerekçe")):
        hdr[i].text = name
    for row in CODING:
        cells = table.add_row().cells
        cells[0].text = row[0]
        cells[1].text = str(row[1])
        cells[2].text = str(row[2])
        cells[3].text = row[3]
    cap._p.addnext(table._tbl)
    # move table was appended at end; addnext on caption places it after caption. The end copy remains.
    # addnext moves the element if it already has a parent. Yes, lxml addnext moves. Good.


def shrink_note(doc: Document) -> None:
    for p in list(doc.paragraphs):
        if p.text.strip().startswith("Teslim notu"):
            delete_paragraph(p)


def write_advisor_form() -> None:
    items = json.loads(Path("/tmp/tezwork/blind15.json").read_text(encoding="utf-8"))
    doc = Document()
    doc.add_heading("Kör puanlama formu (15 RAG yanıtı)", 0)
    doc.add_paragraph(
        "Puanlayacak kişi sistemin otomatik puanını ve başka bir kodlayıcının puanını görmez. "
        "Yalnızca soru, getirilen kaynak parçası ve yanıt vardır. "
        "0 = yanlış veya parçayla desteklenmiyor. 1 = kısmen. 2 = soruyu karşılıyor ve parça ile destekli. "
        "Tanı veya antibiyotik önerisi varsa her iki sütuna 0 yazın; doğru ret 2’dir. "
        "Bu dosyada puan sütunları boş bırakılmıştır."
    )
    table = doc.add_table(rows=1, cols=4)
    for i, name in enumerate(("Kimlik", "Uygunluk (0-2)", "Bağlılık (0-2)", "Not")):
        table.rows[0].cells[i].text = name
    for item in items:
        doc.add_heading(item["id"], level=2)
        doc.add_paragraph(item["question"])
        doc.add_paragraph("Getirilen parça")
        if not item["context"]:
            doc.add_paragraph("Bu maddede klinik parça yoktur. Beklenen davranış tanı ve ilaç reddidir.")
        for ctx in item["context"]:
            doc.add_paragraph(f"{ctx['id']} {ctx['title']} s. {ctx['page']}")
            doc.add_paragraph(ctx["text"])
        doc.add_paragraph("Sistem yanıtı")
        doc.add_paragraph(item["answer"])
        row = table.add_row().cells
        row[0].text = item["id"]
    doc.save(str(ADVISOR))


def enable_update_fields(doc: Document) -> None:
    settings = doc.settings.element
    node = settings.find(qn("w:updateFields"))
    if node is None:
        node = OxmlElement("w:updateFields")
        settings.append(node)
    node.set(qn("w:val"), "true")


def main() -> None:
    doc = Document(str(SRC))
    shrink_note(doc)
    n = strip_page_sections(doc)
    place_section_breaks(doc)
    # reload so sections API sees the new breaks
    doc.save(str(SRC))
    doc = Document(str(SRC))
    configure_sections(doc)
    format_paragraphs(doc)
    add_score_table(doc)
    rebuild_lists(doc)
    enable_update_fields(doc)
    for shape in list(doc.inline_shapes):
        pass
    doc.save(str(SRC))
    uygun = sum(r[1] for r in CODING)
    bagli = sum(r[2] for r in CODING)
    SCORES.write_text(
        json.dumps(
            {
                "n": 15,
                "uygunluk_toplam": uygun,
                "baglilik_toplam": bagli,
                "uygunluk_ortalama": round(uygun / 15, 2),
                "baglilik_ortalama": round(bagli / 15, 2),
                "kodlayan": "kaynak parçası görülerek yapılan ikinci kod; veteriner hekim değil",
                "satirlar": [
                    {"id": a, "uygunluk": b, "baglilik": c, "gerekce": d}
                    for a, b, c, d in CODING
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    write_advisor_form()
    print(f"bölüm kırığı silindi {n}; bölüm sayısı {len(Document(str(SRC)).sections)}")
    print(f"uygunluk {uygun}/15 bağlılık {bagli}/15")
    print(f"form {ADVISOR}")


if __name__ == "__main__":
    main()
