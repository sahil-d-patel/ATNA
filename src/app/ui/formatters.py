"""Display-focused formatting helpers for Streamlit pages.

Every helper accepts ``object`` because the values arrive from DataFrame cells, which
may be Python scalars, NumPy scalars, or one of several pandas missing sentinels. Each
returns ``"N/A"`` for missing input rather than raising, so a single null cell cannot
take down a page render.
"""

from __future__ import annotations

import math
from typing import Any

import pandas as pd

MISSING_DISPLAY = "N/A"


def _is_missing(value: object) -> bool:
    if value is None:
        return True
    if isinstance(value, float):
        return math.isnan(value)
    # Catches pandas missing scalars (pd.NA, pd.NaT) that would otherwise raise
    # TypeError in the float()/int() casts below. Guard against non-scalar inputs
    # where pd.isna returns an array (ambiguous truth value).
    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False


def _as_float(value: object) -> float:
    """Coerce a DataFrame cell to float.

    Typed as ``Any`` at the call boundary because NumPy and pandas scalars satisfy
    ``float()`` at runtime without being expressible in the stubs' accepted union.
    """
    numeric: Any = value
    return float(numeric)


def format_percent(value: object, digits: int = 1) -> str:
    """Format decimals as percentages; missing values become a placeholder."""
    if _is_missing(value):
        return MISSING_DISPLAY
    return f"{_as_float(value) * 100:.{digits}f}%"


def format_score(value: object, digits: int = 3) -> str:
    """Format numeric scores with fixed precision."""
    if _is_missing(value):
        return MISSING_DISPLAY
    return f"{_as_float(value):.{digits}f}"


def format_integer(value: object) -> str:
    """Format integer-like values with thousands separators."""
    if _is_missing(value):
        return MISSING_DISPLAY
    return f"{int(_as_float(value)):,}"
