"""Load raw BTS CSVs for the configured MVP snapshot.

Column mapping (raw → spec artifacts):

**Master Coordinate** → ``airports.csv`` (via ``build_airports``):

- ``AIRPORT_ID`` → ``airport_id_canonical`` (canonical graph key; join on IDs not IATA)
- ``AIRPORT`` → ``airport_code_raw``
- ``DISPLAY_AIRPORT_NAME`` → ``airport_name``
- ``DISPLAY_AIRPORT_CITY_NAME_FULL`` → ``city``
- ``AIRPORT_STATE_CODE`` → ``state``
- ``AIRPORT_COUNTRY_CODE_ISO`` / ``AIRPORT_COUNTRY_NAME`` → ``country``
- ``LATITUDE`` / ``LONGITUDE`` → ``latitude`` / ``longitude``
- ``UTC_LOCAL_TIME_VARIATION`` → ``timezone``
- ``AIRPORT_IS_CLOSED`` → ``active_flag`` (inverted: active = not closed)

**On-Time** → ``edges.csv`` aggregates (via ``build_edges``):

- ``YEAR``, ``MONTH`` → snapshot filter
- ``ORIGIN_AIRPORT_ID``, ``DEST_AIRPORT_ID`` → ``origin_id`` / ``destination_id`` (directed edges)
- ``ARR_DELAY`` → ``avg_arr_delay``, ``pct_delayed`` (with cancelled rows excluded for ops counts)
- ``CANCELLED``, ``DIVERTED`` → filter completed operations

**T-100 Segment** → ``passenger_count``, ``seat_count`` (and cross-check weights):

- ``ORIGIN_AIRPORT_ID``, ``DEST_AIRPORT_ID`` → route keys (same ID join as on-time)
- ``PASSENGERS``, ``SEATS``, ``DEPARTURES_PERFORMED`` → summed per route

U.S. domestic slice: keep rows whose origin and destination ``AIRPORT_ID`` map to
``AIRPORT_COUNTRY_CODE_ISO == \"US\"`` in master (see ``data/reference/field_selection_notes.md``).
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from etl.config import AtnaConfig, validate_paths

# Preserve BTS integer IDs without float coercion
_INT_COLS_MASTER = {"AIRPORT_SEQ_ID", "AIRPORT_ID", "CITY_MARKET_ID"}
_INT_COLS_ON_TIME = {
    "YEAR",
    "MONTH",
    "OP_CARRIER_AIRLINE_ID",
    "ORIGIN_AIRPORT_ID",
    "ORIGIN_AIRPORT_SEQ_ID",
    "ORIGIN_CITY_MARKET_ID",
    "DEST_AIRPORT_ID",
    "DEST_AIRPORT_SEQ_ID",
    "DEST_CITY_MARKET_ID",
}
_INT_COLS_T100 = {"YEAR", "MONTH", "ORIGIN_AIRPORT_ID", "DEST_AIRPORT_ID"}


def _read_csv_typed(path: Path, int_columns: set[str]) -> pd.DataFrame:
    """Read CSV with integer ID columns as pandas Int64 (nullable)."""
    df = pd.read_csv(path, low_memory=False)
    for col in int_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")
    return df


def read_master_airport_file(path: Path) -> pd.DataFrame:
    """Load full master coordinate file (all airports)."""
    return _read_csv_typed(path, _INT_COLS_MASTER)


def read_on_time_file(path: Path, year: int, month: int) -> pd.DataFrame:
    """Load on-time CSV and keep rows for ``year`` / ``month``."""
    df = _read_csv_typed(path, _INT_COLS_ON_TIME)
    if "YEAR" not in df.columns or "MONTH" not in df.columns:
        raise ValueError(f"On-time file missing YEAR/MONTH: {path}")
    out = df[(df["YEAR"] == year) & (df["MONTH"] == month)].copy()
    return out


def read_t100_file(path: Path, year: int, month: int) -> pd.DataFrame:
    """Load T-100 segment CSV and keep rows for ``year`` / ``month``."""
    df = _read_csv_typed(path, _INT_COLS_T100)
    for col in ("PASSENGERS", "SEATS", "DEPARTURES_SCHEDULED", "DEPARTURES_PERFORMED"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    if "YEAR" not in df.columns or "MONTH" not in df.columns:
        raise ValueError(f"T-100 file missing YEAR/MONTH: {path}")
    out = df[(df["YEAR"] == year) & (df["MONTH"] == month)].copy()
    return out


def us_airport_ids(master: pd.DataFrame) -> set[int]:
    """DOT airport IDs for U.S. airports per master country code."""
    if "AIRPORT_COUNTRY_CODE_ISO" not in master.columns:
        raise ValueError("Master missing AIRPORT_COUNTRY_CODE_ISO")
    us = master.loc[master["AIRPORT_COUNTRY_CODE_ISO"].astype(str).str.upper() == "US"]
    return set(us["AIRPORT_ID"].dropna().astype(int))


def filter_us_domestic_on_time(on_time: pd.DataFrame, master: pd.DataFrame) -> pd.DataFrame:
    """Keep on-time rows where origin and destination are U.S. airports in master."""
    us_ids = us_airport_ids(master)
    o = on_time["ORIGIN_AIRPORT_ID"]
    d = on_time["DEST_AIRPORT_ID"]
    mask = o.isin(us_ids) & d.isin(us_ids)
    return on_time.loc[mask].copy()


def filter_us_domestic_t100(t100: pd.DataFrame, master: pd.DataFrame) -> pd.DataFrame:
    """Keep T-100 rows where origin and destination are U.S. airports in master."""
    us_ids = us_airport_ids(master)
    o = t100["ORIGIN_AIRPORT_ID"]
    d = t100["DEST_AIRPORT_ID"]
    mask = o.isin(us_ids) & d.isin(us_ids)
    return t100.loc[mask].copy()


def snapshot_year_month(cfg: AtnaConfig) -> tuple[int, int]:
    y, m = cfg.snapshot_id.split("-", 1)
    return int(y), int(m)


def load_master(cfg: AtnaConfig) -> pd.DataFrame:
    """Load master airport reference (full table)."""
    return read_master_airport_file(cfg.raw_master_airport)


def load_on_time(cfg: AtnaConfig) -> pd.DataFrame:
    """Load on-time rows for the configured snapshot month (unfiltered by country)."""
    y, m = snapshot_year_month(cfg)
    return read_on_time_file(cfg.raw_on_time, y, m)


def load_t100(cfg: AtnaConfig) -> pd.DataFrame:
    """Load T-100 rows for the configured snapshot month (unfiltered by country)."""
    y, m = snapshot_year_month(cfg)
    return read_t100_file(cfg.raw_t100, y, m)


def load_on_time_us_domestic(cfg: AtnaConfig) -> pd.DataFrame:
    """On-time for snapshot month, U.S.–U.S. legs only."""
    master = load_master(cfg)
    ot = load_on_time(cfg)
    return filter_us_domestic_on_time(ot, master)


def load_t100_us_domestic(cfg: AtnaConfig) -> pd.DataFrame:
    """T-100 for snapshot month, U.S.–U.S. legs only."""
    master = load_master(cfg)
    t = load_t100(cfg)
    return filter_us_domestic_t100(t, master)


def assert_raw_files_exist(cfg: AtnaConfig) -> None:
    """Raise ``FileNotFoundError`` if configured raw inputs are missing."""
    validate_paths(cfg)
