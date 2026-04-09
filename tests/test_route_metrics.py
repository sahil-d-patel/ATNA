from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from metrics.config import load_config
from metrics.route_criticality import ROUTE_METRICS_COL_ORDER, build_route_metrics_frame
from metrics.run_metrics import run


def _cfg_for_snapshot(snapshot_id: str):
    base = load_config()
    return type(base)(
        snapshot_id=snapshot_id,
        repo_root=Path("."),
        config_path=Path("config/atna.yaml"),
        raw_on_time=Path("data/raw/on_time"),
        raw_t100=Path("data/raw/t100"),
        raw_master_airport=Path("data/raw/master.csv"),
        processed_dir=Path(f"data/processed/{snapshot_id}"),
        edges_csv=Path(f"data/processed/{snapshot_id}/edges.csv"),
        metrics_csv=Path(f"data/processed/{snapshot_id}/metrics.csv"),
        communities_csv=Path(f"data/processed/{snapshot_id}/communities.csv"),
        route_metrics_csv=Path(f"data/processed/{snapshot_id}/route_metrics.csv"),
    )


def test_cross_community_flag_is_0_or_100_and_matches_partition():
    cfg = _cfg_for_snapshot("2099-01")
    edges = pd.DataFrame(
        {
            "snapshot_id": ["2099-01", "2099-01"],
            "origin_id": [1, 1],
            "destination_id": [2, 3],
            "analysis_weight": [1.0, 1.0],
        }
    )
    metrics = pd.DataFrame({"airport_id": [1, 2, 3], "leiden_community_id": [0, 0, 7]})
    out = build_route_metrics_frame(cfg, edges_df=edges, metrics_df=metrics)
    flags = out.set_index(["origin_id", "destination_id"])["cross_community_flag"].to_dict()
    assert int(flags[(1, 2)]) == 0
    assert int(flags[(1, 3)]) == 100
    assert set(out["cross_community_flag"].astype(int).unique()).issubset({0, 100})


def test_route_criticality_increases_with_percentile_and_cross_community_boost():
    cfg = _cfg_for_snapshot("2099-01")
    edges = pd.DataFrame(
        {
            "snapshot_id": ["2099-01", "2099-01", "2099-01"],
            "origin_id": [1, 1, 2],
            "destination_id": [2, 3, 3],
            "analysis_weight": [1.0, 2.0, 3.0],
        }
    )
    # Make (1->2) and (2->3) cross-community, (1->3) same-community
    metrics = pd.DataFrame({"airport_id": [1, 2, 3], "leiden_community_id": [0, 1, 0]})

    out = build_route_metrics_frame(cfg, edges_df=edges, metrics_df=metrics).set_index(
        ["origin_id", "destination_id"]
    )
    s_12 = float(out.loc[(1, 2), "route_criticality_score"])  # cross, low weight
    s_13 = float(out.loc[(1, 3), "route_criticality_score"])  # same, mid weight
    s_23 = float(out.loc[(2, 3), "route_criticality_score"])  # cross, high weight

    assert s_23 > s_12
    assert s_12 > s_13


def test_run_writes_route_metrics_csv_with_contract_columns_and_sanity(tmp_path: Path):
    cfg = load_config()
    nodes_path = cfg.processed_dir / "nodes.csv"
    edges_path = cfg.processed_dir / "edges.csv"
    if not nodes_path.is_file() or not edges_path.is_file():
        pytest.skip("processed nodes/edges missing for configured snapshot")

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
        communities_csv=(tmp_path / "communities.csv").resolve(),
        route_metrics_csv=(tmp_path / "route_metrics.csv").resolve(),
    )

    _ = run(cfg2)
    assert cfg2.route_metrics_csv.is_file()
    df = pd.read_csv(cfg2.route_metrics_csv)
    assert list(df.columns) == ROUTE_METRICS_COL_ORDER
    assert df["snapshot_id"].astype(str).eq(cfg.snapshot_id).all()

    flags = pd.to_numeric(df["cross_community_flag"], errors="coerce").dropna().astype(int)
    if len(flags) >= 10:
        frac_cross = float((flags == 100).mean())
        if frac_cross in (0.0, 1.0):
            pytest.skip(f"degenerate snapshot: cross-community share is {frac_cross:.0%}")

    w = pd.to_numeric(df["analysis_weight"], errors="coerce")
    s = pd.to_numeric(df["route_criticality_score"], errors="coerce")
    ok = w.notna() & s.notna()
    if int(ok.sum()) >= 10:
        corr = float(np.corrcoef(w[ok].astype(float), s[ok].astype(float))[0, 1])
        if np.isfinite(corr):
            assert abs(corr) < 0.999

