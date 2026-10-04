from __future__ import annotations

import re

DIAGNOSIS_PATTERNS = (
    r"\bmastitis\s+var\s+m[ıi]\b",
    r"\btanı\s+koy",
    r"\bteşhis\b",
    r"\bantibiyotik\b",
    r"\bilaç\s+ver",
    r"\bdoz\b",
    r"\btedavi\s+et",
    r"\bpenisilin\b",
    r"\bceftiofur\b",
    r"\bhasta\s+m[ıi]\b",
)

VETERINARY_DISCLAIMER = (
    "Bu sistem veteriner hekim tanısının yerine geçmez. "
    "Kesin hastalık tanısı konulmaz; antibiyotik, ilaç veya doz önerilmez. "
    "Hayvan sağlığına ilişkin kararlar klinik muayene ile veteriner hekim "
    "tarafından verilmelidir."
)


def is_diagnosis_or_treatment_request(question: str) -> bool:
    q = str(question or "").casefold()
    return any(re.search(pattern, q) for pattern in DIAGNOSIS_PATTERNS)


def ensure_veterinary_disclaimer(answer: str) -> str:
    text = str(answer or "").strip()
    if "veteriner hekim" in text.casefold():
        return text
    if not text:
        return VETERINARY_DISCLAIMER
    return f"{text}\n\n{VETERINARY_DISCLAIMER}"


def refuse_diagnosis_answer() -> str:
    return (
        "Bu soru kesin bir hastalık tanısı veya ilaç/antibiyotik kararı "
        "içermektedir. Sistem bu tür kararları veremez. "
        f"{VETERINARY_DISCLAIMER}"
    )
