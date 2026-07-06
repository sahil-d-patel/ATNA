from __future__ import annotations

from pathlib import Path

import networkx as nx
import pandas as pd

from scenarios.artifacts import SCENARIO_EXPOSURE_COLUMNS, SCENARIOS_COLUMNS
from scenarios.engine import run_scenario
from scenarios.run_scenarios import run_demo_scenarios


def _write_temp_config(tmp_path: Path) -> Path:
    """Write a self-contained atna.yaml + edges.csv rooted entirely under ``tmp_path``.

    ``metrics``/``scenario`` config loaders resolve relative YAML paths against the
    repository root, so the output templates use absolute ``tmp_path`` paths (a
    repo-root join with an absolute path is a no-op). This keeps the demo batch
    reproducible without any real BTS data and without clobbering real artifacts.
    """
    base = tmp_path.resolve()
    processed = base / "data" / "processed" / "2025-12"
    processed.mkdir(parents=True, exist_ok=True)

    edges = pd.DataFrame(
        [
            {"origin_id": 1, "destination_id": 2, "analysis_weight": 20.0, "snapshot_id": "2025-12"},
            {"origin_id": 2, "destination_id": 1, "analysis_weight": 20.0, "snapshot_id": "2025-12"},
            {"origin_id": 2, "destination_id": 3, "analysis_weight": 10.0, "snapshot_id": "2025-12"},
            {"origin_id": 3, "destination_id": 2, "analysis_weight": 10.0, "snapshot_id": "2025-12"},
            {"origin_id": 3, "destination_id": 4, "analysis_weight": 5.0, "snapshot_id": "2025-12"},
            {"origin_id": 4, "destination_id": 3, "analysis_weight": 5.0, "snapshot_id": "2025-12"},
        ]
    )
    edges.to_csv(processed / "edges.csv", index=False)

    processed_tpl = f"{base}/data/processed/{{snapshot_id}}"
    cfg = tmp_path / "atna.yaml"
    cfg.write_text(
        "\n".join(
            [
                'snapshot_id: "2025-12"',
                "raw:",
                f'  on_time_glob: "{base}/data/raw/on_time/{{year}}/on_time_{{year}}_{{month}}.csv"',
                f'  t100_glob: "{base}/data/raw/t100_segment/{{year}}/t100_{{year}}_{{month}}.csv"',
                f'  master_airport_file: "{base}/data/raw/airport_reference/master_coordinate_latest.csv"',
                "output:",
                f'  processed_dir: "{processed_tpl}/"',
                f'  metrics_csv: "{processed_tpl}/metrics.csv"',
                f'  communities_csv: "{processed_tpl}/communities.csv"',
                f'  route_metrics_csv: "{processed_tpl}/route_metrics.csv"',
                f'  scenarios_csv: "{processed_tpl}/scenarios.csv"',
                f'  scenario_exposure_csv: "{processed_tpl}/scenario_exposure.csv"',
            ]
        ),
        encoding="utf-8",
    )
    return cfg


def test_contract_columns_and_key_dtypes(fixture_graph: nx.DiGraph, tmp_path: Path) -> None:
    graph = fixture_graph
    scenario_row, exposure_rows = run_scenario(
        graph,
        snapshot_id="2025-12",
        scenario_type="airport_removal",
        payload={"airport_id": 1},
        created_at="2026-04-09T00:00:00Z",
    )
    scenarios_df = pd.DataFrame([scenario_row])[SCENARIOS_COLUMNS]
    exposure_df = pd.DataFrame(exposure_rows)[SCENARIO_EXPOSURE_COLUMNS]

    scenarios_path = tmp_path / "scenarios.csv"
    exposure_path = tmp_path / "scenario_exposure.csv"
    scenarios_df.to_csv(scenarios_path, index=False)
    exposure_df.to_csv(exposure_path, index=False)

    loaded_scenarios = pd.read_csv(scenarios_path)
    loaded_exposure = pd.read_csv(exposure_path)

    assert list(loaded_scenarios.columns) == SCENARIOS_COLUMNS
    assert list(loaded_exposure.columns) == SCENARIO_EXPOSURE_COLUMNS
    assert loaded_exposure["airport_id"].dtype.kind in {"i", "u"}
    assert loaded_exposure["hop_level"].dtype.kind in {"i", "u"}
    assert loaded_exposure["exposure_rank"].dtype.kind in {"i", "u"}


def test_hop2_rows_are_weaker_than_hop1_for_fixture(fixture_graph: nx.DiGraph) -> None:
    graph = fixture_graph
    _, exposure_rows = run_scenario(
        graph,
        snapshot_id="2025-12",
        scenario_type="airport_removal",
        payload={"airport_id": 1},
        created_at="2026-04-09T00:00:00Z",
    )
    hop1 = [float(r["exposure_score"]) for r in exposure_rows if int(r["hop_level"]) == 1]
    hop2 = [float(r["exposure_score"]) for r in exposure_rows if int(r["hop_level"]) == 2]

    assert hop1 and hop2
    assert max(hop2) < max(hop1)


def test_stronger_scenario_has_higher_impact_and_lower_health(fixture_graph: nx.DiGraph) -> None:
    graph = fixture_graph
    mild, _ = run_scenario(
        graph,
        snapshot_id="2025-12",
        scenario_type="route_removal",
        payload={"origin_id": 3, "destination_id": 4},
        created_at="2026-04-09T00:00:00Z",
    )
    strong, _ = run_scenario(
        graph,
        snapshot_id="2025-12",
        scenario_type="airport_removal",
        payload={"airport_id": 2},
        created_at="2026-04-09T00:00:00Z",
    )

    assert float(strong["impact_score"]) > float(mild["impact_score"])
    assert float(strong["network_health"]) < float(mild["network_health"])


def test_demo_batch_executes_mixed_scenario_types(tmp_path: Path) -> None:
    config_path = _write_temp_config(tmp_path)
    scenarios_path, exposure_path = run_demo_scenarios(config_path=config_path)

    scenarios = pd.read_csv(scenarios_path)
    exposure = pd.read_csv(exposure_path)

    assert len(scenarios) >= 3
    assert {"airport_removal", "route_removal"}.issubset(set(scenarios["scenario_type"]))
    assert not exposure.empty
