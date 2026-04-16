"""Scenario execution adapter for Streamlit UI workflows."""

from __future__ import annotations

from typing import Any

import networkx as nx
import pandas as pd

from app.config import AppConfig, load_app_config
from app.data_loader import load_edges
from metrics.graph_builder import build_analysis_graph
from scenarios.engine import run_scenario
from scenarios.models import ScenarioType


def load_baseline_graph(config: AppConfig | None = None) -> nx.DiGraph:
    """Build the canonical baseline graph for scenario execution."""
    cfg = config if config is not None else load_app_config()
    edges_df = load_edges(cfg)
    return build_analysis_graph(edges_df)


def list_airport_ids(config: AppConfig | None = None) -> list[int]:
    """Return sorted airport ids from the canonical baseline graph."""
    graph = load_baseline_graph(config)
    return sorted(int(node) for node in graph.nodes())


def list_route_pairs(config: AppConfig | None = None) -> list[tuple[int, int]]:
    """Return sorted directed route pairs from the canonical baseline graph."""
    graph = load_baseline_graph(config)
    return sorted((int(origin), int(destination)) for origin, destination in graph.edges())


def run_ui_scenario(
    *,
    scenario_type: str,
    payload: dict[str, Any],
    config: AppConfig | None = None,
) -> tuple[dict[str, Any], pd.DataFrame]:
    """Validate UI payload and run canonical scenario engine."""
    cfg = config if config is not None else load_app_config()
    graph = load_baseline_graph(cfg)
    normalized_type = ScenarioType(str(scenario_type))
    normalized_payload = _normalize_payload(normalized_type, payload)
    scenario_row, exposure_rows = run_scenario(
        graph,
        snapshot_id=cfg.snapshot_id,
        scenario_type=normalized_type.value,
        payload=normalized_payload,
    )
    exposure_df = pd.DataFrame(exposure_rows)
    if not exposure_df.empty:
        exposure_df = exposure_df.sort_values(
            by=["exposure_rank", "airport_id"], ascending=[True, True]
        ).reset_index(drop=True)
    return scenario_row, exposure_df


def _normalize_payload(scenario_type: ScenarioType, payload: dict[str, Any]) -> dict[str, int]:
    if not isinstance(payload, dict):
        raise TypeError("payload must be a dictionary")

    if scenario_type is ScenarioType.AIRPORT_REMOVAL:
        if "airport_id" not in payload:
            raise ValueError("Airport-removal scenario requires airport_id")
        return {"airport_id": _as_int(payload["airport_id"], "airport_id")}

    required = ("origin_id", "destination_id")
    missing = [key for key in required if key not in payload]
    if missing:
        raise ValueError(f"Route-removal scenario missing required field(s): {missing}")
    origin_id = _as_int(payload["origin_id"], "origin_id")
    destination_id = _as_int(payload["destination_id"], "destination_id")
    if origin_id == destination_id:
        raise ValueError("origin_id and destination_id must be different")
    return {"origin_id": origin_id, "destination_id": destination_id}


def _as_int(value: Any, field_name: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be an integer") from exc
