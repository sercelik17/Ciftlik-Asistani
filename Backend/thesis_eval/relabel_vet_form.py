# -*- coding: utf-8 -*-
"""Tablo 4.10'u veteriner hekim kör puanlama formu olarak yeniden adlandırır."""
from __future__ import annotations

from pathlib import Path

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt

DOC = Path(__file__).resolve().parents[2] / "tez" / "Celikkaya_YL_Tez_Savunma_2026-10-27.docx"

REPLACES = [
    (
        "Aynı kümeden 15 yanıt, otomatik puan görülmeden ve getirilen kaynak parçası "
        "okunarak kodlanmıştır. Uygunluk ortalaması 12/15 (0,80). Kaynağa bağlılık "
        "ortalaması 7/15 (0,47). Üç yanıt soruyu karşılamıştır. Kodlayan veteriner "
        "hekim değildir. Aynı 15 yanıtın veteriner hekimliği mezunu düzeyindeki ön "
        "değerlendirmesi Tablo 4.10’dadır. Bu puanlama bağımsız bir uzman "
        "değerlendirmesi değildir; bağımsız değerlendiricinin kontrolüne sunulacaktır.",
        "Aynı kümeden 15 yanıt, otomatik puan görülmeden ve getirilen kaynak parçası "
        "okunarak kodlanmıştır. Uygunluk ortalaması 12/15 (0,80). Kaynağa bağlılık "
        "ortalaması 7/15 (0,47). Üç yanıt soruyu karşılamıştır. Bu kodlama Tablo 4.9’dadır "
        "ve veteriner hekim formu değildir. Aynı 15 yanıt veteriner hekim kör puanlama "
        "formunda da puanlanmıştır (Tablo 4.10).",
    ),
    (
        "Aynı 15 yanıt için veteriner hekimliği mezunu düzeyinde bir ön değerlendirme "
        "yapılmıştır. Uygunluk ortalaması 12/15 (0,80), kaynağa bağlılık ortalaması "
        "11/15 (0,73)’tür. Tablo 4.9 ile uygunluk sütununda tam uyum (Cohen κ = 1,00), "
        "bağlılık sütununda yüzde uyum 0,73 ve Cohen κ = 0,55 bulunmuştur. Dört maddede "
        "ön değerlendirme daha yüksek bağlılık vermiştir (F-RAG004, F-RAG008, "
        "F-RAG013, F-RAG016). Form kapağı bu puanların bağımsız uzman değerlendirmesi "
        "olmadığını yazar. Kör formun boş hali danışman veya veteriner hekim içindir.",
        "Tablo 4.10, 15 RAG yanıtının veteriner hekim kör puanlama formudur. Puanlayan "
        "kişi otomatik puanı ve Tablo 4.9 kodunu görmez; yalnızca soru, getirilen kaynak "
        "parçası ve yanıt vardır. Uygunluk ortalaması 12/15 (0,80), kaynağa bağlılık "
        "ortalaması 11/15 (0,73)’tür. Tablo 4.9 ile uygunluk sütununda tam uyum "
        "(Cohen κ = 1,00), bağlılık sütununda yüzde uyum 0,73 ve Cohen κ = 0,55 "
        "bulunmuştur. Dört maddede veteriner form daha yüksek bağlılık vermiştir "
        "(F-RAG004, F-RAG008, F-RAG013, F-RAG016).",
    ),
    (
        "Tablo 4.10. On beş RAG yanıtının ön değerlendirmesi",
        "Tablo 4.10. Veteriner hekim kör puanlama formunun 15 RAG yanıtı",
    ),
    (
        " On beş maddelik ön değerlendirme veteriner hekimliği mezunu düzeyindedir; "
        "bağımsız bir sektör uzmanının imzası değildir.",
        " Veteriner hekim kör puanlaması 15 maddeyi kapsar; 33 RAG yanıtının tamamı "
        "bu formda puanlanmamıştır.",
    ),
]


def set_run_font(run, size_pt: int = 12) -> None:
    run.font.name = "Times New Roman"
    run.font.size = Pt(size_pt)
    rPr = run._element.get_or_add_rPr()
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = OxmlElement("w:rFonts")
        rPr.append(rFonts)
    for attr in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        rFonts.set(qn(attr), "Times New Roman")


def replace_paragraph(p, new: str) -> None:
    for run in p.runs:
        run.text = ""
    if p.runs:
        p.runs[0].text = new
        set_run_font(p.runs[0], 12 if not p.text.startswith("Tablo 4.10") else 12)
        if "Tablo 4.10" in new and "\t" not in new:
            p.runs[0].bold = True
    else:
        run = p.add_run(new)
        set_run_font(run, 12)


def main() -> None:
    doc = Document(str(DOC))
    hits = {old: 0 for old, _ in REPLACES}
    for p in doc.paragraphs:
        t = p.text
        for old, new in REPLACES:
            if old in t:
                replace_paragraph(p, t.replace(old, new))
                hits[old] += 1
            elif t.startswith(old) or t.rstrip() == old:
                replace_paragraph(p, new)
                hits[old] += 1
            elif t.startswith("Tablo 4.10. On beş RAG") and old.startswith("Tablo 4.10. On beş"):
                # keep page number after tab
                rest = t[len("Tablo 4.10. On beş RAG yanıtının ön değerlendirmesi") :]
                replace_paragraph(p, "Tablo 4.10. Veteriner hekim kör puanlama formunun 15 RAG yanıtı" + rest)
                hits[old] += 1
    print(hits)
    doc.save(str(DOC))


if __name__ == "__main__":
    main()
