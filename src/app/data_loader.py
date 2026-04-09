"""Cached app artifact loaders with schema guards."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from app.config import AppConfig, load_app_config

try:
    import streamlit as st
except ModuleNotFoundError:  # pragma: no cover - fallback for non-UI test environments
    class _StreamlitFallback:
        @staticmethod
        def cache_data(func=None, **_kwargs):  # type: ignore[no-untyped-def]
            if func is None:
                def decorator(inner):  # type: ignore[no-untyped-def]
                    return inner
                return decorator
            return func

    st = _StreamlitFallback()  # type: ignore[assignment]


REQUIRED_COLUMNS: dict[str, set[str]] = {
    "metrics": {
        "snapshot_id",
        "airport_id",
        "pagerank",
        "betweenness",
        "eigenvector",
        "hub_score",
        "bridge_score",
        "vulnerability_score",
        "leiden_community_id",
    },
    "communities": {
        "snapshot_id",
        "leiden_community_id",
        "community_size",
        "community_traffic",
        "internal_density",
        "top_hub_airport_ids",
        "top_bridge_airport_ids",
    },
    "route_metrics": {
        "snapshot_id",
        "origin_id",
        "destination_id",
        "analysis_weight",
        "cross_community_flag",
        "route_criticality_score",
    },
    "scenarios": {
        "scenario_id",
        "snapshot_id",
        "scenario_type",
        "impact_score",
        "network_health",
        "lcc_loss",
        "reachability_loss",
        "ripple_severity",
        "created_at",
    },
    "scenario_exposure": {
        "scenario_id",
        "airport_id",
        "hop_level",
        "exposure_score",
        "exposure_rank",
    },
}


def _read_csv_checked(path: Path, artifact_name: str, required_columns: set[str]) -> pd.DataFrame:
    if not path.is_file():
        raise ValueError(f"{artifact_name} artifact not found: {path}")
    try:
        df = pd.read_csv(path)
    except Exception as exc:  # pragma: no cover - pandas parser error details vary
        raise ValueError(f"Unable to read {artifact_name} artifact at {path}: {exc}") from exc

    missing = sorted(required_columns - set(df.columns))
    if missing:
        raise ValueError(
            f"{artifact_name} artifact missing required columns: {missing}. "
            f"Found columns: {list(df.columns)}"
        )
    return df


def _snapshot_filter(df: pd.DataFrame, snapshot_id: str) -> pd.DataFrame:
    if "snapshot_id" not in df.columns:
        return df
    filtered = df.loc[df["snapshot_id"] == snapshot_id].copy()
    if filtered.empty:
        raise ValueError(
            f"Artifact contains no rows for snapshot_id '{snapshot_id}'. "
            "Check config/atna.yaml snapshot_id and processed outputs."
        )
    return filtered


@st.cache_data(show_spinner=False)
def _load_metrics_cached(snapshot_id: str, csv_path: str) -> pd.DataFrame:
    df = _read_csv_checked(Path(csv_path), "metrics", REQUIRED_COLUMNS["metrics"])
    return _snapshot_filter(df, snapshot_id)


@st.cache_data(show_spinner=False)
def _load_communities_cached(snapshot_id: str, csv_path: str) -> pd.DataFrame:
    df = _read_csv_checked(Path(csv_path), "communities", REQUIRED_COLUMNS["communities"])
    return _snapshot_filter(df, snapshot_id)


@st.cache_data(show_spinner=False)
def _load_route_metrics_cached(snapshot_id: str, csv_path: str) -> pd.DataFrame:
    df = _read_csv_checked(Path(csv_path), "route_metrics", REQUIRED_COLUMNS["route_metrics"])
    return _snapshot_filter(df, snapshot_id)


@st.cache_data(show_spinner=False)
def _load_scenarios_cached(snapshot_id: str, csv_path: str) -> pd.DataFrame:
    df = _read_csv_checked(Path(csv_path), "scenarios", REQUIRED_COLUMNS["scenarios"])
    return _snapshot_filter(df, snapshot_id)


@st.cache_data(show_spinner=False)
def _load_scenario_exposure_cached(_snapshot_id: str, csv_path: str) -> pd.DataFrame:
    return _read_csv_checked(
        Path(csv_path),
        "scenario_exposure",
        REQUIRED_COLUMNS["scenario_exposure"],
    )


def _resolve_config(config: AppConfig | None) -> AppConfig:
    return config if config is not None else load_app_config()


def load_metrics(config: AppConfig | None = None) -> pd.DataFrame:
    cfg = _resolve_config(config)
    return _load_metrics_cached(cfg.snapshot_id, str(cfg.metrics_csv))


def load_communities(config: AppConfig | None = None) -> pd.DataFrame:
    cfg = _resolve_config(config)
    return _load_communities_cached(cfg.snapshot_id, str(cfg.communities_csv))


def load_route_metrics(config: AppConfig | None = None) -> pd.DataFrame:
    cfg = _resolve_config(config)
    return _load_route_metrics_cached(cfg.snapshot_id, str(cfg.route_metrics_csv))


def load_scenarios(config: AppConfig | None = None) -> pd.DataFrame:
    cfg = _resolve_config(config)
    return _load_scenarios_cached(cfg.snapshot_id, str(cfg.scenarios_csv))


def load_scenario_exposure(config: AppConfig | None = None) -> pd.DataFrame:
    cfg = _resolve_config(config)
    return _load_scenario_exposure_cached(cfg.snapshot_id, str(cfg.scenario_exposure_csv))
