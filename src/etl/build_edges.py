"""Build ``edges.csv`` (spec §6.2) for the MVP snapshot."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from etl.config import AtnaConfig
from etl.load_raw import load_on_time_us_domestic, load_t100_us_domestic, snapshot_year_month

EDGES_COLUMNS = [
    "snapshot_id",
    "year",
    "month",
    "origin_id",
    "destination_id",
    "flight_count",
    "passenger_count",
    "seat_count",
    "avg_arr_delay",
    "pct_delayed",
    "analysis_weight",
    "route_key",
]

# BTS-style "late" arrival (minutes) for pct_delayed
DELAY_THRESHOLD_MIN = 15.0


def _aggregate_on_time_routes(completed: pd.DataFrame) -> pd.DataFrame:
    """Per directed route: flight counts and delay stats from completed on-time rows."""
    df = completed.copy()
    df["_arr"] = pd.to_numeric(df["ARR_DELAY"], errors="coerce")
    df["_late"] = (df["_arr"] > DELAY_THRESHOLD_MIN) & df["_arr"].notna()
    df["_valid"] = df["_arr"].notna()
    keys = ["ORIGIN_AIRPORT_ID", "DEST_AIRPORT_ID"]
    agg = df.groupby(keys, sort=False).agg(
        flight_count=("ORIGIN_AIRPORT_ID", "count"),
        avg_arr_delay=("_arr", "mean"),
        _late_sum=("_late", "sum"),
        _valid_sum=("_valid", "sum"),
    )
    agg["pct_delayed"] = np.where(
        agg["_valid_sum"] > 0, agg["_late_sum"] / agg["_valid_sum"], np.nan
    )
    agg = agg.drop(columns=["_late_sum", "_valid_sum"]).reset_index()
    return agg


def _aggregate_t100_routes(t100_us: pd.DataFrame) -> pd.DataFrame:
    """Sum passengers, seats, and departures performed per directed route."""
    g = t100_us.groupby(["ORIGIN_AIRPORT_ID", "DEST_AIRPORT_ID"], as_index=False).agg(
        passenger_count=("PASSENGERS", "sum"),
        seat_count=("SEATS", "sum"),
        departures_performed=("DEPARTURES_PERFORMED", "sum"),
    )
    return g


def build_edges_table(cfg: AtnaConfig) -> pd.DataFrame:
    """Directed edges for the snapshot: on-time ops + T-100 passenger/seat totals."""
    on_time_us = load_on_time_us_domestic(cfg)
    cancelled = pd.to_numeric(on_time_us["CANCELLED"], errors="coerce").fillna(1)
    completed = on_time_us[cancelled == 0].copy()
    if completed.empty:
        raise ValueError("No completed (non-cancelled) flights in U.S. domestic slice")

    ot_agg = _aggregate_on_time_routes(completed)
    ot_agg = ot_agg.rename(
        columns={
            "ORIGIN_AIRPORT_ID": "origin_id",
            "DEST_AIRPORT_ID": "destination_id",
        }
    )

    t100_us = load_t100_us_domestic(cfg)
    t_agg = _aggregate_t100_routes(t100_us)
    t_agg = t_agg.rename(
        columns={
            "ORIGIN_AIRPORT_ID": "origin_id",
            "DEST_AIRPORT_ID": "destination_id",
        }
    )

    edges = ot_agg.merge(
        t_agg[["origin_id", "destination_id", "passenger_count", "seat_count"]],
        on=["origin_id", "destination_id"],
        how="left",
    )
    edges["passenger_count"] = edges["passenger_count"].fillna(0.0)
    edges["seat_count"] = edges["seat_count"].fillna(0.0)

    year, month = snapshot_year_month(cfg)
    snap = cfg.snapshot_id
    edges.insert(0, "snapshot_id", snap)
    edges.insert(1, "year", year)
    edges.insert(2, "month", month)

    edges["analysis_weight"] = np.log1p(edges["flight_count"].astype(float))
    edges["route_key"] = (
        edges["origin_id"].astype(str)
        + "__"
        + edges["destination_id"].astype(str)
        + "__"
        + snap
    )

    edges = edges[EDGES_COLUMNS]
    edges = edges.sort_values(["origin_id", "destination_id"]).reset_index(drop=True)
    return edges


def write_edges_csv(cfg: AtnaConfig, df: pd.DataFrame | None = None) -> Path:
    """Write ``edges.csv`` under the configured processed directory."""
    if df is None:
        df = build_edges_table(cfg)
    cfg.processed_dir.mkdir(parents=True, exist_ok=True)
    path = cfg.processed_dir / "edges.csv"
    df.to_csv(path, index=False)
    return path


def build_edges(cfg: AtnaConfig) -> Path:
    """Build and write ``edges.csv``; returns output path."""
    return write_edges_csv(cfg)
