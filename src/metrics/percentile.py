"""Percentile helpers for comparable metric scoring (spec §7.5)."""

from __future__ import annotations

import pandas as pd


def percentile_rank_0_100(series: pd.Series) -> pd.Series:
    """Return percentile ranks scaled to 0–100 for a snapshot-wide metric vector.

    This implements a **percentile rank** mapping P(·) so that different
    metrics (centralities, degrees, etc.) can be compared on a common 0–100 scale.

    **Tie-breaking:** values that are equal receive the same percentile, using the
    "max" rank for the tie group. Concretely, if multiple airports share the
    maximum value, they all map to 100.

    Notes:
        - Callers must pass values for **all airports in the snapshot**, including
          explicit zeros where applicable; this function does not expand the
          universe.
        - NaNs remain NaN in the output.
    """
    s = pd.Series(series, copy=True)
    if len(s) == 0:
        return s.astype(float)

    out = s.rank(method="max", pct=True) * 100.0
    out = out.astype(float)
    out.index = s.index
    return out

