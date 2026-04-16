"""Table helpers and validations for Phase 2 metrics (METR-02 QA)."""

from __future__ import annotations

from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd

from metrics.config import MetricsConfig, load_config


_NODES_REQUIRED = (
    "snapshot_id",
    "airport_id",
    "strength_out",
    "strength_in",
    "strength_total",
    "degree_out",
    "degree_in",
    "degree_total",
)


def nodes_csv_path(cfg: MetricsConfig) -> Path:
    return (cfg.processed_dir / "nodes.csv").resolve()


def load_nodes(cfg_or_path: MetricsConfig | Path | None = None) -> pd.DataFrame:
    """Load processed ``nodes.csv`` for the configured snapshot."""
    if isinstance(cfg_or_path, Path):
        path = cfg_or_path
    elif isinstance(cfg_or_path, MetricsConfig):
        path = nodes_csv_path(cfg_or_path)
    else:
        cfg = load_config()
        path = nodes_csv_path(cfg)

    df = pd.read_csv(path)
    missing = [c for c in _NODES_REQUIRED if c not in df.columns]
    if missing:
        raise ValueError(f"nodes.csv missing required columns: {missing}")
    df["airport_id"] = pd.to_numeric(df["airport_id"], errors="raise").astype(int)
    df["snapshot_id"] = df["snapshot_id"].astype(str)
    return df


def compute_strength_degree_from_graph(G: nx.DiGraph) -> pd.DataFrame:
    """Compute strength/degree from the analysis DiGraph using edge ``weight``."""
    nodes = list(G.nodes())
    if not nodes:
        return pd.DataFrame(
            columns=[
                "airport_id",
                "strength_out",
                "strength_in",
                "strength_total",
                "degree_out",
                "degree_in",
                "degree_total",
            ]
        )

    strength_out = {}
    strength_in = {}
    for n in nodes:
        out_w = 0.0
        for _, _, w in G.out_edges(n, data="weight"):
            out_w += float(w)
        in_w = 0.0
        for _, _, w in G.in_edges(n, data="weight"):
            in_w += float(w)
        strength_out[n] = out_w
        strength_in[n] = in_w

    deg_out = dict(G.out_degree(nodes))
    deg_in = dict(G.in_degree(nodes))

    df = pd.DataFrame(
        {
            "airport_id": pd.Series(nodes, dtype=int),
            "strength_out": pd.Series(strength_out, dtype=float).reindex(nodes).to_numpy(),
            "strength_in": pd.Series(strength_in, dtype=float).reindex(nodes).to_numpy(),
            "degree_out": pd.Series(deg_out, dtype=int).reindex(nodes).to_numpy(),
            "degree_in": pd.Series(deg_in, dtype=int).reindex(nodes).to_numpy(),
        }
    )
    df["strength_total"] = df["strength_out"] + df["strength_in"]
    df["degree_total"] = df["degree_out"] + df["degree_in"]
    return df


def assert_metr02_nodes_match_graph(
    G: nx.DiGraph,
    nodes_df: pd.DataFrame,
    *,
    rtol: float = 1e-9,
    atol: float = 1e-9,
) -> None:
    """Fail-fast cross-check: graph-derived strength/degree match processed ``nodes.csv``.

    - Strength uses sum of edge ``weight`` values.
    - Degree uses integer neighbor counts (one edge per directed pair per METR-01 invariant).
    """
    required = [c for c in _NODES_REQUIRED if c in nodes_df.columns]
    missing = [c for c in _NODES_REQUIRED if c not in nodes_df.columns]
    if missing:
        raise ValueError(f"nodes_df missing required columns: {missing}")

    calc = compute_strength_degree_from_graph(G)
    base = nodes_df[required].copy()
    base["airport_id"] = pd.to_numeric(base["airport_id"], errors="raise").astype(int)

    merged = base.merge(calc, on="airport_id", how="left", suffixes=("", "_calc"))
    if merged["strength_total_calc"].isna().any():
        missing_ids = merged.loc[merged["strength_total_calc"].isna(), "airport_id"].tolist()
        raise AssertionError(
            "METR-02: Graph is missing airports present in nodes.csv (add isolated nodes "
            f"to DiGraph before validation). Missing airport_id(s): {missing_ids[:20]}"
        )

    for col in ("degree_out", "degree_in", "degree_total"):
        a = merged[col].astype(int).to_numpy()
        b = merged[f"{col}_calc"].astype(int).to_numpy()
        if not np.array_equal(a, b):
            idx = int(np.argmax(a != b))
            raise AssertionError(
                f"METR-02 degree mismatch for airport_id={int(merged.iloc[idx]['airport_id'])}: "
                f"nodes.csv {col}={int(a[idx])} vs graph {col}={int(b[idx])} (expected exact equality)"
            )

    for col in ("strength_out", "strength_in", "strength_total"):
        a = pd.to_numeric(merged[col], errors="coerce").to_numpy(dtype=float)
        b = pd.to_numeric(merged[f"{col}_calc"], errors="coerce").to_numpy(dtype=float)
        ok = np.isclose(a, b, rtol=rtol, atol=atol, equal_nan=True)
        if not bool(np.all(ok)):
            idx = int(np.argmax(~ok))
            raise AssertionError(
                f"METR-02 strength mismatch for airport_id={int(merged.iloc[idx]['airport_id'])}: "
                f"nodes.csv {col}={a[idx]} vs graph {col}={b[idx]} "
                f"(tolerance rtol={rtol}, atol={atol})"
            )

