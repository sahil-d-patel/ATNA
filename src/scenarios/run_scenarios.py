"""Run deterministic demo scenarios and persist scenario artifacts."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import networkx as nx

from metrics.config import load_config
from metrics.graph_builder import build_analysis_graph, load_edges
from scenarios.artifacts import write_scenario_exposure_csv, write_scenarios_csv
from scenarios.config import ScenarioConfig, load_scenario_config
from scenarios.engine import run_scenario
from scenarios.models import ScenarioType


def deterministic_demo_scenarios(graph: nx.DiGraph) -> list[dict[str, Any]]:
    """Build a deterministic mixed demo set (>=3) from graph topology."""
    nodes = sorted(int(node) for node in graph.nodes())
    if len(nodes) < 2:
        raise ValueError("Need at least two airports to build demo scenarios")

    weighted_edges = sorted(
        (
            (int(u), int(v), float(data.get("weight", 0.0)))
            for u, v, data in graph.edges(data=True)
        ),
        key=lambda item: (-item[2], item[0], item[1]),
    )
    if not weighted_edges:
        raise ValueError("Need at least one route to build demo scenarios")

    airport_primary = max(nodes, key=lambda node: (graph.degree(node), -node))
    airport_secondary = min(node for node in nodes if node != airport_primary)
    route_origin, route_destination, _ = weighted_edges[0]

    return [
        {
            "scenario_type": ScenarioType.AIRPORT_REMOVAL.value,
            "payload": {"airport_id": airport_primary},
        },
        {
            "scenario_type": ScenarioType.ROUTE_REMOVAL.value,
            "payload": {
                "origin_id": route_origin,
                "destination_id": route_destination,
            },
        },
        {
            "scenario_type": ScenarioType.AIRPORT_REMOVAL.value,
            "payload": {"airport_id": airport_secondary},
        },
    ]


def run_demo_scenarios(config_path: Path | str | None = None) -> tuple[Path, Path]:
    """Execute deterministic demo scenarios and write both artifact tables."""
    metrics_cfg = load_config(config_path)
    scenario_cfg: ScenarioConfig = load_scenario_config(config_path)

    edges = load_edges(metrics_cfg)
    graph = build_analysis_graph(edges)
    demo_set = deterministic_demo_scenarios(graph)

    scenario_rows: list[dict[str, Any]] = []
    exposure_rows: list[dict[str, Any]] = []
    for request in demo_set:
        scenario_row, scenario_exposure_rows = run_scenario(
            graph,
            snapshot_id=scenario_cfg.snapshot_id,
            scenario_type=request["scenario_type"],
            payload=request["payload"],
        )
        scenario_rows.append(scenario_row)
        exposure_rows.extend(scenario_exposure_rows)

    write_scenarios_csv(scenario_rows, scenario_cfg.scenarios_csv)
    write_scenario_exposure_csv(exposure_rows, scenario_cfg.scenario_exposure_csv)
    return scenario_cfg.scenarios_csv, scenario_cfg.scenario_exposure_csv


def main() -> None:
    scenarios_path, exposure_path = run_demo_scenarios()
    print(f"wrote scenarios: {scenarios_path}")
    print(f"wrote exposure: {exposure_path}")


if __name__ == "__main__":
    main()
