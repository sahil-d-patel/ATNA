"""Build a directed weighted analysis graph from processed ``edges.csv`` (METR-01, spec §7.2)."""

from __future__ import annotations

from pathlib import Path
from typing import Union

import networkx as nx
import pandas as pd

from metrics.config import MetricsConfig, load_config

# Columns required in on-disk ``edges.csv`` from ETL
_FILE_COLUMNS = ("origin_id", "destination_id", "analysis_weight", "snapshot_id")

# Columns required to build the analysis ``DiGraph``
_GRAPH_COLUMNS = ("origin_id", "destination_id", "analysis_weight")


def load_edges(
    cfg_or_path: Union[MetricsConfig, Path, None] = None,
    *,
    snapshot_id: str | None = None,
) -> pd.DataFrame:
    """Load ``edges.csv`` as a DataFrame.

    Args:
        cfg_or_path: ``MetricsConfig`` (uses ``edges_csv``), a path to ``edges.csv``, or
            ``None`` to load default config and that snapshot's ``edges.csv``.
        snapshot_id: If set, keep only rows where ``snapshot_id`` column matches. If
            ``cfg_or_path`` is ``MetricsConfig`` and this is omitted, uses
            ``cfg.snapshot_id``.

    Returns:
        Edge table with at least ``origin_id``, ``destination_id``, ``analysis_weight``.
    """
    if isinstance(cfg_or_path, Path):
        path = cfg_or_path
        snap_filter = snapshot_id
    elif isinstance(cfg_or_path, MetricsConfig):
        path = cfg_or_path.edges_csv
        snap_filter = snapshot_id if snapshot_id is not None else cfg_or_path.snapshot_id
    else:
        cfg = load_config()
        path = cfg.edges_csv
        snap_filter = snapshot_id if snapshot_id is not None else cfg.snapshot_id

    df = pd.read_csv(path)
    _validate_file_columns(df)
    if snap_filter is not None:
        if "snapshot_id" not in df.columns:
            raise ValueError("edges frame has no snapshot_id column; cannot filter")
        df = df[df["snapshot_id"].astype(str) == snap_filter].copy()
    return df.reset_index(drop=True)


def _validate_file_columns(df: pd.DataFrame) -> None:
    missing = [c for c in _FILE_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"edges.csv missing required columns: {missing}")


def _assert_one_row_per_directed_pair(edges_df: pd.DataFrame) -> None:
    """``edges.csv`` invariant (Phase 1): one row per (origin_id, destination_id)."""
    key = ["origin_id", "destination_id"]
    dup = edges_df.duplicated(subset=key, keep=False)
    if dup.any():
        n = int(dup.sum())
        raise ValueError(
            f"Expected one row per directed pair; found {n} duplicate route row(s). "
            "Resolve upstream in ETL or define an aggregation policy before building the graph."
        )


def build_analysis_graph(edges_df: pd.DataFrame) -> nx.DiGraph:
    """Build a **directed** graph with ``weight = analysis_weight`` only (spec §7.2).

    **Multi-edge policy:** The MVP pipeline emits exactly one row per directed airport
    pair. Duplicate ``(origin_id, destination_id)`` rows are treated as an error; we
    do not sum weights here (that would hide upstream duplication).

    ``flight_count`` and other columns are ignored for edge weights; use them only for
    QA or display.

    **Weights:** ``analysis_weight`` must be finite and strictly positive (``log1p`` of
    positive flight counts per spec §6.2).
    """
    _validate_graph_columns(edges_df)
    _assert_positive_analysis_weights(edges_df)
    _assert_one_row_per_directed_pair(edges_df)

    g = nx.DiGraph()
    for row in edges_df.itertuples(index=False):
        o = int(row.origin_id)
        d = int(row.destination_id)
        w = float(row.analysis_weight)
        g.add_edge(o, d, weight=w)
    return g


def _validate_graph_columns(df: pd.DataFrame) -> None:
    missing = [c for c in _GRAPH_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"edges frame missing columns for graph build: {missing}")


def _assert_positive_analysis_weights(edges_df: pd.DataFrame) -> None:
    w = pd.to_numeric(edges_df["analysis_weight"], errors="coerce")
    if w.isna().any() or (w <= 0).any():
        raise ValueError(
            "analysis_weight must be finite and > 0 for every edge (expected log1p of "
            "positive flight_count per spec §6.2)"
        )


def graph_order_and_size(g: nx.DiGraph) -> tuple[int, int]:
    """Return ``(number_of_nodes, number_of_edges)``."""
    return g.number_of_nodes(), g.number_of_edges()
