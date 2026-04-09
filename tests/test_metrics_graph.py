"""Graph construction contracts: METR-01 DiGraph from ``analysis_weight``."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from metrics.config import load_config
from metrics.graph_builder import (
    build_analysis_graph,
    graph_order_and_size,
    load_edges,
)


def test_synthetic_graph_counts_and_weight_sum():
    """Small edge list: node/edge counts and one manual weight check."""
    df = pd.DataFrame(
        {
            "origin_id": [1, 2, 3],
            "destination_id": [2, 3, 1],
            "analysis_weight": [0.5, 1.0, 1.5],
        }
    )
    g = build_analysis_graph(df)
    n, m = graph_order_and_size(g)
    assert n == 3
    assert m == 3
    assert g[1][2]["weight"] == 0.5
    assert sum(d["weight"] for _, _, d in g.edges(data=True)) == pytest.approx(3.0)


def test_nonpositive_analysis_weight_raises():
    """log1p-positive flight counts imply strictly positive ``analysis_weight``."""
    df = pd.DataFrame(
        {
            "origin_id": [1, 2],
            "destination_id": [2, 1],
            "analysis_weight": [1.0, 0.0],
        }
    )
    with pytest.raises(ValueError, match="analysis_weight"):
        build_analysis_graph(df)


def test_processed_edges_contract_if_present():
    """When ``edges.csv`` exists for the configured snapshot, graph matches table shape."""
    cfg = load_config()
    path: Path = cfg.edges_csv
    if not path.is_file():
        pytest.skip(f"No processed edges at {path} (run ETL or use CI fixture)")

    df = load_edges(cfg)

    g = build_analysis_graph(df)
    _, m = graph_order_and_size(g)
    assert m == len(df), "one DiGraph edge per edges.csv row (unique directed pair)"
