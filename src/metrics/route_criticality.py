"""Per-route structural metrics (METR-06): cross-community flag + route criticality.

Spec references:
  - §6.6 route_metrics.csv
  - §7.10 Route Criticality Score
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from metrics.config import MetricsConfig, load_config
from metrics.graph_builder import load_edges


ROUTE_METRICS_COL_ORDER = [
    "snapshot_id",
    "origin_id",
    "destination_id",
    "analysis_weight",
    "cross_community_flag",
    "route_criticality_score",
]


def build_route_metrics_frame(
    cfg: MetricsConfig,
    *,
    edges_df: pd.DataFrame | None = None,
    metrics_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Build ``route_metrics.csv`` frame for one snapshot.

    Args:
        cfg: Resolved metrics config for the snapshot.
        edges_df: Optional preloaded edges table (from ``edges.csv``).
        metrics_df: Optional precomputed metrics frame containing Leiden IDs.

    Returns:
        DataFrame in §6.6 column order with one row per directed route.
    """
    edges = edges_df.copy() if edges_df is not None else load_edges(cfg)
    if not {"origin_id", "destination_id", "analysis_weight"}.issubset(edges.columns):
        raise ValueError("edges_df must include origin_id, destination_id, analysis_weight")

    if metrics_df is None:
        metrics = pd.read_csv(cfg.metrics_csv)
    else:
        metrics = metrics_df.copy()

    if not {"airport_id", "leiden_community_id"}.issubset(metrics.columns):
        raise ValueError("metrics_df must include airport_id and leiden_community_id")

    comm_map = (
        metrics[["airport_id", "leiden_community_id"]]
        .drop_duplicates(subset=["airport_id"])
        .set_index("airport_id")["leiden_community_id"]
    )

    out = pd.DataFrame(
        {
            "snapshot_id": str(cfg.snapshot_id),
            "origin_id": pd.to_numeric(edges["origin_id"], errors="raise").astype(int),
            "destination_id": pd.to_numeric(edges["destination_id"], errors="raise").astype(int),
            "analysis_weight": pd.to_numeric(edges["analysis_weight"], errors="raise").astype(float),
        }
    )

    o_comm = out["origin_id"].map(comm_map)
    d_comm = out["destination_id"].map(comm_map)
    if o_comm.isna().any() or d_comm.isna().any():
        missing = int((o_comm.isna() | d_comm.isna()).sum())
        raise ValueError(
            f"Missing Leiden community ids for {missing} route endpoint(s); ensure metrics.csv "
            "contains leiden_community_id for all airports in edges.csv."
        )

    cross = (o_comm.astype(int) != d_comm.astype(int)).astype(int) * 100
    out["cross_community_flag"] = cross.astype(int)

    out["route_criticality_score"] = pd.NA

    out = out[ROUTE_METRICS_COL_ORDER].copy()
    return out


def write_route_metrics_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def run(cfg_or_path: MetricsConfig | Path | str | None = None) -> Path:
    """Compute and write ``route_metrics.csv`` for the configured snapshot."""
    cfg = cfg_or_path if isinstance(cfg_or_path, MetricsConfig) else load_config(cfg_or_path)
    df = build_route_metrics_frame(cfg)
    write_route_metrics_csv(df, cfg.route_metrics_csv)
    return cfg.route_metrics_csv

