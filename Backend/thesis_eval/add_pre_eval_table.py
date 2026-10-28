# -*- coding: utf-8 -*-
"""Tablo 4.10: 15 maddelik ön değerlendirmeyi teze dürüst çerçeveyle ekler."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT, WD_TAB_LEADER
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt
from docx.text.paragraph import Paragraph

ROOT = Path(__file__).resolve().parents[2]
DOC = ROOT / "tez" / "Celikkaya_YL_Tez_Savunma_2026-10-27.docx"
JSON = ROOT / "Backend" / "evaluation_output" / "on_degerlendirme_15.json"
PDF_SRC = Path(
    "/home/ubuntu/.cursor/projects/workspace/uploads/"
    "Kor_Puanlama_15_Danisman_On_Degerlendirme_d6cc.pdf"
)
PDF_DST = ROOT / "tez" / "Kor_Puanlama_15_On_Degerlendirme.pdf"

PARA_419 = (
    "Aynı kümeden 15 yanıt, otomatik puan görülmeden ve getirilen kaynak parçası "
    "okunarak kodlanmıştır. Uygunluk ortalaması 12/15 (0,80). Kaynağa bağlılık "
    "ortalaması 7/15 (0,47). Üç yanıt soruyu karşılamıştır. Kodlayan veteriner "
    "hekim değildir. Aynı 15 yanıtın veteriner hekimliği mezunu düzeyindeki ön "
    "değerlendirmesi Tablo 4.10’dadır. Bu puanlama bağımsız bir uzman "
    "değerlendirmesi değildir; bağımsız değerlendiricinin kontrolüne sunulacaktır."
)
PARA_410 = (
    "Aynı 15 yanıt için veteriner hekimliği mezunu düzeyinde bir ön değerlendirme "
    "yapılmıştır. Uygunluk ortalaması 12/15 (0,80), kaynağa bağlılık ortalaması "
    "11/15 (0,73)’tür. Tablo 4.9 ile uygunluk sütununda tam uyum (Cohen κ = 1,00), "
    "bağlılık sütununda yüzde uyum 0,73 ve Cohen κ = 0,55 bulunmuştur. Dört maddede "
    "ön değerlendirme daha yüksek bağlılık vermiştir (F-RAG004, F-RAG008, "
    "F-RAG013, F-RAG016). Form kapağı bu puanların bağımsız uzman değerlendirmesi "
    "olmadığını yazar. Kör formun boş hali danışman veya veteriner hekim içindir."
)
LIMIT_ADD = (
    " On beş maddelik ön değerlendirme veteriner hekimliği mezunu düzeyindedir; "
    "bağımsız bir sektör uzmanının imzası değildir."
)


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


def insert_after(element, text: str) -> Paragraph:
    new_p = OxmlElement("w:p")
    element.addnext(new_p)
    parent = element.getparent()
    created = Paragraph(new_p, parent)
    run = created.add_run(text)
    set_run_font(run, 12, False)
    created.paragraph_format.line_spacing = 1.5
    created.paragraph_format.space_before = Pt(0)
    created.paragraph_format.space_after = Pt(0)
    created.paragraph_format.first_line_indent = Cm(1)
    created.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    return created


def find_table_49(doc: Document):
    for table in doc.tables:
        first = table.rows[0].cells[0].text.strip().replace("\n", " ")
        if first == "Kimlik" and len(table.rows) == 16:
            second = table.rows[1].cells[0].text.strip()
            if second == "F-RAG001":
                return table
    raise SystemExit("Tablo 4.9 bulunamadı")


def main() -> None:
    data = json.loads(JSON.read_text(encoding="utf-8"))
    if PDF_SRC.exists():
        shutil.copyfile(PDF_SRC, PDF_DST)
    doc = Document(str(DOC))
    if any(p.text.startswith("Tablo 4.10") for p in doc.paragraphs):
        print("Tablo 4.10 zaten var")
        return

    for p in doc.paragraphs:
        t = p.text.strip()
        if t.startswith("Aynı kümeden 15 yanıt, otomatik puan görülmeden"):
            for run in p.runs:
                run.text = ""
            if p.runs:
                p.runs[0].text = PARA_419
            else:
                run = p.add_run(PARA_419)
                set_run_font(run, 12, False)
        if t.startswith("Ayrıca, RAG tarafından üretilen yanıtların doğruluk") and LIMIT_ADD.strip() not in t:
            extra = LIMIT_ADD
            if p.runs:
                p.runs[-1].text = (p.runs[-1].text or "") + extra
            else:
                p.add_run(extra)

    table49 = find_table_49(doc)
    note = insert_after(table49._tbl, PARA_410)
    cap = insert_after(note._p, "Tablo 4.10. On beş RAG yanıtının ön değerlendirmesi")
    cap.paragraph_format.first_line_indent = Cm(0)
    cap.alignment = WD_ALIGN_PARAGRAPH.LEFT
    for run in cap.runs:
        run.bold = True

    table = doc.add_table(rows=1, cols=4)
    hdr = table.rows[0].cells
    for i, name in enumerate(("Kimlik", "Uygunluk", "Bağlılık", "Not")):
        hdr[i].text = name
    for row in data["satirlar"]:
        cells = table.add_row().cells
        cells[0].text = row["id"]
        cells[1].text = str(row["uygunluk"])
        cells[2].text = str(row["baglilik"])
        cells[3].text = row["not"]
    for row in table.rows:
        for cell in row.cells:
            for p in cell.paragraphs:
                p.paragraph_format.line_spacing = 1.0
                p.paragraph_format.first_line_indent = Cm(0)
                for run in p.runs:
                    set_run_font(run, 10, run.bold)
    cap._p.addnext(table._tbl)

    # TOC: insert Tablo 4.10 after Tablo 4.9 line
    for p in doc.paragraphs:
        if p.text.startswith("Tablo 4.9.") and "\t" in p.text:
            line = insert_after(p._p, "Tablo 4.10. On beş RAG yanıtının ön değerlendirmesi\t")
            line.paragraph_format.first_line_indent = Cm(0)
            line.paragraph_format.line_spacing = 1.0
            line.alignment = WD_ALIGN_PARAGRAPH.LEFT
            break

    doc.save(str(DOC))
    print("yazıldı", DOC)


if __name__ == "__main__":
    main()
