from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from metrics.config import load_config
from metrics.hub_bridge import add_hub_bridge_scores
from metrics.run_metrics import _METRICS_COL_ORDER, run


def test_hub_bridge_scores_follow_spec_weights():
    df = pd.DataFrame(
        {
            "airport_id": [1, 2, 3, 4],
            "pagerank": [0.10, 0.40, 0.30, 0.20],
            "betweenness": [0.0, 0.5, 0.2, 0.1],
            "strength_total": [10.0, 20.0, 40.0, 30.0],
            "degree_total": [1, 2, 4, 3],
        }
    )
    out = add_hub_bridge_scores(df)

    # Hub score should rank airport 3 highest (dominates strength + degree and strong PR).
    top_hub = int(out.sort_values("hub_score", ascending=False).iloc[0]["airport_id"])
    assert top_hub == 3

    # Bridge score is percentile(betweenness): airport 2 highest.
    top_bridge = int(out.sort_values("bridge_score", ascending=False).iloc[0]["airport_id"])
    assert top_bridge == 2

    assert out["hub_score"].between(0, 100).all()
    assert out["bridge_score"].between(0, 100).all()


def test_metrics_csv_written_if_processed_inputs_exist(tmp_path: Path):
    """End-to-end smoke: writes metrics.csv with correct columns when snapshot inputs exist."""
    cfg = load_config()
    nodes_path = cfg.processed_dir / "nodes.csv"
    edges_path = cfg.processed_dir / "edges.csv"
    if not nodes_path.is_file() or not edges_path.is_file():
        pytest.skip("processed nodes/edges missing for configured snapshot")

    # Write to a temp location to avoid clobbering real processed artifact during tests.
    cfg2 = type(cfg)(
        snapshot_id=cfg.snapshot_id,
        repo_root=cfg.repo_root,
        config_path=cfg.config_path,
        raw_on_time=cfg.raw_on_time,
        raw_t100=cfg.raw_t100,
        raw_master_airport=cfg.raw_master_airport,
        processed_dir=cfg.processed_dir,
        edges_csv=cfg.edges_csv,
        metrics_csv=(tmp_path / "metrics.csv").resolve(),
        communities_csv=cfg.communities_csv,
        route_metrics_csv=cfg.route_metrics_csv,
    )

    out_path = run(cfg2)
    assert out_path.is_file()

    df = pd.read_csv(out_path)
    assert list(df.columns) == _METRICS_COL_ORDER
    assert df["snapshot_id"].astype(str).eq(cfg.snapshot_id).all()

    # Placeholders until later plans.
    assert df["vulnerability_score"].isna().all()
    assert set(pd.to_numeric(df["leiden_community_id"], errors="coerce").unique()) == {-1}

    # Centralities should be finite (zeros allowed for isolated nodes).
    assert np.isfinite(pd.to_numeric(df["pagerank"], errors="coerce")).all()
    assert np.isfinite(pd.to_numeric(df["betweenness"], errors="coerce")).all()

