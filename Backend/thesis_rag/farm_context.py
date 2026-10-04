from __future__ import annotations

from contextvars import ContextVar

current_farm_id: ContextVar[int | None] = ContextVar(
    "current_farm_id",
    default=None,
)


def farm_sql_clause(alias: str = "") -> str:
    """
    Kullanıcı/işletme izolasyonu için güvenli tamsayı süzgeci.

    alias: 'i.' veya 'a.' gibi tablo öneki.
    """
    farm_id = current_farm_id.get()
    if farm_id is None:
        return ""
    farm_id = int(farm_id)
    column = f"{alias}ciftlik_id" if alias else "ciftlik_id"
    return f" AND COALESCE({column}, 1) = {farm_id}"
