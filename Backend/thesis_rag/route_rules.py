from __future__ import annotations

from typing import Literal

Route = Literal["RAG", "SQL", "HYBRID", "CHAT"]

_TR_TRANSLATION = str.maketrans({
    "\u00e7": "c",
    "\u011f": "g",
    "\u0131": "i",
    "\u00f6": "o",
    "\u015f": "s",
    "\u00fc": "u",
    "\u00c7": "c",
    "\u011e": "g",
    "\u0130": "i",
    "\u00d6": "o",
    "\u015e": "s",
    "\u00dc": "u",
})


def _normalize(text: str) -> str:
    return str(text).translate(_TR_TRANSLATION).casefold()


CHAT_TERMS = tuple(_normalize(term) for term in (
    "merhaba",
    "selam",
    "tesekkur",
    "tesekkurler",
    "sag ol",
    "sagol",
    "nasilsin",
    "iyi gunler",
    "iyi aksamlar",
    "gunaydin",
    "ne yapabilirsin",
    "kendini tanit",
    "yardimci olur musun",
))

FARM_TERMS = tuple(_normalize(term) for term in (
    "bugun",
    "dun",
    "son sagim",
    "sagim kaydi",
    "sagim kayit",
    "inegim",
    "ineklerim",
    "inekleri",
    "ciftligim",
    "ciftlikte",
    "kupe",
    "toplam sut",
    "kac litre",
    "alarm",
    "riskli",
    "dusus",
    "dusen",
    "verim durumu",
    "veriminde",
    "sut degisim",
    "sut verimi en yuksek",
    "en yuksek sut",
    "en cok sut",
    "en fazla sut",
    "en verimli",
    "en dusuk",
    "suru ortalamasi",
    "uretim trendi",
    "gunluk uretim",
    "sut miktari",
    "sut verisi",
    "sut kaydi",
    "sut dusus",
    "verimindeki",
    "ciftlikteki",
    "ciftligin",
    "inek sayisi",
    "kac inek",
    "irki",
    "irkindaki",
    "ortalama sut",
    "sagilan",
))

FARM_ENTITIES = tuple(_normalize(term) for term in (
    "serap",
    "beyza",
    "boncuk",
    "papatya",
    "lale",
    "tr0001",
    "tr0002",
    "tr0003",
    "tr0004",
    "tr0005",
))

KNOWLEDGE_TERMS = tuple(_normalize(term) for term in (
    "neden",
    "olasi neden",
    "belirti",
    "tedavi",
    "mastitis",
    "ketozis",
    "besleme",
    "rasyon",
    "somatik",
    "hastalik",
    "saglik",
    "ureme",
    "buzagi",
    "sut kalitesi",
    "meme sagligi",
    "kolostrum",
    "kuru donem",
    "bilimsel",
    "kaynak",
    "literatur",
    "hijyen",
    "refah",
    "metabolik",
    "kuru madde",
    "meme",
    "rumen",
    "yemleme",
    "mikrobiyal",
    "barinak",
    "konfor",
    "sogutul",
    "klinik",
    "subklinik",
    "enerji",
    "humma",
    "hipokalsemi",
    "fertilite",
    "gecis donemi",
    "vucut kondisyon",
    "yem tuketimi",
))


def deterministic_route(question: str) -> Route | None:
    q = _normalize(question).strip()

    if any(term in q for term in CHAT_TERMS) and len(q.split()) <= 5:
        return "CHAT"

    has_farm = any(term in q for term in FARM_TERMS) or any(
        name in q for name in FARM_ENTITIES
    )
    has_knowledge = any(term in q for term in KNOWLEDGE_TERMS)
    cow_status = has_farm and any(
        term in q
        for term in ("verim", "durum", "degisim", "nasil", "risk")
    ) and not any(
        term in q
        for term in ("neden", "mastitis", "kaynak", "belirti", "tedavi")
    )

    if cow_status:
        return "SQL"
    if has_farm and has_knowledge:
        return "HYBRID"
    if has_farm:
        return "SQL"
    if has_knowledge:
        return "RAG"
    return None
