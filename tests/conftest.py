"""Shared pytest fixtures for the ATNA test suite.

Provides the small directed-graph fixture reused across the scenario and
vulnerability tests, plus a module-scoped ETL config fixture that skips its
dependent tests cleanly when the configured raw BTS files are absent (mirroring
the "processed nodes/edges missing" skip used in ``test_metrics_graph.py``).
"""

from __future__ import annotations

import networkx as nx
import pytest

from etl.config import load_config


@pytest.fixture
def fixture_graph() -> nx.DiGraph:
    """Small bidirectional 4-node chain (1-2-3-4) with decreasing edge weights.

    Shared by the scenario engine, ripple/scoring, and vulnerability tests so the
    topology stays identical across them.
    """
    graph = nx.DiGraph()
    graph.add_edge(1, 2, weight=20.0)
    graph.add_edge(2, 1, weight=20.0)
    graph.add_edge(2, 3, weight=10.0)
    graph.add_edge(3, 2, weight=10.0)
    graph.add_edge(3, 4, weight=5.0)
    graph.add_edge(4, 3, weight=5.0)
    return graph


@pytest.fixture(scope="module")
def cfg():
    """Resolved ETL config; skips dependent tests when configured raw files are absent.

    The ETL contract tests need the raw BTS CSVs for the configured snapshot. On a
    machine without that data (data/raw absent) they are skipped with a clear reason
    rather than erroring out.
    """
    c = load_config()
    missing = [
        str(p)
        for p in (c.raw_on_time, c.raw_t100, c.raw_master_airport)
        if not p.is_file()
    ]
    if missing:
        pytest.skip(
            f"configured raw files missing for snapshot {c.snapshot_id}: {missing}"
        )
    return c
