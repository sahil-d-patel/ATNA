"""Display-focused formatting helpers for Streamlit pages."""

from __future__ import annotations

import math


def _is_missing(value: object) -> bool:
    if value is None:
        return True
    if isinstance(value, float):
        return math.isnan(value)
    return False


def format_percent(value: object, digits: int = 1) -> str:
    """Format decimals as percentages; missing values become placeholder."""
    if _is_missing(value):
        return "N/A"
    return f"{float(value) * 100:.{digits}f}%"


def format_score(value: object, digits: int = 3) -> str:
    """Format numeric scores with fixed precision."""
    if _is_missing(value):
        return "N/A"
    return f"{float(value):.{digits}f}"


def format_integer(value: object) -> str:
    """Format integer-like values with separators."""
    if _is_missing(value):
        return "N/A"
    return f"{int(value):,}"
