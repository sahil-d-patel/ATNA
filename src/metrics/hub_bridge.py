"""Hub and bridge composite scores (METR-04, spec §7.6–§7.7)."""

from __future__ import annotations

import pandas as pd

from metrics.percentile import percentile_rank_0_100


_REQ_COLS = (
    "airport_id",
    "pagerank",
    "betweenness",
    "strength_total",
    "degree_total",
)


def add_hub_bridge_scores(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of ``df`` with ``hub_score`` and ``bridge_score`` columns added.

    Inputs must include **all airports in the snapshot** (including explicit zeros where
    applicable), matching the percentile scaling rule (spec §7.5).
    """
    missing = [c for c in _REQ_COLS if c not in df.columns]
    if missing:
        raise ValueError(f"hub/bridge inputs missing columns: {missing}")

    out = df.copy()
    out["airport_id"] = pd.to_numeric(out["airport_id"], errors="raise").astype(int)

    p_strength = percentile_rank_0_100(pd.to_numeric(out["strength_total"], errors="coerce"))
    p_pr = percentile_rank_0_100(pd.to_numeric(out["pagerank"], errors="coerce"))
    p_deg = percentile_rank_0_100(pd.to_numeric(out["degree_total"], errors="coerce"))
    p_bc = percentile_rank_0_100(pd.to_numeric(out["betweenness"], errors="coerce"))

    out["hub_score"] = 0.50 * p_strength + 0.30 * p_pr + 0.20 * p_deg
    out["bridge_score"] = p_bc

    out["hub_score"] = out["hub_score"].astype(float)
    out["bridge_score"] = out["bridge_score"].astype(float)
    return out

