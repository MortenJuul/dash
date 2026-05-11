from datetime import date
from typing import Any

import pandas as pd

from .config import CHALLENGE_START


def bool_icon(value: Any) -> str:
    if value is True:
        return "✅"
    if value is False:
        return "❌"
    return "—"


def format_status(value: bool | None, good: str, bad: str, unknown: str = "Not logged") -> str:
    if value is True:
        return good
    if value is False:
        return bad
    return unknown


def format_local_dt(value: Any) -> str:
    return value.strftime('%Y-%m-%d %H:%M:%S %Z') if pd.notna(value) else '—'


def safe_int(value: Any, default: int = 0) -> int:
    if pd.isna(value):
        return default
    return int(value)


def safe_float(value: Any, default: float = 0.0) -> float:
    if pd.isna(value):
        return default
    return float(value)


def challenge_day(selected_date: date) -> int:
    return (selected_date - CHALLENGE_START).days + 1


def join_list(values: Any) -> str:
    return ", ".join(values or [])
