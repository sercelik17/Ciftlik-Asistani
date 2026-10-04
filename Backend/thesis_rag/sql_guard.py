from __future__ import annotations

import re

_COMMENT_RE = re.compile(r"(--[^\n]*|/\*.*?\*/)", re.DOTALL)
_FORBIDDEN_RE = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|CREATE|GRANT|"
    r"REVOKE|COPY|EXECUTE|CALL|DO|LOCK|VACUUM|COMMENT|"
    r"SET\s+ROLE|LOAD|IMPORT)\b",
    re.IGNORECASE,
)
_ALLOWED_START_RE = re.compile(
    r"^\s*(WITH|SELECT|EXPLAIN)\b",
    re.IGNORECASE,
)


def normalize_sql(query: str) -> str:
    text = str(query or "").replace("\x00", " ")
    text = _COMMENT_RE.sub(" ", text)
    return text.strip().rstrip(";").strip()


def is_read_only_sql(query: str) -> bool:
    """
    Yalnızca okuma sorgularına izin verir.

    WITH ... SELECT kabul edilir; WITH ... INSERT/UPDATE/DELETE reddedilir.
    """
    sql = normalize_sql(query)
    if not sql:
        return False
    if not _ALLOWED_START_RE.match(sql):
        return False
    if _FORBIDDEN_RE.search(sql):
        return False
    return True


def reject_unsafe_sql(query: str) -> str | None:
    if is_read_only_sql(query):
        return None
    return (
        "Güvenlik nedeniyle yalnızca SELECT / WITH ... SELECT "
        "okuma sorguları çalıştırılabilir. "
        "INSERT, UPDATE, DELETE, DROP ve benzeri komutlar engellenmiştir."
    )
