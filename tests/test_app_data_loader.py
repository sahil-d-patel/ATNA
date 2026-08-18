"""Artifact loader guards: schema validation, snapshot filtering, and cache freshness.

These loaders are the application's only defence against a malformed or stale artifact
directory. A missing column here surfaces as a clear message rather than a traceback
several frames deep inside a page render, and a rebuilt pipeline has to be picked up
without restarting the server.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pandas as pd
import pytest

from app.config import AppConfig, load_app_config
from app.data_loader import (
    label_airports,
    load_airports,
    load_airports_geo,
    load_edges,
    load_metrics,
)

SNAPSHOT_ID = "2025-12"


def _write_metrics(path: Path, snapshot_id: str = SNAPSHOT_ID) -> None:
    pd.DataFrame(
        {
            "snapshot_id": [snapshot_id, snapshot_id],
            "airport_id": [10397, 13930],
            "pagerank": [0.10, 0.09],
            "betweenness": [0.5, 0.4],
            "eigenvector": [0.3, 0.2],
            "hub_score": [99.0, 98.0],
            "bridge_score": [98.0, 100.0],
            "vulnerability_score": [75.0, 80.0],
            "leiden_community_id": [0, 1],
        }
    ).to_csv(path, index=False)


def _write_airports(path: Path) -> None:
    pd.DataFrame(
        {
            "airport_id_canonical": [10397, 13930],
            "airport_code_raw": ["ATL", "ORD"],
            "airport_name": ["Hartsfield-Jackson Atlanta International", "Chicago O'Hare"],
            "city": ["Atlanta, GA", "Chicago, IL"],
            "state": ["GA", "IL"],
            "latitude": [33.6367, 41.9786],
            "longitude": [-84.4281, -87.9048],
        }
    ).to_csv(path, index=False)


@pytest.fixture
def temp_config(tmp_path: Path) -> AppConfig:
    """An AppConfig pointing at a scratch artifact directory."""
    processed = tmp_path / "processed"
    processed.mkdir()
    base = load_app_config()
    return replace(
        base,
        processed_dir=processed,
        airports_csv=processed / "airports.csv",
        edges_csv=processed / "edges.csv",
        nodes_csv=processed / "nodes.csv",
        metrics_csv=processed / "metrics.csv",
    )


def test_missing_artifact_names_the_file(temp_config: AppConfig) -> None:
    with pytest.raises(ValueError, match="metrics artifact not found"):
        load_metrics(temp_config)


def test_missing_columns_are_listed_explicitly(temp_config: AppConfig) -> None:
    """The message must name what is missing, not just that something is."""
    pd.DataFrame({"snapshot_id": [SNAPSHOT_ID], "airport_id": [10397]}).to_csv(
        temp_config.metrics_csv, index=False
    )
    with pytest.raises(ValueError, match="missing required columns") as excinfo:
        load_metrics(temp_config)
    message = str(excinfo.value)
    assert "hub_score" in message
    assert "vulnerability_score" in message


def test_snapshot_mismatch_is_rejected(temp_config: AppConfig) -> None:
    """An artifact for a different month must not silently render as empty."""
    _write_metrics(temp_config.metrics_csv, snapshot_id="1999-01")
    with pytest.raises(ValueError, match="no rows for snapshot_id"):
        load_metrics(temp_config)


def test_rebuilt_artifact_is_reloaded(temp_config: AppConfig) -> None:
    """Caches key on modification time, so a pipeline rerun is picked up."""
    _write_metrics(temp_config.metrics_csv)
    first = load_metrics(temp_config)
    assert len(first.index) == 2

    rebuilt = pd.read_csv(temp_config.metrics_csv).head(1)
    # Bump mtime explicitly: writes inside one test can land in the same clock tick.
    rebuilt.to_csv(temp_config.metrics_csv, index=False)
    import os

    stat = temp_config.metrics_csv.stat()
    os.utime(temp_config.metrics_csv, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1_000_000))

    assert len(load_metrics(temp_config).index) == 1


def test_airports_loader_builds_a_display_label(temp_config: AppConfig) -> None:
    _write_airports(temp_config.airports_csv)
    airports = load_airports(temp_config)
    assert set(airports.columns) >= {"airport_id", "iata_code", "airport_name", "airport_label"}
    atl = airports.loc[airports["iata_code"] == "ATL"].iloc[0]
    assert atl["airport_id"] == 10397
    assert atl["airport_label"].startswith("ATL")


def test_geo_join_attaches_identity_to_metrics(temp_config: AppConfig) -> None:
    _write_metrics(temp_config.metrics_csv)
    _write_airports(temp_config.airports_csv)
    geo = load_airports_geo(temp_config)
    assert len(geo.index) == 2
    assert geo["iata_code"].tolist() == ["ATL", "ORD"]
    assert geo["latitude"].notna().all()


def test_label_airports_supports_route_endpoints(temp_config: AppConfig) -> None:
    """Route tables key on origin_id and destination_id rather than airport_id."""
    _write_airports(temp_config.airports_csv)
    routes = pd.DataFrame({"origin_id": [10397], "destination_id": [13930]})
    labelled = label_airports(routes, temp_config, id_column="origin_id")
    assert labelled["iata_code"].tolist() == ["ATL"]


def test_edges_loader_validates_its_own_contract(temp_config: AppConfig) -> None:
    """Each artifact is checked against its own required columns, not a shared set."""
    _write_metrics(temp_config.edges_csv)  # right shape for metrics, wrong for edges
    with pytest.raises(ValueError, match="edges artifact missing required columns"):
        load_edges(temp_config)
