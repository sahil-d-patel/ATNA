"""Build ``nodes.csv`` (spec §6.3) from ``edges.csv`` for the MVP snapshot."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from etl.config import AtnaConfig

NODES_COLUMNS = [
    "snapshot_id",
    "airport_id",
    "flights_out",
    "flights_in",
    "strength_out",
    "strength_in",
    "strength_total",
    "degree_out",
    "degree_in",
    "degree_total",
]

# Degrees = counts of edge **rows** in ``edges.csv`` (one row per directed route in the
# monthly aggregate). ``degree_out`` is the number of distinct destinations served;
# ``degree_in`` is the number of distinct origins with flights into the airport.


def _read_edges(cfg: AtnaConfig) -> pd.DataFrame:
    path = cfg.processed_dir / "edges.csv"
    if not path.is_file():
        raise FileNotFoundError(
            f"edges.csv not found at {path}; run build_edges before build_nodes."
        )
    return pd.read_csv(path)


def build_nodes_table(cfg: AtnaConfig, edges: pd.DataFrame | None = None) -> pd.DataFrame:
    """Per-airport node metrics: traffic and log-strength sums from directed edges."""
    if edges is None:
        edges = _read_edges(cfg)
    if edges.empty:
        raise ValueError("edges frame is empty; cannot build nodes.")

    snap = cfg.snapshot_id
    if (edges["snapshot_id"].astype(str) != snap).any():
        raise ValueError(
            f"edges.snapshot_id must all equal config snapshot_id {snap!r}"
        )

    e = edges.copy()
    e["flight_count"] = pd.to_numeric(e["flight_count"], errors="coerce").fillna(0.0)
    e["analysis_weight"] = pd.to_numeric(e["analysis_weight"], errors="coerce").fillna(0.0)

    out = (
        e.groupby("origin_id", sort=False)
        .agg(
            flights_out=("flight_count", "sum"),
            strength_out=("analysis_weight", "sum"),
            degree_out=("destination_id", "count"),
        )
        .reset_index()
        .rename(columns={"origin_id": "airport_id"})
    )
    inn = (
        e.groupby("destination_id", sort=False)
        .agg(
            flights_in=("flight_count", "sum"),
            strength_in=("analysis_weight", "sum"),
            degree_in=("origin_id", "count"),
        )
        .reset_index()
        .rename(columns={"destination_id": "airport_id"})
    )

    nodes = out.merge(inn, on="airport_id", how="outer")
    fill_zero = [
        "flights_out",
        "flights_in",
        "strength_out",
        "strength_in",
        "degree_out",
        "degree_in",
    ]
    for c in fill_zero:
        nodes[c] = pd.to_numeric(nodes[c], errors="coerce").fillna(0.0)

    nodes["airport_id"] = nodes["airport_id"].astype("Int64")
    nodes["flights_out"] = nodes["flights_out"].round().astype("Int64")
    nodes["flights_in"] = nodes["flights_in"].round().astype("Int64")
    nodes["degree_out"] = nodes["degree_out"].astype("Int64")
    nodes["degree_in"] = nodes["degree_in"].astype("Int64")

    nodes["strength_total"] = nodes["strength_out"] + nodes["strength_in"]
    nodes["degree_total"] = nodes["degree_out"] + nodes["degree_in"]

    nodes.insert(0, "snapshot_id", snap)
    nodes = nodes[NODES_COLUMNS]
    nodes = nodes.sort_values("airport_id").reset_index(drop=True)

    # Consistency: strength splits
    chk = nodes["strength_out"] + nodes["strength_in"]
    if not np.allclose(chk.values, nodes["strength_total"].values, rtol=1e-9, atol=1e-6):
        raise AssertionError("strength_total must equal strength_out + strength_in")

    return nodes


def write_nodes_csv(cfg: AtnaConfig, df: pd.DataFrame | None = None) -> Path:
    """Write ``nodes.csv`` under the configured processed directory."""
    if df is None:
        df = build_nodes_table(cfg)
    cfg.processed_dir.mkdir(parents=True, exist_ok=True)
    path = cfg.processed_dir / "nodes.csv"
    df.to_csv(path, index=False)
    return path


def build_nodes(cfg: AtnaConfig) -> Path:
    """Build and write ``nodes.csv``; returns output path."""
    return write_nodes_csv(cfg)
