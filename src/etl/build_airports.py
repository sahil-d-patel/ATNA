"""Build ``airports.csv`` (spec §6.1) for the MVP snapshot."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from etl.config import AtnaConfig
from etl.load_raw import load_master, load_on_time_us_domestic

AIRPORTS_COLUMNS = [
    "airport_id_canonical",
    "airport_code_raw",
    "airport_name",
    "city",
    "state",
    "country",
    "latitude",
    "longitude",
    "timezone",
    "active_flag",
    "source_version",
]


def airport_ids_in_mvp_slice(on_time_us: pd.DataFrame) -> set[int]:
    """Union of origin and destination DOT IDs in the filtered on-time frame."""
    o = on_time_us["ORIGIN_AIRPORT_ID"].dropna()
    d = on_time_us["DEST_AIRPORT_ID"].dropna()
    return set(o.astype(int).unique()) | set(d.astype(int).unique())


def build_airports_table(cfg: AtnaConfig) -> pd.DataFrame:
    """Return §6.1 columns for airports appearing in the U.S. domestic MVP slice."""
    master = load_master(cfg)
    on_time_us = load_on_time_us_domestic(cfg)
    ids = airport_ids_in_mvp_slice(on_time_us)
    sub = master[master["AIRPORT_ID"].isin(ids)].copy()
    if sub.empty:
        raise ValueError("No airports matched master for MVP slice airport IDs")

    # One row per AIRPORT_ID (master should be unique on AIRPORT_ID)
    sub = sub.drop_duplicates(subset=["AIRPORT_ID"], keep="first")

    closed = sub["AIRPORT_IS_CLOSED"].fillna(0)
    try:
        closed_i = pd.to_numeric(closed, errors="coerce").fillna(0).astype(int)
    except (TypeError, ValueError):
        closed_i = closed.astype(str).str.strip().isin(("1", "1.0", "True", "true")).astype(int)

    active = (closed_i == 0).astype(int)

    tz = sub["UTC_LOCAL_TIME_VARIATION"].astype(str).replace({"nan": ""})

    out = pd.DataFrame(
        {
            "airport_id_canonical": sub["AIRPORT_ID"].astype("Int64"),
            "airport_code_raw": sub["AIRPORT"].astype(str),
            "airport_name": sub["DISPLAY_AIRPORT_NAME"].astype(str),
            "city": sub["DISPLAY_AIRPORT_CITY_NAME_FULL"].astype(str),
            "state": sub["AIRPORT_STATE_CODE"].astype(str),
            "country": sub["AIRPORT_COUNTRY_CODE_ISO"].astype(str),
            "latitude": pd.to_numeric(sub["LATITUDE"], errors="coerce"),
            "longitude": pd.to_numeric(sub["LONGITUDE"], errors="coerce"),
            "timezone": tz,
            "active_flag": active,
            "source_version": "BTS_master_coordinate_latest",
        }
    )
    out = out[AIRPORTS_COLUMNS]
    out = out.sort_values("airport_id_canonical").reset_index(drop=True)
    return out


def write_airports_csv(cfg: AtnaConfig, df: pd.DataFrame | None = None) -> Path:
    """Write ``airports.csv`` under the configured processed directory."""
    if df is None:
        df = build_airports_table(cfg)
    cfg.processed_dir.mkdir(parents=True, exist_ok=True)
    path = cfg.processed_dir / "airports.csv"
    df.to_csv(path, index=False)
    return path


def build_airports(cfg: AtnaConfig) -> Path:
    """Build and write ``airports.csv``; returns output path."""
    return write_airports_csv(cfg)
