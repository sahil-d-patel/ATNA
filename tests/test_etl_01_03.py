"""Contract and sanity tests for DATA-02/DATA-03 ETL (plan 01-03)."""

from __future__ import annotations

import re
from dataclasses import replace

import numpy as np
import pandas as pd
import pytest

from etl.build_airports import AIRPORTS_COLUMNS, build_airports_table
from etl.build_edges import EDGES_COLUMNS, build_edges_table
from etl.build_nodes import NODES_COLUMNS
from etl.config import load_config, validate_paths
from etl.load_raw import (
    load_on_time,
    load_on_time_us_domestic,
    load_t100,
    load_t100_us_domestic,
    snapshot_year_month,
)


@pytest.fixture(scope="module")
def cfg():
    c = load_config()
    validate_paths(c)
    return c


def test_load_raw_non_empty(cfg):
    validate_paths(cfg)
    ot = load_on_time(cfg)
    t = load_t100(cfg)
    assert len(ot) > 0
    assert len(t) > 0
    y, m = snapshot_year_month(cfg)
    assert (ot["YEAR"] == y).all()
    assert (ot["MONTH"] == m).all()
    assert (t["YEAR"] == y).all()
    assert (t["MONTH"] == m).all()


def test_us_domestic_slices_non_empty(cfg):
    ot_us = load_on_time_us_domestic(cfg)
    t_us = load_t100_us_domestic(cfg)
    assert len(ot_us) > 0
    assert len(t_us) > 0


def test_airports_columns_and_uniqueness(cfg):
    df = build_airports_table(cfg)
    assert list(df.columns) == AIRPORTS_COLUMNS
    assert df["airport_id_canonical"].is_unique


def test_edges_columns_weights_and_route_key(cfg):
    df = build_edges_table(cfg)
    assert list(df.columns) == EDGES_COLUMNS
    np.testing.assert_allclose(
        df["analysis_weight"].values,
        np.log1p(df["flight_count"].astype(float).values),
        rtol=1e-9,
        atol=1e-9,
    )
    pat = re.compile(r"^\d+__\d+__\d{4}-\d{2}$")
    assert df["route_key"].astype(str).str.match(pat).all()
    assert (df["snapshot_id"] == cfg.snapshot_id).all()
    y, m = snapshot_year_month(cfg)
    assert (df["year"] == y).all()
    assert (df["month"] == m).all()


def test_written_csvs_roundtrip(cfg, tmp_path):
    """Write to temp dir to verify CSV writers without clobbering configured output."""
    from etl.build_airports import write_airports_csv
    from etl.build_edges import write_edges_csv
    from etl.build_nodes import write_nodes_csv

    out = tmp_path / "out"
    c = replace(cfg, processed_dir=out.resolve())
    pa = write_airports_csv(c)
    pe = write_edges_csv(c)
    pn = write_nodes_csv(c)
    assert pa.is_file() and pe.is_file() and pn.is_file()
    a = pd.read_csv(pa)
    e = pd.read_csv(pe)
    n = pd.read_csv(pn)
    assert list(a.columns) == AIRPORTS_COLUMNS
    assert list(e.columns) == EDGES_COLUMNS
    assert list(n.columns) == NODES_COLUMNS
