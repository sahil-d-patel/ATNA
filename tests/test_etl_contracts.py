"""Contract and join-sanity tests for DATA-04/DATA-05 (plan 01-04)."""

from __future__ import annotations

from dataclasses import replace

import numpy as np
import pandas as pd
import pytest

from etl.build_airports import AIRPORTS_COLUMNS, build_airports_table
from etl.build_edges import build_edges_table
from etl.build_nodes import NODES_COLUMNS, build_nodes_table
from etl.config import load_config, validate_paths


@pytest.fixture(scope="module")
def cfg():
    c = load_config()
    validate_paths(c)
    return c


def test_nodes_columns_and_strength_identity(cfg):
    nodes = build_nodes_table(cfg)
    assert list(nodes.columns) == NODES_COLUMNS
    assert (nodes["snapshot_id"] == cfg.snapshot_id).all()
    np.testing.assert_allclose(
        nodes["strength_out"].astype(float) + nodes["strength_in"].astype(float),
        nodes["strength_total"].astype(float),
        rtol=1e-9,
        atol=1e-6,
    )
    np.testing.assert_allclose(
        nodes["degree_out"].astype(float) + nodes["degree_in"].astype(float),
        nodes["degree_total"].astype(float),
        rtol=1e-9,
        atol=1e-9,
    )


def test_edge_endpoints_exist_in_airports(cfg):
    """Every edge origin/destination DOT ID appears in airports (§6.1 key)."""
    ap = build_airports_table(cfg)
    keys = set(ap["airport_id_canonical"].dropna().astype(int))
    ed = build_edges_table(cfg)
    origins = set(ed["origin_id"].astype(int))
    dests = set(ed["destination_id"].astype(int))
    missing_o = origins - keys
    missing_d = dests - keys
    assert not missing_o, f"edge origins not in airports: {sorted(missing_o)[:20]}..."
    assert not missing_d, f"edge destinations not in airports: {sorted(missing_d)[:20]}..."


def test_nodes_align_with_airport_universe(cfg):
    """nodes.csv covers the same airport IDs as §6.1 for the snapshot."""
    ap = build_airports_table(cfg)
    nodes = build_nodes_table(cfg)
    a_ids = set(ap["airport_id_canonical"].dropna().astype(int))
    n_ids = set(nodes["airport_id"].dropna().astype(int))
    assert a_ids == n_ids


def test_row_counts_report(cfg):
    """Sanity: non-empty processed slice; nodes row count matches airports."""
    ap = build_airports_table(cfg)
    ed = build_edges_table(cfg)
    nodes = build_nodes_table(cfg)
    assert len(ap) > 0 and len(ed) > 0 and len(nodes) > 0
    assert len(ap) == len(nodes)


def test_written_csvs_contract_roundtrip(cfg, tmp_path):
    """Write airports, edges, nodes to temp dir and verify column contracts."""
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
    assert list(n.columns) == NODES_COLUMNS
    assert len(n) == len(a)
