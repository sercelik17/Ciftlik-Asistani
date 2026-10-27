# -*- coding: utf-8 -*-
"""
24 Ekim 2026 sonrası tez Word sürümünü teslim için hizalar.

Girdi: pdf2docx ile dönüştürülmüş tez (veya özgün .docx)
Çıktı: sayılar, terimler, tablo değerleri ve başlık stilleri düzeltilmiş .docx

    python -m thesis_eval.finalize_thesis_docx --src /tmp/tezwork/tez_from_pdf.docx
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.text.paragraph import Paragraph

DEFAULT_SRC = Path("/tmp/tezwork/tez_from_pdf.docx")
DEFAULT_DST = Path(__file__).resolve().parents[2] / "tez" / "Celikkaya_YL_Tez_Savunma_2026-10-27.docx"


def set_para_text(paragraph: Paragraph, text: str) -> None:
    if paragraph.runs:
        paragraph.runs[0].text = text
        for run in paragraph.runs[1:]:
            run.text = ""
    else:
        paragraph.add_run(text)


def apply_map(text: str) -> str:
    pairs = [
        ("ayrık final final", "ayrık final"),
        ("Accuracy 1.00", "Accuracy 1,00"),
        ("Macro-F1 1.00", "Macro-F1 1,00"),
        ("%95\nGA 0.96–1.00", "%95 GA 0,96–1,00"),
        ("GA 0.96–1.00", "GA 0,96–1,00"),
        ("artırılmış üretim ve geri alma (RAG)", "Geri Getirme Destekli Üretim (RAG)"),
        ("artırılmış üretim ve geri alma", "Geri Getirme Destekli Üretim"),
        ("artırılmış bilgi edinme yoluyla üretim (RAG)", "Geri Getirme Destekli Üretim (RAG)"),
        ("Bilgi Alma Çerçevesi (RAG) tabanlı bir Bilgi Alma çerçevesinde", "RAG çerçevesinde"),
        ("Bilgi Alma Çerçevesi (RAG)", "RAG"),
        ("Retrieval-Augmented Generation - Erişim Destekli Üretim", "Retrieval-Augmented Generation, RAG"),
        ("Retrieval-Augmented Generation - RAG", "Retrieval-Augmented Generation, RAG"),
        ("(Retrieval-Augmented Generation - RAG)", "(Retrieval-Augmented Generation, RAG)"),
        ("RAG (Retrieval-Augmented Generation - RAG)", "RAG"),
        ("LangChain ve RAG (Retrieval-Augmented Generation - RAG)", "LangChain ve RAG"),
        ("FAISS HNSW gibi çapraz kodlayıcılar kullanılarak yapılan geri alma sonrası yeniden sıralama",
         "FAISS HNSW (yaklaşık en yakın komşu indeksi) ve ayrı bir çapraz kodlayıcı ile yapılan yeniden sıralama"),
        ("SQL kanalında sayısal yanıtların tutarlılığı 0,63 iken, HYBRID kanalında uçtan uca başarı oranı 0,69",
         "SQL kanalında sayısal yanıt tutarlılığı 17/24 (0,708; Wilson %95 GA 0,51–0,85) iken, HYBRID kanalında uçtan uca başarı oranı 11/16 (0,688; Wilson %95 GA 0,44–0,86)"),
        ("SQL kanalında değerlerin ve varlıkların genel tutarlılığı 0,625 iken, hibrit kanal için genel başarı oranı 0,6875",
         "SQL kanalında değer ve varlık tutarlılığı 17/24 (0,708) iken, HYBRID uçtan uca oranı 11/16 (0,688)"),
        ("Daha önceki ana metindeki 15/24 (0,625) toplamı, bu satır sayımıyla değiştirilmiştir.",
         "Güncel ve bağlayıcı sayı 17/24 (0,708) olup Tablo 4.8 ile aynıdır."),
        ("HYBRID kanalının elde ettiği 0,6875'lik genel başarı oranı, farklı kaynaklardan bilgi sentezlenirken hataların ortaya çıkabileceğini göstermektedir",
         "HYBRID kanalının 11/16 (0,688) uçtan uca oranı, başarısız beş soruda tercih edilen belgenin retrieval listesine girmemesinden kaynaklanır; bu oran sentez doğruluğu değil, kaynak seçimi ölçüsüdür"),
        ("yapay zeka tabanlı", "yapay zekâ tabanlı"),
        ("Yapay zeka tabanlı", "Yapay zekâ tabanlı"),
        ("yapay zeka ve", "yapay zekâ ve"),
        ("Üretken yapay zeka", "Üretken yapay zekâ"),
        ("alanında yapay zeka uygulamaları", "alanında yapay zekâ uygulamaları"),
        ("geliştirilen yapay zeka tabanlı", "geliştirilen yapay zekâ tabanlı"),
        ("sağlayan, yapay zeka tabanlı", "sağlayan, yapay zekâ tabanlı"),
        ("routing precision", "yönlendirme kesinliği"),
        ("held-out", "ayrık final"),
        ("Security smoke", "güvenlik duman testi"),
        ("Pref. kaynak", "tercih edilen kaynak"),
        ("Route acc.", "yönlendirme doğruluğu"),
    ]
    for old, new in pairs:
        text = text.replace(old, new)
    text = re.sub(r"\bYapay zeka\b", "Yapay zekâ", text)
    text = re.sub(r"\byapay zeka\b", "yapay zekâ", text)
    return text


def rewrite_cells_and_paragraphs(doc: Document) -> int:
    n = 0
    for para in doc.paragraphs:
        old = para.text
        new = apply_map(old)
        if new != old:
            set_para_text(para, new)
            n += 1
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for para in cell.paragraphs:
                    old = para.text
                    new = apply_map(old)
                    if new != old:
                        set_para_text(para, new)
                        n += 1
    return n


def fix_result_tables(doc: Document) -> int:
    n = 0
    for table in doc.tables:
        blob = " ".join(c.text for r in table.rows for c in r.cells)
        if "Sayısal yanıt tutarlılığı" in blob and "0,63" in blob:
            for row in table.rows:
                if "Sayısal" in row.cells[0].text:
                    row.cells[1].text = "0,708 (17/24)"
                    n += 1
                if "Uçtan uca" in row.cells[0].text:
                    row.cells[2].text = "0,688 (11/16)"
                    n += 1
        if "E2E / değer" in blob and "0,625" in blob:
            for row in table.rows:
                if row.cells[0].text.strip().startswith("SQL"):
                    row.cells[3].text = "0,708 (17/24)"
                    n += 1
                if row.cells[0].text.strip().startswith("HYBRID"):
                    row.cells[3].text = "0,688 (11/16)"
                    n += 1
    return n


BODY_H1 = {
    "1. GİRİŞ",
    "2. KAVRAMSAL ÇERÇEVE VE LİTERATÜR TARAMASI",
    "3. MATERYAL VE YÖNTEM",
    "4. BULGULAR",
    "5. SONUÇ VE ÖNERİLER",
    "KAYNAKLAR",
    "EKLER",
    "ÖNSÖZ",
    "ÖZET",
    "ABSTRACT",
}

H2_RE = re.compile(
    r"^(1\.[1-4]|2\.[1-7]|3\.[1-8]|4\.[1-4]|5\.[1-3])\.?\s+\S"
)


def style_headings(doc: Document) -> int:
    n = 0
    passed_abstract = False
    for para in doc.paragraphs:
        t = para.text.strip()
        if t.startswith("ABSTRACT"):
            passed_abstract = True
        if not passed_abstract and t not in {"ÖNSÖZ", "ÖZET", "ABSTRACT", "İÇİNDEKİLER"}:
            continue
        if t in BODY_H1 or t.rstrip(".") in BODY_H1:
            try:
                para.style = "Heading 1"
                n += 1
            except Exception:
                pass
            continue
        if passed_abstract and H2_RE.match(t) and "...." not in t and len(t) < 120:
            try:
                para.style = "Heading 2"
                n += 1
            except Exception:
                pass
    return n


def insert_note_after_ozet_title(doc: Document) -> None:
    for para in doc.paragraphs:
        if para.text.strip() == "ÖZET":
            new_p = OxmlElement("w:p")
            para._p.addprevious(new_p)
            note = Paragraph(new_p, para._parent)
            run = note.add_run(
                "Teslim notu (27 Ekim 2026): SQL sayısal yanıt tutarlılığı tüm metinde 17/24 (0,708) "
                "olarak hizalanmıştır. RAG kısaltması ilk tanımdan sonra tekleştirilmiştir. "
                "İçindekiler alanını Word’de Ctrl+A → F9 ile yenileyiniz. Ekran görüntülerindeki "
                "işletim sistemi filigranı nitel hata örneği olarak bırakılmıştır."
            )
            run.italic = True
            return


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--src", default=str(DEFAULT_SRC))
    parser.add_argument("--dst", default=str(DEFAULT_DST))
    args = parser.parse_args()
    src, dst = Path(args.src), Path(args.dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    doc = Document(str(src))
    n_text = rewrite_cells_and_paragraphs(doc)
    n_tbl = fix_result_tables(doc)
    n_h = style_headings(doc)
    insert_note_after_ozet_title(doc)
    doc.save(str(dst))
    print(f"kaydedildi: {dst}")
    print(f"paragraf/hücre {n_text}; tablo hücresi {n_tbl}; başlık stili {n_h}")
    print(f"boyut {dst.stat().st_size} bayt")


if __name__ == "__main__":
    main()
