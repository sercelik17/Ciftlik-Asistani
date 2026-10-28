# -*- coding: utf-8 -*-
"""Kesilmiş, İngilizce veya boş RAG yanıtlarını okunur Türkçe bırakır."""
from __future__ import annotations

import re

INSUFFICIENT = (
    "Mevcut kaynaklarda bu soruyu güvenilir biçimde yanıtlayacak "
    "yeterli bilgi bulunamadı."
)

_LATIN_WORD = re.compile(r"\b[a-z]{4,}\b")
_TR_WORD = re.compile(r"\b[a-zçğıöşü]{4,}\b", re.IGNORECASE)
_KEEP_EN = {
    "mastitis",
    "subklinik",
    "klinik",
    "ketozis",
    "ketosis",
    "colostrum",
    "kolostrum",
    "rumen",
    "holstein",
    "simmental",
    "hybrid",
    "rag",
}


def split_sentences(text: str) -> list[str]:
    text = re.split(
        r"\n\s*kaynaklar\s*:",
        str(text or ""),
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0].strip()
    text = re.sub(r"[ \t]+", " ", text)
    parts = re.split(r"(?<=[.!?])\s+|\n+", text)
    return [p.strip() for p in parts if p.strip()]


def is_english_heavy(sentence: str) -> bool:
    lowered = sentence.casefold()
    latin = [
        w for w in _LATIN_WORD.findall(lowered)
        if w not in _KEEP_EN and not w.startswith("k")
    ]
    turkish_chars = len(re.findall(r"[çğıöşüÇĞİÖŞÜ]", sentence))
    if turkish_chars >= 2:
        return False
    return len(latin) >= 6


def is_complete(sentence: str) -> bool:
    return bool(re.search(r"[.!?…][”\"']?$", sentence.strip()))


def finish_answer(raw: str, max_sentences: int = 4) -> str:
    sentences = split_sentences(raw)
    kept: list[str] = []
    last = len(sentences) - 1
    for index, sentence in enumerate(sentences):
        if is_english_heavy(sentence):
            continue
        if len(re.sub(r"\[K\d+\]", "", sentence)) < 20:
            continue
        if not is_complete(sentence) and index == last:
            continue
        kept.append(sentence)
        if len(kept) >= max_sentences:
            break
    if not kept:
        return INSUFFICIENT
    return " ".join(kept)
