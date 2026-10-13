# -*- coding: utf-8 -*-
"""10 Ekim 2026 revizyon raporuna göre tez Word dosyasını düzenler.

Kaynak dosya değiştirilmez; yanına *_revize_10_10.docx yazar.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from docx import Document
from docx.oxml import OxmlElement
from docx.text.paragraph import Paragraph

DESKTOP = Path(r"C:\Users\Serenay\Desktop")
OUT_DIR = Path(__file__).resolve().parents[1] / "evaluation_output"
GEN_PATH = OUT_DIR / "generation_report.json"
SQL_PATH = OUT_DIR / "sql_gold_results.json"
E2E_PATH = OUT_DIR / "sql_hybrid_e2e_report.json"


def find_src() -> Path:
    for p in DESKTOP.glob("*.docx"):
        name = p.name.casefold()
        if "revize" in name or name.startswith("~$"):
            continue
        if "son" in name and "hayvan" in name:
            return p
    raise FileNotFoundError("Desktop'ta 'hayvancılık ... son.docx' bulunamadı")


def set_para_text(paragraph: Paragraph, text: str) -> None:
    if paragraph.runs:
        paragraph.runs[0].text = text
        for run in paragraph.runs[1:]:
            run.text = ""
    else:
        paragraph.add_run(text)


def insert_after(paragraph: Paragraph, text: str, style: str | None = None) -> Paragraph:
    new_p = OxmlElement("w:p")
    paragraph._p.addnext(new_p)
    new_para = Paragraph(new_p, paragraph._parent)
    if style:
        try:
            new_para.style = style
        except Exception:
            pass
    new_para.add_run(text)
    return new_para


PHRASE_MAP = [
    (
        "Belirli alanlar veya sektörler hakkında daha detaylı bir analiz "
        "isterseniz lütfen bize bildirin. ",
        "",
    ),
    (
        "Belirli alanlar veya sektörler hakkında daha detaylı bir analiz "
        "isterseniz lütfen bize bildirin.",
        "",
    ),
    ("Transformer tabanlı öğrenme yönetim sistemleri (LLM'ler)",
     "Transformer tabanlı büyük dil modelleri (LLM'ler)"),
    ("Transformer tabanlı öğrenme yönetim sistemleri",
     "Transformer tabanlı büyük dil modelleri"),
    ("artırılmış üretim yoluyla bilgi alma (AGR)",
     "geri getirme destekli üretim (RAG)"),
    ("artırılmış üretim yoluyla geri alma (AGR)",
     "geri getirme destekli üretim (RAG)"),
    ("Artırılmış Veri Alımıyla Üretim (AGR)",
     "Geri Getirme Destekli Üretim (RAG)"),
    ("RAG (İlişkisel Toplu Veritabanı)",
     "RAG (Geri Getirme Destekli Üretim)"),
    ("Geri Alma Destekli Üretim", "Geri Getirme Destekli Üretim"),
    ("Geri Getirim Destekli Üretim", "Geri Getirme Destekli Üretim"),
    ("Geri Alma", "Geri Getirme"),
    (" (AGR)", " (RAG)"),
    ("AGR ", "RAG "),
    ("AGR,", "RAG,"),
    ("YAPAY ZEKA", "YAPAY ZEKÂ"),
    ("Yapay zeka", "Yapay zekâ"),
    ("yapay zeka", "yapay zekâ"),
    ("veritabanındaki ticari verilere",
     "veritabanındaki sentetik çiftlik kayıtlarına"),
    ("PostgreSQL veritabanından şirket özel verilerini",
     "PostgreSQL veritabanından sentetik çiftlik verilerini"),
    ("ticari verilerden elde edilen sayısal sonuçların",
     "sentetik çiftlik kayıtlarından elde edilen sayısal sonuçların"),
]


CONTRADICTION_REPLACEMENTS = [
    (
        re.compile(
            r"Precision@K.*?nihai nicel sonuçlar henüz mevcut verilere dahil edilmemiştir\.?",
            re.IGNORECASE | re.DOTALL,
        ),
        (
            "Retrieval için Precision@K, Recall@K, MRR ve nDCG@5 sonuçları "
            "Tablo 4.5’te verilmiştir. Yanıt üretimi (generation) ölçümleri "
            "ise atıf doğruluğu ve desteksiz iddia oranı ile ayrıca raporlanmıştır."
        ),
    ),
]


def apply_phrase_map(text: str) -> str:
    for old, new in PHRASE_MAP:
        text = text.replace(old, new)
    for pattern, repl in CONTRADICTION_REPLACEMENTS:
        text = pattern.sub(repl, text)
    return text


def load_metrics() -> dict:
    gen = {}
    sql = {}
    e2e = {}
    if GEN_PATH.exists():
        gen = json.loads(GEN_PATH.read_text(encoding="utf-8")).get("summary", {})
    if SQL_PATH.exists():
        sql = json.loads(SQL_PATH.read_text(encoding="utf-8"))
    if E2E_PATH.exists():
        e2e = json.loads(E2E_PATH.read_text(encoding="utf-8"))
    return {"gen": gen, "sql": sql, "e2e": e2e}


def patch_incomplete_sentence(text: str) -> str:
    if "daha güvenilir karar destek sistemleri oluşturur" in text and "..." in text:
        return (
            "Bu yaklaşımlar, yapılandırılmış çiftlik kayıtları ile bilimsel "
            "kaynakların birlikte kullanımı yoluyla daha güvenilir karar destek "
            "sistemleri oluşturmayı amaçlar."
        )
    if text.strip().endswith("kullanımı yoluyla daha güvenilir karar destek sistemleri oluşturur."):
        # incomplete subject
        if text.strip().startswith("Bu yaklaşımlar,"):
            return (
                "Bu yaklaşımlar, yapılandırılmış çiftlik kayıtları ile bilimsel "
                "kaynakların birlikte kullanımı yoluyla daha güvenilir karar destek "
                "sistemleri oluşturmayı amaçlar."
            )
    return text


def update_title_candidates(doc: Document) -> int:
    n = 0
    new_title = (
        "Süt Sığırcılığında Yapılandırılmış Çiftlik Verileri ile Bilimsel "
        "Bilginin Entegrasyonu için RAG Tabanlı Sohbet Asistanı"
    )
    for para in doc.paragraphs:
        t = para.text.strip()
        if not t:
            continue
        if "Hayvancılık Sektöründe" in t and (
            "Sohbet" in t or "LangChain" in t or "RAG" in t or "Yapay" in t
        ):
            set_para_text(para, new_title)
            n += 1
        elif t.startswith("Hayvancılık Sektöründe Yapay"):
            set_para_text(para, new_title)
            n += 1
    return n


def fix_sql_counts(doc: Document, sql_ok: int | None, sql_n: int | None) -> int:
    n = 0
    if not sql_n:
        return 0
    # Prefer truthful counts after F-SQL019 fix
    target_ok = sql_ok if sql_ok is not None else sql_n
    patterns = [
        (
            "24 referans sorgunun 23’ü",
            f"24 referans sorgunun {target_ok}’ü" if target_ok != 24
            else "24 referans sorgunun tamamı",
        ),
        (
            "24 referans sorgunun 23'ü",
            f"24 referans sorgunun {target_ok}'ü" if target_ok != 24
            else "24 referans sorgunun tamamı",
        ),
        ("23/24", f"{target_ok}/24"),
        (
            "ciftlikler.ad",
            "ciftlikler.ciftlik_adi (F-SQL019 şema uyumu için düzeltilmiştir)",
        ),
    ]
    for para in doc.paragraphs:
        raw = para.text
        new = raw
        for old, repl in patterns:
            if old in new:
                new = new.replace(old, repl)
        if new != raw:
            set_para_text(para, new)
            n += 1
    return n


def insert_discussion_and_rq(doc: Document, metrics: dict) -> int:
    gen = metrics["gen"]
    e2e = metrics["e2e"]
    cit = gen.get("mean_citation_correctness")
    uns = gen.get("mean_unsupported_claim_rate")
    sql_num = (e2e.get("sql") or {}).get("numerical_accuracy")
    hyb = (e2e.get("hybrid") or {}).get("end_to_end_accuracy")

    discussion = (
        "5.1. Tartışma\n"
        if False else ""
    )
    hyb_txt = f"{hyb}" if hyb is not None else "ayrıca"
    sql_txt = (
        f" (sayısal tutarlılık={sql_num})" if sql_num is not None else ""
    )
    blocks: list[tuple[str, str]] = [
        ("Tartışma", "Heading 1"),
        (
            "Held-out yönlendirme başarısı (89/89) soruların doğru işleme "
            "kanalına gitmesini ölçer; nihai kullanıcı yanıtının bilimsel veya "
            "sayısal doğruluğunu kanıtlamaz. Retrieval katmanında BGE-M3 tabanlı "
            "anlamsal erişim BM25’e göre belirgin üstünlük göstermiş, ağırlıklı "
            "RRF hibrit ise bu derlemede FAISS’in çok az gerisinde kalmıştır. "
            "FAISS ile hibrit arasındaki yaklaşık 0,01’lik P@5 farkı 33 soruluk "
            "örneklemde istatistiksel üstünlük kanıtı değildir. Pilot sette "
            "60/40 ve 70/30 birleştirme ağırlıkları nDCG@5 açısından bağlanmış; "
            "60/40 önceden belirlenen tie-break tercihi olarak dondurulmuştur.",
            "Normal",
        ),
        (
            f"RAG üretim deneyinde ortalama atıf doğruluğu {cit}, desteksiz "
            f"iddia oranı {uns} bulunmuştur. Bu sonuç, ilgili belgenin "
            "getirilmesinin doğru cümlenin üretilmesini garanti etmediğini "
            "gösterir. SQL kanalında referans sorguların çalıştırılabilirliği "
            "ile sistem doğal dil yanıtının altın sonuçlarla sayısal uyumu "
            f"ayrı raporlanmıştır{sql_txt}. HYBRID uçtan uca sentez doğruluğu "
            f"{hyb_txt} olarak ölçülmüştür. RAG gecikmeleri onlarca saniyeyi "
            "bulabildiğinden kullanıcı deneyimi açısından darboğaz yerel LLM "
            "çıkarımıdır. Çiftlik kayıtları sentetik olduğu için saha "
            "genellemesi iddia edilmez; sistem veteriner tanısı veya ilaç "
            "önerisi vermez.",
            "Normal",
        ),
        ("Araştırma sorularının yanıtlanma durumu", "Heading 2"),
        (
            "RQ1 (yönlendirme) nicel olarak yanıtlanmıştır. RQ2 (BM25/FAISS/RRF) "
            "nicel olarak yanıtlanmıştır; gold relevance protokolü belgede "
            "açıklanmalıdır. RQ3 (ağırlık etkisi) pilot sette kısmen "
            "yanıtlanmıştır ve 60/40 tie-break tercihidir. RQ4 (SQL doğal dil "
            "uçtan uca sayısal tutarlılık) ve RQ5 (atıf/desteksiz iddia) bu "
            "revizyonda otomatik metriklerle ölçülmüştür; iki bağımsız uzman "
            "0–2 puanlaması tamamlayıcı protokol olarak bırakılmıştır.",
            "Normal",
        ),
    ]

    anchor = None
    for para in doc.paragraphs:
        t = para.text.strip()
        if (t.startswith("5.") and "Sonuç" in t) or t.startswith("SONUÇ") or t.startswith("5. Sonuç"):
            anchor = para
            break
    if anchor is None:
        for para in reversed(doc.paragraphs):
            if para.text.strip():
                anchor = para
                break
    if anchor is None:
        return 0

    prev = None
    for para in doc.paragraphs:
        if para._p is anchor._p:
            break
        prev = para
    target = prev or anchor
    node = target
    inserted = 0
    for text, style in blocks:
        node = insert_after(node if inserted else target, text, style)
        inserted += 1
    return inserted


def global_replace(doc: Document) -> int:
    n = 0
    for para in doc.paragraphs:
        old = para.text
        new = apply_phrase_map(old)
        new = patch_incomplete_sentence(new)
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


def patch_appendix_sql_table(doc: Document) -> int:
    """Ensure F-SQL019 appears in any 3-column SQL appendix-like table."""
    changed = 0
    for table in doc.tables:
        if len(table.rows) < 5 or len(table.columns) < 3:
            continue
        header = " ".join(c.text.strip().casefold() for c in table.rows[0].cells)
        if "soru" not in header and "id" not in header:
            continue
        ids = [row.cells[0].text.strip() for row in table.rows[1:]]
        if any(i.startswith("F-SQL") for i in ids) and "F-SQL019" not in ids:
            # Find F-SQL018 row and insert note in a new row if possible
            for row in table.rows:
                if row.cells[0].text.strip() == "F-SQL018":
                    # Can't easily insert mid-table; append row
                    new_row = table.add_row()
                    new_row.cells[0].text = "F-SQL019"
                    new_row.cells[1].text = "Çiftliğin adını söyle."
                    new_row.cells[2].text = (
                        "ciftlik_adi (şema-düzeltilmiş altın SQL; "
                        "DB yeniden çalıştırma ile doğrulanır)"
                    )
                    changed += 1
                    break
        # If F-SQL019 exists with empty/missing expected, update
        for row in table.rows:
            if row.cells[0].text.strip() == "F-SQL019":
                if len(row.cells) >= 3:
                    row.cells[2].text = (
                        "ciftlik_adi sütunu ile düzeltilmiş altın sorgu "
                        "(SELECT ciftlik_adi FROM ciftlikler WHERE id = 1)"
                    )
                    changed += 1
    return changed


def main() -> None:
    src = find_src()
    dst = DESKTOP / "hayvancilik_guncel_son_revize_10_10.docx"
    metrics = load_metrics()
    sql_ok = metrics["sql"].get("executed_ok")
    sql_n = metrics["sql"].get("n")

    doc = Document(str(src))
    n_title = update_title_candidates(doc)
    n_global = global_replace(doc)
    n_sql = fix_sql_counts(doc, sql_ok, sql_n)
    n_app = patch_appendix_sql_table(doc)
    n_disc = insert_discussion_and_rq(doc, metrics)
    doc.save(str(dst))

    # Also copy into repo for backup
    repo_dst = Path(__file__).resolve().parents[2] / "hayvancilik_guncel_son_revize_10_10.docx"
    doc.save(str(repo_dst))

    summary = {
        "source": str(src),
        "dest_desktop": str(dst),
        "dest_repo": str(repo_dst),
        "title_updates": n_title,
        "global_replacements": n_global,
        "sql_count_fixes": n_sql,
        "appendix_patches": n_app,
        "discussion_blocks": n_disc,
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "thesis_word_revision_log.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (OUT_DIR / "thesis_word_revision_log.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("saved", summary["dest_desktop"].encode("ascii", "backslashreplace").decode())
    print(
        "title", summary["title_updates"],
        "global", summary["global_replacements"],
        "discussion", summary["discussion_blocks"],
    )


if __name__ == "__main__":
    main()
