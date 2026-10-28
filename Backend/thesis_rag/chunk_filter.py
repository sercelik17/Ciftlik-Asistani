# -*- coding: utf-8 -*-
"""Kaynakça ve katkı maddesi tablosu gibi yanıta yaramayan parçaları ayıklar."""
from __future__ import annotations

import re

_BIB_MARKERS = (
    "bibliography",
    "references",
    "kaynaklar",
    "kaynakça",
)
_JOURNAL = re.compile(
    r"\b(j\.\s*dairy\s*sci|theriogenology|j\.\s*anim\.\s*sci)\b",
    re.IGNORECASE,
)


def is_low_value_chunk(text: str) -> bool:
    raw = str(text or "").strip()
    if len(raw) < 80:
        return True
    lowered = raw.casefold()
    head = lowered[:120]
    if any(marker in head for marker in _BIB_MARKERS):
        return True
    if lowered.count("et al") >= 3 and _JOURNAL.search(lowered):
        return True
    if "ins no." in lowered and "additive" in lowered:
        return True
    return False
