"""Scenario execution adapter for Streamlit UI workflows."""

from __future__ import annotations

from typing import Any

import networkx as nx
import pandas as pd

from app.config import AppConfig, load_app_config
from app.data_loader import load_edges
from app.streamlit_compat import st
from metrics.graph_builder import build_analysis_graph
from scenarios.engine import run_scenario
from scenarios.models import ScenarioType
from scenarios.ripple import build_dependency_weights, normalize_neighbor_shares
from scenarios.scoring import reachable_pairs_count


@st.cache_resource(show_spinner=False)
def _build_baseline_graph_cached(
    snapshot_id: str, edges_csv: str, _edges_df: pd.DataFrame
) -> nx.DiGraph:
    """Build and cache the baseline DiGraph for one snapshot.

    ``_edges_df`` is underscore-prefixed so Streamlit skips hashing the frame; the
    cache key is ``(snapshot_id, edges_csv)``. The scenario engine only ever reads the
    baseline — edits are applied as read-only ``restricted_view`` overlays (see
    ``scenarios.graph_edits``) — so the cached instance is never mutated and can be
    shared safely across reruns.
    """
    return build_analysis_graph(_edges_df)


@st.cache_resource(show_spinner=False)
def _baseline_invariants_cached(
    snapshot_id: str, edges_csv: str, _graph: nx.DiGraph
) -> tuple[dict[int, dict[int, float]], dict[int, dict[int, float]], int]:
    """Cache the baseline-only inputs every scenario would otherwise re-derive.

    Normalized neighbor shares and the baseline reachable-pair count depend solely on
    the unchanged baseline graph, so recomputing them per click makes every scenario
    pay a full dependency rebuild plus an SCC pass before any scenario-specific work
    starts. They are cached alongside the graph and reused for every UI scenario.
    """
    dependency = build_dependency_weights(_graph)
    return (
        dependency,
        normalize_neighbor_shares(dependency),
        reachable_pairs_count(_graph),
    )


def load_baseline_graph(config: AppConfig | None = None) -> nx.DiGraph:
    """Build the canonical baseline graph for scenario execution."""
    cfg = config if config is not None else load_app_config()
    edges_df = load_edges(cfg)
    return _build_baseline_graph_cached(cfg.snapshot_id, str(cfg.edges_csv), edges_df)


@st.cache_resource(show_spinner=False)
def _list_airport_ids_cached(snapshot_id: str, edges_csv: str, _graph: nx.DiGraph) -> list[int]:
    return sorted(int(node) for node in _graph.nodes())


@st.cache_resource(show_spinner=False)
def _list_route_pairs_cached(
    snapshot_id: str, edges_csv: str, _graph: nx.DiGraph
) -> list[tuple[int, int]]:
    return sorted((int(origin), int(destination)) for origin, destination in _graph.edges())


def list_airport_ids(config: AppConfig | None = None) -> list[int]:
    """Return sorted airport ids from the canonical baseline graph."""
    cfg = config if config is not None else load_app_config()
    graph = load_baseline_graph(cfg)
    return _list_airport_ids_cached(cfg.snapshot_id, str(cfg.edges_csv), graph)


def list_route_pairs(config: AppConfig | None = None) -> list[tuple[int, int]]:
    """Return sorted directed route pairs from the canonical baseline graph.

    Cached because the scenario editor rebuilds a selectbox from this on every rerun,
    and at full BTS scale it is a sort over roughly 15,000 tuples each time.
    """
    cfg = config if config is not None else load_app_config()
    graph = load_baseline_graph(cfg)
    return _list_route_pairs_cached(cfg.snapshot_id, str(cfg.edges_csv), graph)


def run_ui_scenario(
    *,
    scenario_type: str,
    payload: dict[str, Any],
    config: AppConfig | None = None,
) -> tuple[dict[str, Any], pd.DataFrame]:
    """Validate UI payload and run canonical scenario engine."""
    cfg = config if config is not None else load_app_config()
    graph = load_baseline_graph(cfg)
    dependency, shares, pre_reachable_pairs = _baseline_invariants_cached(
        cfg.snapshot_id, str(cfg.edges_csv), graph
    )
    normalized_type = ScenarioType(str(scenario_type))
    normalized_payload = _normalize_payload(normalized_type, payload)
    scenario_row, exposure_rows = run_scenario(
        graph,
        snapshot_id=cfg.snapshot_id,
        scenario_type=normalized_type.value,
        payload=normalized_payload,
        precomputed_shares=shares,
        precomputed_dependency=dependency,
        pre_reachable_pairs=pre_reachable_pairs,
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
