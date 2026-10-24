# -*- coding: utf-8 -*-
"""24 Ekim 2026 editör listesi için veri paketi üretir ve tez docx'ine son düzeltmeleri işler.

Paket: Downloads/Tez_Veri_Paketi_24_10_2026/ (docx + csv + md)
Tez:   Downloads/hayvancilik_revizyon_24_10_2026.docx (yerinde güncellenir)
"""
from __future__ import annotations

import csv
import json
import os
import shutil
import sys
from pathlib import Path

import psycopg2
from docx import Document
from docx.oxml import OxmlElement
from docx.shared import Pt
from docx.text.paragraph import Paragraph
from dotenv import load_dotenv

BACKEND = Path(__file__).resolve().parents[1]
ROOT = BACKEND.parent
sys.path.insert(0, str(BACKEND))
load_dotenv(BACKEND / ".env")

from thesis_eval.metrics import wilson_interval  # noqa: E402
from thesis_rag import route_rules  # noqa: E402

OUT_DIR = Path(r"C:\Users\Serenay\Downloads\Tez_Veri_Paketi_24_10_2026")
THESIS = Path(r"C:\Users\Serenay\Downloads\hayvancilik_revizyon_24_10_2026.docx")
THESIS_COPY = ROOT / "hayvancilik_revizyon_24_10_2026.docx"
EVAL = BACKEND / "evaluation_output"

GEN = json.loads((EVAL / "generation_report.json").read_text(encoding="utf-8"))
E2E = json.loads((EVAL / "sql_hybrid_e2e_report.json").read_text(encoding="utf-8"))
GOLD = json.loads((EVAL / "sql_gold_results.json").read_text(encoding="utf-8"))
RESEARCHER = json.loads((EVAL / "rag_researcher_scores.json").read_text(encoding="utf-8"))
MANIFEST = json.loads((BACKEND / "knowledge_base" / "corpus_manifest.json").read_text(encoding="utf-8"))
HELDOUT = json.loads((BACKEND / "evaluation_sets" / "final_heldout_set.json").read_text(encoding="utf-8"))
SECURITY = json.loads((EVAL / "security_smoke.json").read_text(encoding="utf-8"))
LLM_ONLY_PATH = EVAL / "llm_only_baseline.json"
LLM_ONLY = json.loads(LLM_ONLY_PATH.read_text(encoding="utf-8")) if LLM_ONLY_PATH.exists() else None

RAG_SYSTEM_PROMPT = """Sen süt sığırcılığı alanında çalışan kaynak-temelli bir yapay zekâ danışmanısın.
SADECE verilen KAYNAK BAĞLAMI içindeki bilgileri kullan.
HER ZAMAN TÜRKÇE cevap ver.
Cevap en fazla 3 kısa cümle olsun.
Kesin hastalık tanısı koyma. Antibiyotik veya doz önerme.
Her bilimsel cümlenin sonunda [K1] veya [K2] gibi kaynak kimliği yaz.
Kaynakta yoksa uydurma.
JSON veya kod üretme."""
RAG_USER_PROMPT = "SORU:\n{question}\n\nKAYNAK BAĞLAMI:\n{context}\n\nYalnızca kaynak bağlamına dayanarak Türkçe cevap ver."
SQL_GEN_PROMPT = "PostgreSQL için yalnızca bir SELECT veya WITH ... SELECT yaz. Markdown, açıklama ve noktalı virgül yok. Şema: <schema.sql özeti> + 'Sorguda ilgili tablolara AND COALESCE(ciftlik_id, 1) = {ciftlik_id} ekle.'"
SQL_VERBALIZE_PROMPT = "Sen süt çiftliği asistanısın. SQL sonucunu kısa Türkçe açıkla. Sayıları değiştirme. Tanı veya ilaç önerme. Süt sığırcılığını hastalık gibi anlatma.  (kullanıcı: SORU + SONUÇ json)"
ROUTER_LLM_PROMPT = "Sınıfı tek kelime yaz: RAG, SQL, HYBRID veya CHAT."

CORPUS_CITATIONS = {
    "D01": "FAO Regional Dairy Development and Training Team for Asia and the Pacific (1993). Small-scale dairy farming manual, Vol. 5. FAO, Rome. (Kapak metni; FAO Paper 78 değildir.)",
    "D02": "Kurt, S., Çolakoğlu, H. E., Yazlık, M. O., Vural, M. R., Küplülü, Ş. (2019). Sütçü ineklerde mastitis yönünden kuru ve geçiş dönemlerinin önemi. Atatürk Üniv. Vet. Bil. Derg., 14(1), 107-113. doi:10.17094/ataunivbd.407022",
    "D03": "Darbaz, İ., Ergene, O. (2015). Sürü meme sağlığı yönetiminde somatik hücre sayısının önemi. Erciyes Üniv. Vet. Fak. Derg., 12(3), 203-210.",
    "D04": "Yalçın, H., Çakmak, T. (2022). İnek sütlerinde somatik hücre sayısı ve bazı parametrelerin araştırılması. MJAVL, 12(1), 81-87. doi:10.53518/mjavl1092994",
    "D05": "Makkar, H. P. S. (2012). Balanced feeding for improving livestock productivity. FAO Animal Production and Health Paper 173. ISBN 978-92-5-107303-2",
    "D06": "Bernard, J. K., Montgomery, M. J. (t.y.). Managing intake of lactating dairy cows (PB 1598). University of Tennessee Agricultural Extension Service.",
    "D07": "University of Wisconsin–Madison Division of Extension (t.y.). The fresh cow: Milk fever.",
    "D08": "Overton, T. R. (t.y.). Effective transition cow management to maximize internal herd growth. Cornell University, Dept. of Animal Science.",
    "D09": "Moriel, P., Batistel, F. (2021). Nutrition at early stages of life determines the future growth and reproductive performance of dairy calves (AN336). UF/IFAS Extension. doi:10.32473/edis-an336-2021",
    "D10": "Snarr, A. (t.y.). The importance of colostrum (fact sheet). Utah State University Extension. (Dosya adı 2026; yıl kapakta okunamadı.)",
    "D11": "Fricke, P. M. (2018). Evolution of timed AI protocols and overview of the 2018 DCRC reproductive management strategies protocol sheet for dairy cows. DCRC Proceedings.",
    "D12": "Fricke, P. M., Wiltbank, M. C., Pursley, J. R. (2023). The high fertility cycle. University of Wisconsin–Madison Division of Extension.",
    "D13": "WOAH (2024). Chapter 7.11 Animal welfare and dairy cattle production systems. Terrestrial Animal Health Code.",
    "D14": "Öcal, G. O., Güven, F. M., Cedden, F. (2026). Evaluation of housing and management conditions affecting animal welfare in dairy cattle farms in Ankara Province, Türkiye. ADÜ Ziraat Derg., 23(1), 47-53. doi:10.25308/aduziraat.1850888",
    "D15": "FAO, IDF (2011). Guide to good dairy farming practice (2nd ed.). FAO Animal Production and Health Guidelines 8. ISSN 1810-0708",
    "D16": "Codex Alimentarius Commission (2007). Milk and milk products (1st ed.); Code of Hygienic Practice for Milk and Milk Products. FAO/WHO.",
}

SQL_FAIL_REASONS = {
    "F-SQL006": ("Şablon, tek güne ait toplam yerine son sağımların listesini döndürdü; 25,70 L toplamı yanıtta yok.", "şablon kapsamı / toplama hatası"),
    "F-SQL010": ("'En düşük ortalama' sorusu sürü ortalaması şablonuna düştü; hayvan adı (Boncuk) verilmedi.", "şablon yanlış eşleşmesi"),
    "F-SQL012": ("'Papatya'nın ortalaması' sürü ortalaması şablonuna düştü; 14,86 yerine 13,58 sürü değeri verildi.", "şablon yanlış eşleşmesi"),
    "F-SQL013": ("Lale için alarm sayısı 0 iken yanıt genel alarm listesini (Serap) gösterdi; soruya 'hayır' denmedi.", "şablon kapsamı / varlık süzgeci yok"),
    "F-SQL015": ("Şablon yok; model SQL yazdı, çiftlik süzgeci ipucu yanlış eklendi ('= COALESCE(...) = 1') ve sorgu sözdizimi hatası verdi.", "model SQL sözdizimi hatası"),
    "F-SQL020": ("Irk süzgeci şablonda yok; toplam inek sayısı (5) verildi, Simental sayısı (2) verilmedi.", "şablon kapsamı / süzgeç yok"),
    "F-SQL023": ("Okunmamış alarm sayısı 0 iken yanıt alarm listesini gösterdi; sayım verilmedi.", "şablon kapsamı / sayım yok"),
}


def db_snapshot() -> dict:
    connection = psycopg2.connect(
        host=os.getenv("DB_HOST"), port=int(os.getenv("DB_PORT", "5432")),
        dbname=os.getenv("DB_NAME"), user=os.getenv("DB_USER"), password=os.getenv("DB_PASSWORD"),
    )
    snap: dict = {}
    with connection.cursor() as cur:
        for table in ("ciftlikler", "kullanicilar", "inekler", "sagim_kayitlari", "alarmlar", "gunluk_ozetler", "cihaz_tokenlari"):
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            snap[table] = cur.fetchone()[0]
        cur.execute("SELECT MIN(tarih), MAX(tarih) FROM sagim_kayitlari")
        snap["sagim_range"] = [str(x) for x in cur.fetchone()]
        cur.execute("SELECT COUNT(*) FROM sagim_kayitlari WHERE tarih BETWEEN DATE '2026-09-01' AND DATE '2026-09-05'")
        snap["sagim_1_5_eylul"] = cur.fetchone()[0]
        cur.execute("SELECT kupe_no, isim, irk FROM inekler ORDER BY kupe_no")
        snap["inekler"] = cur.fetchall()
        cur.execute("SELECT kupe_no, COUNT(*), ROUND(AVG(sut_miktari),2), MIN(sut_miktari), MAX(sut_miktari) FROM sagim_kayitlari GROUP BY kupe_no ORDER BY kupe_no")
        snap["per_cow"] = [[str(v) for v in row] for row in cur.fetchall()]
        cur.execute("SELECT kupe_no, tarih, sagim_zamani, eski_ortalama, son_verim, dusus_yuzdesi, okundu FROM alarmlar")
        snap["alarmlar_rows"] = [[str(v) for v in row] for row in cur.fetchall()]
        cur.execute("SELECT ciftlik_id, COUNT(*) FROM inekler GROUP BY ciftlik_id")
        snap["inek_per_farm"] = cur.fetchall()
    connection.close()
    return snap


def add_table(doc: Document, headers: list[str], rows: list[list[str]], font_size: int = 9) -> None:
    table = doc.add_table(rows=1, cols=len(headers))
    table.style = "Table Grid"
    for index, header in enumerate(headers):
        cell = table.rows[0].cells[index]
        cell.text = header
        for paragraph in cell.paragraphs:
            for run in paragraph.runs:
                run.bold = True
                run.font.size = Pt(font_size)
    for row in rows:
        cells = table.add_row().cells
        for index, value in enumerate(row):
            cells[index].text = "" if value is None else str(value)
            for paragraph in cells[index].paragraphs:
                for run in paragraph.runs:
                    run.font.size = Pt(font_size)


def fmt(value, digits: int = 4) -> str:
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:.{digits}f}".replace(".", ",")
    return str(value)


def write_csv(path: Path, headers: list[str], rows: list[list]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle, delimiter=";")
        writer.writerow(headers)
        writer.writerows(rows)


def build_package(snap: dict) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    doc = Document()
    doc.styles["Normal"].font.name = "Times New Roman"
    doc.styles["Normal"].font.size = Pt(11)

    doc.add_heading("Tez veri paketi — 24 Ekim 2026 revizyon listesi", 0)
    doc.add_paragraph(
        "Bu paket, ikinci liste için istenen yedi öğeyi içerir. Tüm sayılar Backend/evaluation_output "
        "kayıtlarından ve canlı PostgreSQL veri tabanından okunmuştur. Uydurma değer yoktur. "
        "Metin içinde 'ölçülmedi' yazan yerler gerçekten ölçülmemiştir."
    )

    # 1. Metrik tanımları
    doc.add_heading("1. RAG değerlendirme metrikleri: model, formül, hesaplama", 1)
    doc.add_paragraph(
        "Hakem (judge) model yoktur. Tüm otomatik metrikler thesis_eval/metrics.py içindeki "
        "generation_metrics fonksiyonuyla, her yanıt için ayrı ayrı hesaplanır ve 33 soru üzerinden "
        "aritmetik ortalama alınır (payda = 33 soru, soru başına ortalama)."
    )
    add_table(
        doc,
        ["Metrik", "Birim", "Soru başına formül", "33 soru ortalaması", "Not"],
        [
            ["Atıf doğruluğu (citation correctness)", "atıf kimliği", "geçerli [K] kimliği sayısı / yanıttaki tekil [K] sayısı; yanıtta atıf yoksa 0", fmt(GEN["summary"]["mean_citation_correctness"]), "10 yanıtta atıf var ve hepsi geçerli (10 × 1,0 / 33 = 0,303)"],
            ["Atıf tamlığı (citation completeness)", "cümle", "[K] içeren cümle sayısı / toplam cümle sayısı (cümle = . ! ? ile bölünür)", fmt(GEN["summary"]["mean_citation_completeness"]), "23 yanıtta 0"],
            ["Desteksiz iddia oranı", "cümle", "1 − atıf tamlığı (iddia = cümle; ayrı iddia ayrıştırma yok)", fmt(GEN["summary"]["mean_unsupported_claim_rate"]), "atıfsız cümle = desteksiz kabul edilir"],
            ["Tercih edilen kaynağa isabet", "belge", "retrieval listesindeki tercih edilen dosya sayısı / tercih listesi uzunluğu (genelde 2)", fmt(GEN["summary"]["mean_preferred_source_hit_rate"]), "yanıt metnine değil, getirilen belge adlarına bakar"],
            ["Tanı reddi", "yanıt", "yanıtta 'veteriner hekim', 'tanı koy', 'antibiyotik' veya 'sistem bu tür kararları veremez' geçiyorsa 1", f"{GEN['summary']['diagnosis_refusal_ok']}/33", "anahtar sözcük taraması; tanı istemeyen sorular da sayılır"],
            ["0–2 doğruluk proxy (otomatik)", "yanıt", "pref ≥ 0,5 ve desteksiz ≤ 0,5 → 2; pref ≥ 0,5 veya desteksiz ≤ 0,75 → 1; aksi 0", fmt(GEN["summary"]["mean_accuracy_0_2_auto"], 3), "kural; hakem değil"],
            ["0–2 bağlılık proxy (otomatik)", "yanıt", "atıf doğruluğu ≥ 0,5 ve desteksiz ≤ 0,5 → 2; atıf > 0 veya desteksiz ≤ 0,75 → 1; aksi 0", fmt(GEN["summary"]["mean_faithfulness_0_2_auto"], 3), "kural; hakem değil"],
            ["Araştırmacı 0–2 doğruluk / bağlılık", "yanıt", "tek değerlendirici, kör değil, aynı rubrik", f"{fmt(RESEARCHER['summary']['rater_A_mean_accuracy'],3)} / {fmt(RESEARCHER['summary']['rater_A_mean_faithfulness'],3)}", f"otomatik ile doğruluk uyumu {fmt(RESEARCHER['summary']['agreement_accuracy_rate'],3)}; Cohen κ yok"],
        ],
    )
    doc.add_paragraph(
        "Önerilen tez cümlesi: 'Atıf doğruluğu, atıf tamlığı ve desteksiz iddia oranı bir hakem modelin "
        "anlamsal kararı değil, yanıttaki [K] kaynak kimliklerine dayanan kural tabanlı ölçülerdir; "
        "RAGAS veya benzeri bir araç kullanılmamıştır.'"
    )

    # 2. LLM-only
    doc.add_heading("2. LLM-only karşılaştırma (aynı 33 soru, retrieval kapalı)", 1)
    if LLM_ONLY and LLM_ONLY.get("status") == "complete":
        s = LLM_ONLY["summary"]
        r = s["rag_reference"]
        doc.add_paragraph(s["protocol"])
        add_table(
            doc,
            ["Ölçü", "RAG (bağlamlı)", "LLM-only (bağlamsız)"],
            [
                ["n", "33", str(s["n"])],
                ["Atıf doğruluğu", fmt(r["mean_citation_correctness"]), fmt(s["mean_citation_correctness"]) + " (yapısal; kaynak kimliği yok)"],
                ["Atıf tamlığı", fmt(r["mean_citation_completeness"]), fmt(s["mean_citation_completeness"]) + " (yapısal)"],
                ["Desteksiz iddia oranı", fmt(r["mean_unsupported_claim_rate"]), fmt(s["mean_unsupported_claim_rate"]) + " (yapısal)"],
                ["Red/uyarı dili taşıyan yanıt", f"{GEN['summary']['diagnosis_refusal_ok']}/33", f"{s['refusal_marker_count']}/{s['n']}"],
                ["Yabancı sözcük izi taşıyan yanıt", "—", f"{s['foreign_token_rows']}/{s['n']}"],
                ["Ortalama cümle sayısı", "—", fmt(s["mean_sentence_count"], 2)],
                ["Gecikme ort. / medyan / p95 (sn)", f"{fmt(r['latency']['mean'],2)} / {fmt(r['latency']['median'],2)} / {fmt(r['latency']['p95'],2)}", f"{fmt(s['latency']['mean'],2)} / {fmt(s['latency']['median'],2)} / {fmt(s['latency']['p95'],2)}"],
            ],
        )
        doc.add_paragraph(s["interpretation_note"])
        doc.add_paragraph("Soru düzeyinde iki yanıt yan yana (insan karşılaştırması için):")
        add_table(
            doc,
            ["Kimlik", "Soru", "RAG yanıtı", "LLM-only yanıtı"],
            [[row["id"], row["question"], (row["answer_rag"] or "").strip(), row["answer_llm_only"]] for row in LLM_ONLY["rows"]],
            font_size=8,
        )
    else:
        doc.add_paragraph(
            "LLM-only koşusu bu paket üretilirken henüz tamamlanmamıştı. Tamamlanınca "
            "evaluation_output/llm_only_baseline.json dosyası ve bu bölüm yeniden üretilir."
        )

    # 3. Yapılandırma
    doc.add_heading("3. Model ayarları: tek yapılandırma", 1)
    add_table(
        doc,
        ["Parametre", "Final deney (geçerli)", "Şekil 3.1'deki eski değer", "Kaynak"],
        [
            ["Üretim modeli", "mistral (Ollama etiketi mistral:latest)", "mistral:latest", "thesis_rag/settings.py; ollama /api/tags"],
            ["Model özeti (digest)", "6577803aa9a036369e481d648a2baebb381ebc6e897f2bb9a766a2aa7bfbc1cf", "—", "ollama /api/tags"],
            ["Kuantizasyon / boyut", "Q4_K_M, GGUF, 7,2 milyar parametre, 4,37 GB", "—", "ollama /api/tags"],
            ["num_ctx (bağlam penceresi)", "2048", "4096", "settings.llm_num_ctx; reproducibility.json"],
            ["num_predict (maks. çıktı)", "160", "320", "settings.llm_num_predict; reproducibility.json"],
            ["temperature / seed", "0 / 0", "—", "reproducibility.json"],
            ["num_gpu", "0 (CPU)", "—", "rag_chain.py; LLM-only koşusu"],
            ["Gömme modeli", "bge-m3 (F16, 566,7 M)", "bge-m3", "ollama /api/tags"],
            ["Retrieval", "FAISS IndexFlatL2 + BM25 (k1 1,5; b 0,75); weighted RRF 0,60/0,40; k=60; top-k 8+8→5", "—", "reproducibility.json"],
            ["Parçalama", "900 karakter, 150 örtüşme; 1.833 parça; 748 sayfa birimi", "—", "index manifest"],
            ["Paketler", "langchain 0.1.17; langchain_core 1.4.7; langchain_community 0.4.2; langchain_ollama 1.1.0; langgraph 1.2.5; faiss 1.8.0; psycopg2 2.9.12; Python 3.12.2", "—", "reproducibility.json"],
            ["Donanım", "Intel Core i7-11800H, 16 GB RAM, RTX 3050 Ti 4 GB (GPU kullanılmadı)", "aynı", "Şekil 3.1"],
        ],
    )
    doc.add_paragraph(
        "Not: 4096/320 değerleri thesis_rag/rag_chain_before_*.py yedek dosyalarındaki önceki sürüme aittir. "
        "Şekil 3.1 yeniden çizilirken 2048 / 160 / mistral:latest (Q4_K_M) yazılmalıdır."
    )

    # 4. Veritabanı
    doc.add_heading("4. Sentetik veri tabanı: şema, hayvan ve kayıt sayıları", 1)
    doc.add_paragraph("Kaynak: Backend/schema.sql ve canlı PostgreSQL (Sut_Sihirbazi) sayımı, 24 Ekim 2026.")
    add_table(
        doc,
        ["Tablo", "Temel alanlar", "Kayıt sayısı"],
        [
            ["ciftlikler", "id, ciftlik_adi, olusturulma_tarihi", f"{snap['ciftlikler']} (yalnız id=1 'Tez Test Ciftligi' hayvan ve kayıt içerir; diğer 3 satır kullanıcı kaydı testlerinden kalan boş çiftliklerdir)"],
            ["kullanicilar", "id, ciftlik_id→ciftlikler, ad_soyad, eposta, sifre_hash, telefon", str(snap["kullanicilar"])],
            ["inekler", "kupe_no (PK), ciftlik_id, isim, irk, dogum_tarihi, laktasyon_no", f"{snap['inekler']} (3 Holstein, 2 Simental; tamamı çiftlik 1)"],
            ["sagim_kayitlari", "id, ciftlik_id, kupe_no→inekler, tarih, sagim_zamani (m/e), sut_miktari NUMERIC(10,2) litre", f"{snap['sagim_kayitlari']} ({snap['sagim_range'][0]} – {snap['sagim_range'][1]}; günde 10 = 5 inek × sabah/akşam; 1–5 Eylül kesiti {snap['sagim_1_5_eylul']})"],
            ["alarmlar", "id, ciftlik_id, kupe_no, tarih, sagim_zamani, eski_ortalama, son_verim, dusus_yuzdesi, mesaj, okundu", f"{snap['alarmlar']} (TR0001 Serap, 05.09.2026 akşam, 12,80→7,80 L, %39,06, okundu=true)"],
            ["gunluk_ozetler", "ciftlik_id, tarih, dunku/bugunku_toplam_sut, en_verimli_inek_kupe_no, mesaj", str(snap["gunluk_ozetler"])],
            ["cihaz_tokenlari", "token", str(snap["cihaz_tokenlari"])],
        ],
    )
    cow_rows = []
    for (kupe, name, breed), pc in zip(snap["inekler"], snap["per_cow"]):
        cow_rows.append([kupe, name, breed, pc[1], pc[2].replace(".", ","), pc[3].replace(".", ","), pc[4].replace(".", ",")])
    add_table(doc, ["Küpe", "Ad", "Irk", "Sağım sayısı", "Ort. (L)", "Min", "Maks"], cow_rows)
    doc.add_paragraph(
        "Varlık-ilişki: ciftlikler 1—N kullanicilar; ciftlikler 1—N inekler; inekler 1—N sagim_kayitlari; "
        "inekler 1—N alarmlar; ciftlikler 1—N gunluk_ozetler. Veriler prototip için elle/betikle girilmiş "
        "sentetik kayıtlardır. Not: okunmamış alarm sayısı 0'dır çünkü tek alarm okundu=true durumundadır."
    )

    # 5. SQL başarısız sorular + HYBRID
    doc.add_heading("5. SQL başarısız soruların nedenleri ve HYBRID bayrakları", 1)
    sql_rows = [r for r in E2E["rows"] if r["expected_route"] == "SQL"]
    ok = sum(1 for r in sql_rows if r.get("entity_or_value_correct"))
    ci = wilson_interval(ok, len(sql_rows))
    doc.add_paragraph(
        f"Soru düzeyindeki kayıt (sql_hybrid_e2e_report.json): {ok}/{len(sql_rows)} değer veya varlık uyumu "
        f"= {ok/len(sql_rows):.4f} (Wilson %95: {ci['low']:.3f}–{ci['high']:.3f}). Tezdeki 15/24 = 0,625 değeri "
        "önceki toplu özetten gelmektedir; satır sayımı 17/24'tür ve tez bu sayıma çekilmiştir. "
        "Başarısız soru sayısı 9 değil 7'dir. Referans SQL çalıştırılabilirliği (24/24) ayrı bir ölçüdür: "
        "araştırmacının yazdığı altın sorgunun veri tabanında hatasız çalışıp beklenen değeri döndürmesi."
    )
    gold_by_id = {r["id"]: r for r in GOLD["rows"]}
    fail_rows = []
    for r in sql_rows:
        if r.get("entity_or_value_correct"):
            continue
        reason, kind = SQL_FAIL_REASONS.get(r["id"], ("", ""))
        fail_rows.append([
            r["id"], r["question"], str(gold_by_id.get(r["id"], {}).get("expected_value", "")).replace("Decimal(", "").replace(")", "").replace("'", ""),
            (r.get("answer") or "").replace("\n", " / ")[:160], r.get("path"), kind, reason,
        ])
    add_table(doc, ["Kimlik", "Soru", "Altın değer", "Sistem yanıtı (kısaltılmış)", "Yol", "Hata türü", "Açıklama"], fail_rows, font_size=8)
    doc.add_paragraph(
        "Hata tipolojisi (7 soru): şablon yanlış eşleşmesi 2 (F-SQL010, 012); şablon kapsamı/süzgeç eksik 4 "
        "(F-SQL006, 013, 020, 023); model SQL sözdizimi hatası 1 (F-SQL015). 22 soru şablon yolu, 2 soru model SQL yolu kullandı."
    )
    hyb_rows = [r for r in E2E["rows"] if r["expected_route"] == "HYBRID"]
    hok = sum(1 for r in hyb_rows if r.get("hybrid_e2e_correct"))
    hci = wilson_interval(hok, len(hyb_rows))
    doc.add_paragraph(
        f"HYBRID: {hok}/{len(hyb_rows)} = {hok/len(hyb_rows):.4f} (Wilson %95: {hci['low']:.3f}–{hci['high']:.3f}). "
        "E2E bayrağı = yönlendirme HYBRID ∧ çiftlik varlığı yanıtta ∧ tercih edilen belge retrieval listesinde ∧ tanı sızıntısı yok. "
        "Başarısız 5 soruda yalnızca 'tercih edilen belge' bayrağı yanlıştır; bu nedenle oran sentez doğruluğu değil, kaynak seçimi oranıdır. "
        "Bilimsel açıklamanın doğruluğu ve sentez tutarlılığı ölçülmemiştir; HYBRID gecikmesi LLM sentezini içermez."
    )
    add_table(
        doc,
        ["Kimlik", "Soru", "Yönlendirme", "Çiftlik varlığı", "Tercih edilen belge", "Kaynak var", "Tanı yok", "E2E", "Getirilen belgeler"],
        [[r["id"], r["question"], "✓" if r["route_correct"] else "✗", "✓" if r.get("hybrid_farm_ok") else "✗",
          "✓" if r.get("hybrid_preferred_source_hit") else "✗", "✓" if r.get("hybrid_has_sources") else "✗",
          "✓" if r.get("hybrid_no_diagnosis_leak") else "✗", "✓" if r.get("hybrid_e2e_correct") else "✗",
          "; ".join(dict.fromkeys(r.get("retrieved_titles") or []))] for r in hyb_rows],
        font_size=8,
    )

    # 6. 89 soru + prompt
    doc.add_heading("6. Final 89 soru ve kullanılan istemler", 1)
    from collections import Counter
    counts = Counter(q["route"] for q in HELDOUT)
    doc.add_paragraph(f"Dağılım: {dict(counts)}. Tam liste CSV olarak paket klasöründedir (06_final_89_soru.csv). "
                      "Oluşturma tarihi dosya sisteminde ayrı kayıtlı değildir; soru dosyası 'split: heldout_final' etiketlidir.")
    add_table(doc, ["Kimlik", "Kanal", "Kategori", "Soru", "Tercih edilen belgeler"],
              [[q["id"], q["route"], q.get("category", ""), q["question"], "; ".join(q.get("preferred_sources") or [])] for q in HELDOUT], font_size=8)
    doc.add_heading("İstemler", 2)
    for label, text in (
        ("RAG üretim sistem istemi (final koşu, thesis_eval/run_academic_evaluation.py)", RAG_SYSTEM_PROMPT),
        ("RAG kullanıcı istemi", RAG_USER_PROMPT),
        ("Yönlendirici LLM yedeği (kural eşleşmezse)", ROUTER_LLM_PROMPT),
        ("SQL üretim istemi (yalnız şablon eşleşmezse)", SQL_GEN_PROMPT),
        ("SQL sözelleştirme istemi", SQL_VERBALIZE_PROMPT),
    ):
        doc.add_paragraph(label).runs[0].bold = True
        doc.add_paragraph(text)
    doc.add_heading("Yönlendirme kuralları (thesis_rag/route_rules.py)", 2)
    doc.add_paragraph("Sıra: (1) CHAT terimi ve ≤5 sözcük → CHAT; (2) çiftlik terimi/varlık + bilimsel terim → HYBRID; (3) yalnız çiftlik → SQL; (4) yalnız bilimsel → RAG; (5) hiçbiri → LLM yedeği.")
    doc.add_paragraph("CHAT terimleri: " + ", ".join(route_rules.CHAT_TERMS))
    doc.add_paragraph("Çiftlik terimleri: " + ", ".join(route_rules.FARM_TERMS))
    doc.add_paragraph("Çiftlik varlıkları: " + ", ".join(route_rules.FARM_ENTITIES))
    doc.add_paragraph("Bilimsel terimler: " + ", ".join(route_rules.KNOWLEDGE_TERMS))
    doc.add_paragraph(
        f"Güvenlik duman testi ({SECURITY['passed']}/{SECURITY['n']}): " +
        "; ".join(f"{r['id']} {r['kind']}: {'geçti' if r['ok'] else 'kaldı'}" for r in SECURITY["rows"])
    )

    # 7. Corpus
    doc.add_heading("7. 16 PDF: kesin kaynak bilgisi, sayfa ve parça sayıları", 1)
    corpus_rows = []
    for d in MANIFEST["documents"]:
        corpus_rows.append([d["id"], d["file"], d["theme"], CORPUS_CITATIONS.get(d["id"], d["full_title"]), str(d["page_unit_count"]), str(d["chunk_count"])])
    add_table(doc, ["Kod", "Dosya", "Tema", "Künye (PDF ilk sayfasından)", "Sayfa birimi", "Parça"], corpus_rows, font_size=8)
    total_pages = sum(d["page_unit_count"] for d in MANIFEST["documents"])
    total_chunks = sum(d["chunk_count"] for d in MANIFEST["documents"])
    doc.add_paragraph(f"Toplam: {total_pages} sayfa birimi, {total_chunks} parça. Seçim ölçütleri: " + "; ".join(MANIFEST["selection_criteria"]) + ".")

    doc.save(OUT_DIR / "Tez_Veri_Paketi_24_10_2026.docx")

    # CSV / yardımcı dosyalar
    write_csv(OUT_DIR / "06_final_89_soru.csv", ["id", "kanal", "kategori", "soru", "tercih_edilen_belgeler"],
              [[q["id"], q["route"], q.get("category", ""), q["question"], "; ".join(q.get("preferred_sources") or [])] for q in HELDOUT])
    write_csv(OUT_DIR / "05_sql_hata_analizi.csv", ["id", "soru", "altin_deger", "sistem_yaniti", "yol", "hata_turu", "aciklama"], fail_rows)
    write_csv(OUT_DIR / "05_hybrid_bayraklar.csv", ["id", "soru", "route_ok", "farm_ok", "preferred_hit", "has_sources", "no_diag_leak", "e2e", "retrieved"],
              [[r["id"], r["question"], r["route_correct"], r.get("hybrid_farm_ok"), r.get("hybrid_preferred_source_hit"), r.get("hybrid_has_sources"), r.get("hybrid_no_diagnosis_leak"), r.get("hybrid_e2e_correct"), "; ".join(r.get("retrieved_titles") or [])] for r in hyb_rows])
    write_csv(OUT_DIR / "07_corpus_16_pdf.csv", ["kod", "dosya", "tema", "kunye", "sayfa_birimi", "parca"], corpus_rows)
    write_csv(OUT_DIR / "01_rag_soru_duzeyi_metrikler.csv",
              ["id", "soru", "atif_dogrulugu", "atif_tamligi", "desteksiz_iddia", "tercih_isabet", "cumle", "atif_kimlikleri", "tani_reddi", "gecikme_sn"],
              [[r["id"], r["question"], r["generation"]["citation_correctness"], r["generation"]["citation_completeness"], r["generation"]["unsupported_claim_rate"], r["generation"]["preferred_source_hit_rate"], r["generation"]["sentence_count"], " ".join(r["generation"].get("cited_ids") or []), r["generation"]["refuses_diagnosis"], r["latency_sec"]] for r in GEN["rows"]])
    shutil.copyfile(BACKEND / "schema.sql", OUT_DIR / "04_schema.sql")
    (OUT_DIR / "06_istemler.txt").write_text(
        "RAG SISTEM ISTEMI\n" + RAG_SYSTEM_PROMPT + "\n\nRAG KULLANICI ISTEMI\n" + RAG_USER_PROMPT +
        "\n\nYONLENDIRICI LLM YEDEGI\n" + ROUTER_LLM_PROMPT + "\n\nSQL URETIM\n" + SQL_GEN_PROMPT + "\n\nSQL SOZELLESTIRME\n" + SQL_VERBALIZE_PROMPT + "\n",
        encoding="utf-8",
    )
    if LLM_ONLY:
        shutil.copyfile(LLM_ONLY_PATH, OUT_DIR / "02_llm_only_baseline.json")


# ---------- Tez docx son düzeltmeleri ----------

def set_text(paragraph: Paragraph, text: str) -> None:
    if paragraph.runs:
        paragraph.runs[0].text = text
        for run in paragraph.runs[1:]:
            run.text = ""
    else:
        paragraph.add_run(text)


def insert_after(paragraph: Paragraph, text: str, style: str = "Normal") -> Paragraph:
    new_p = OxmlElement("w:p")
    paragraph._p.addnext(new_p)
    para = Paragraph(new_p, paragraph._parent)
    para.style = style
    para.add_run(text)
    return para


def patch_thesis(snap: dict) -> dict:
    doc = Document(str(THESIS))
    log = {"kendi_kendini": 0, "db_scale": 0, "figure_table": 0, "llm_only": 0, "sql_count": 0}
    for p in doc.paragraphs:
        t = p.text
        if "Ayrı bir kendi kendini düzeltme ölçümü yapılmamıştır" in t:
            set_text(p, t.replace(" Ayrı bir kendi kendini düzeltme ölçümü yapılmamıştır.", ""))
            log["kendi_kendini"] += 1
        if t.startswith("Sentetik PostgreSQL kayıtları bir prototip ölçeğindedir."):
            set_text(p, (
                "Sentetik PostgreSQL kayıtları bir prototip ölçeğindedir. Canlı veri tabanı sayımına göre hayvan ve sağım "
                "kaydı içeren tek çiftlik vardır (Tez Test Çiftliği; diğer üç çiftlik satırı kullanıcı kaydı denemelerinden "
                f"kalan boş kayıtlardır). Beş inek (3 Holstein: Serap TR0001, Beyza TR0002, Papatya TR0004; 2 Simental: "
                f"Boncuk TR0003, Lale TR0005), {snap['sagim_kayitlari']} sağım kaydı ({snap['sagim_range'][0]} – "
                f"{snap['sagim_range'][1]}; günde 10 kayıt = 5 inek × sabah/akşam) ve tek bir alarm kaydı "
                "(Serap, 05.09.2026 akşam, 12,80→7,80 L, %39,06 düşüş, okundu) bulunur. Referans SQL'deki 50 kayıt, "
                f"1–5 Eylül kesitidir. Süt miktarı litre olarak tutulur. Şema yedi tablodan oluşur: ciftlikler, kullanicilar, "
                "inekler, sagim_kayitlari, alarmlar, gunluk_ozetler (boş) ve cihaz_tokenlari (boş); ilişkiler çiftlik→inek→sağım/alarm "
                "yönündedir. Beş hayvan ve bir haftalık kayıt, 'en yüksek on inek', çok aylık trend veya ABC segmentasyonu gibi "
                "işlevlerin genellenmesini engeller. Kayıtlar betikle üretilmiş örnek kayıtlardır; ticari bir işletmeden alınmamıştır."
            ))
            log["db_scale"] += 1
        if "Uyumsuz sorular F-SQL006" in t and "yedi sorudur" not in t:
            set_text(p, t.replace(
                "Uyumsuz sorular F-SQL006, F-SQL010, F-SQL012, F-SQL013, F-SQL015, F-SQL020 ve F-SQL023'tür.",
                "Uyumsuz sorular yedi sorudur: F-SQL006, F-SQL010, F-SQL012, F-SQL013, F-SQL015, F-SQL020 ve F-SQL023. "
                "Hata türleri: şablonun yanlış soruya eşleşmesi (F-SQL010, F-SQL012: hayvan ortalaması yerine sürü ortalaması), "
                "şablon kapsamı veya süzgeç eksikliği (F-SQL006 tek gün toplamı, F-SQL013 hayvana özgü alarm, F-SQL020 ırk sayımı, "
                "F-SQL023 okunmamış alarm sayımı) ve model SQL sözdizimi hatası (F-SQL015: çiftlik süzgeci ipucu hatalı eklendi).",
            ))
            log["sql_count"] += 1

    # 5.1 tartışmasına şekil tutarsızlık tablosu
    has_table_51 = any(p.text.startswith("Tablo 5.1.") for p in doc.paragraphs)
    for p in doc.paragraphs:
        if has_table_51:
            break
        if p.text.startswith("Retrieval katmanı ile üretim katmanı aynı başarıyı ölçmez."):
            intro = insert_after(p, (
                "Bölüm 4.1'deki ekran görüntüleri de bu açığın nitel örnekleridir. Aşağıdaki tablo, şekillerde doğrudan "
                "gözlenebilen tutarsızlıkları ve ilgili nicel bulguyu eşleştirir."
            ))
            table = doc.add_table(rows=1, cols=3)
            table.style = "Table Grid"
            for i, h in enumerate(("Şekil", "Gözlenen tutarsızlık", "İlgili bulgu / hata türü")):
                table.rows[0].cells[i].text = h
            rows = [
                ("Şekil 4.1 – SQL", "En yüksek 10 inek istenmiş, 5 inek listelenmiş; yanıt yine de 10 inekten söz ediyor. Birim kg; veri tabanı litre.", "Sayısal sözelleştirme hatası; birim tutarsızlığı (Tablo 4.8 SQL tutarlılığı)."),
                ("Şekil 4.2 – HYBRID", "Yanıtta İspanyolca sözcükler; aynı inek için hem %10 artış hem %5 düşüş; Serap için %15 düşüş yazılmış, alarm kaydı %39,06.", "Dil karışması ve iç çelişki; HYBRID sentez doğruluğu ölçülmemiştir."),
                ("Şekil 4.3 – Panel", "'Son 10 günlük üretim' etiketi; grafik 7 günü (30.08–05.09) gösteriyor.", "Arayüz etiketi veri aralığıyla uyumsuz; veri tabanı yalnızca 7 gün içerir."),
                ("Şekil 4.4 – ABC analizi", "Küpe numaralarında TRTR öneki tekrarı; Serap için %43 dalgalanma, alarmda %39,06.", "Arayüz biçimlendirme hatası; 'dalgalanma' ile 'düşüş yüzdesi' farklı tanımlardır, metinde ayrıştırılmalıdır."),
            ]
            for r in rows:
                cells = table.add_row().cells
                for i, v in enumerate(r):
                    cells[i].text = v
            intro._p.addnext(table._tbl)
            cap = Paragraph(OxmlElement("w:p"), intro._parent)
            table._tbl.addnext(cap._p)
            cap.style = "Normal"
            cap.add_run("Tablo 5.1. Şekil 4.1–4.4'te gözlenen tutarsızlıklar ve ilgili nicel bulgular.")
            log["figure_table"] += 1
            break

    # LLM-only sonucu
    if LLM_ONLY and LLM_ONLY.get("status") == "complete":
        s = LLM_ONLY["summary"]
        r = s["rag_reference"]
        for p in doc.paragraphs:
            if p.text.startswith("Aynı 33 RAG sorusunda retrieval bağlamı kapatılarak yalnız Mistral ile üretim yapılmamıştır."):
                set_text(p, (
                    f"Aynı 33 RAG sorusu, retrieval kapatılarak ve bağlam verilmeden yalnız Mistral ile yeniden yanıtlanmıştır "
                    f"(aynı model, temperature 0, seed 0, num_predict 160, num_ctx 2048; istemden yalnızca kaynak bağlamı ve [K] "
                    f"atıf kuralı çıkarılmıştır). Bağlam kimliği bulunmadığı için atıf doğruluğu {fmt(s['mean_citation_correctness'])}, "
                    f"atıf tamlığı {fmt(s['mean_citation_completeness'])} ve desteksiz iddia oranı {fmt(s['mean_unsupported_claim_rate'])} "
                    f"değerleri yapısaldır; RAG koşusunda bu değerler {fmt(r['mean_citation_correctness'])}, "
                    f"{fmt(r['mean_citation_completeness'])} ve {fmt(r['mean_unsupported_claim_rate'])} idi. Bağlamsız yanıtların "
                    f"{s['foreign_token_rows']} tanesinde yabancı sözcük izi, {s['refusal_marker_count']} tanesinde red veya veteriner "
                    f"uyarısı dili vardır; ortalama gecikme {fmt(s['latency']['mean'],2)} saniye (medyan {fmt(s['latency']['median'],2)}, "
                    f"p95 {fmt(s['latency']['p95'],2)}), RAG koşusunda {fmt(r['latency']['mean'],2)} saniyedir. Bu karşılaştırma RAG'in "
                    "izlenebilir atıf üretme katkısını gösterir; içerik doğruluğu farkı için iki yanıt kümesinin kör insan "
                    "puanlaması gerekir ve bu puanlama yapılmamıştır. İki yanıt kümesi Ek Tablo G'de yan yana verilmiştir."
                ))
                log["llm_only"] += 1
                break
        for p in doc.paragraphs:
            if p.text.startswith("Ek Tablo H. Yönlendirme kararı"):
                head = insert_after(p, "Ek Tablo G. Aynı 33 soruda RAG ve LLM-only yanıtları", "Heading 2")
                cur = head
                for row in LLM_ONLY["rows"]:
                    cur = insert_after(cur, f"{row['id']} | {row['question']}")
                    cur = insert_after(cur, "RAG: " + (row["answer_rag"] or "").strip().replace("\n", " "))
                    cur = insert_after(cur, "LLM-only: " + row["answer_llm_only"].replace("\n", " "))
                break
    doc.save(str(THESIS))
    shutil.copyfile(THESIS, THESIS_COPY)
    return log


if __name__ == "__main__":
    snapshot = db_snapshot()
    build_package(snapshot)
    print("package", OUT_DIR)
    if "--thesis" in sys.argv:
        print("thesis", json.dumps(patch_thesis(snapshot), ensure_ascii=False))
