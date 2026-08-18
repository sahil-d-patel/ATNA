"""Cached app artifact loaders with schema guards."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from app.config import AppConfig, load_app_config
from app.streamlit_compat import st

REQUIRED_COLUMNS: dict[str, set[str]] = {
    "nodes": {
        "snapshot_id",
        "airport_id",
        "flights_out",
        "flights_in",
        "strength_out",
        "strength_in",
        "strength_total",
        "degree_out",
        "degree_in",
        "degree_total",
    },
    "airports": {
        "airport_id_canonical",
        "airport_code_raw",
        "airport_name",
        "city",
        "state",
        "latitude",
        "longitude",
    },
    "edges": {
        "snapshot_id",
        "year",
        "month",
        "origin_id",
        "destination_id",
        "flight_count",
        "passenger_count",
        "seat_count",
        "avg_arr_delay",
        "pct_delayed",
        "analysis_weight",
        "route_key",
    },
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
def _read_artifact_cached(
    csv_path: str, artifact_name: str, mtime_ns: int, snapshot_id: str | None
) -> pd.DataFrame:
    """Read, validate, and snapshot-filter one artifact.

    ``mtime_ns`` participates in the cache key so a pipeline rebuild is picked up on
    the next interaction. Keying on the path alone made the application keep serving
    artifacts from a previous build until the server was restarted, which defeats the
    point of rebuilding.

    The name deliberately has no leading underscore: Streamlit excludes
    underscore-prefixed parameters from the cache key, which would silently restore
    exactly the staleness this argument exists to prevent.
    """
    frame = _read_csv_checked(Path(csv_path), artifact_name, REQUIRED_COLUMNS[artifact_name])
    return frame if snapshot_id is None else _snapshot_filter(frame, snapshot_id)


def _load_artifact(
    path: Path, artifact_name: str, snapshot_id: str | None = None
) -> pd.DataFrame:
    """Cached artifact read, invalidated whenever the file on disk changes."""
    if not path.is_file():
        raise ValueError(f"{artifact_name} artifact not found: {path}")
    return _read_artifact_cached(str(path), artifact_name, path.stat().st_mtime_ns, snapshot_id)


def _resolve_config(config: AppConfig | None) -> AppConfig:
    return config if config is not None else load_app_config()


def load_metrics(config: AppConfig | None = None) -> pd.DataFrame:
    cfg = _resolve_config(config)
    return _load_artifact(cfg.metrics_csv, "metrics", cfg.snapshot_id)


def load_nodes(config: AppConfig | None = None) -> pd.DataFrame:
    cfg = _resolve_config(config)
    return _load_artifact(cfg.nodes_csv, "nodes", cfg.snapshot_id)


def load_edges(config: AppConfig | None = None) -> pd.DataFrame:
    cfg = _resolve_config(config)
    return _load_artifact(cfg.edges_csv, "edges", cfg.snapshot_id)


def load_communities(config: AppConfig | None = None) -> pd.DataFrame:
    cfg = _resolve_config(config)
    return _load_artifact(cfg.communities_csv, "communities", cfg.snapshot_id)


def load_route_metrics(config: AppConfig | None = None) -> pd.DataFrame:
    cfg = _resolve_config(config)
    return _load_artifact(cfg.route_metrics_csv, "route_metrics", cfg.snapshot_id)


def load_scenarios(config: AppConfig | None = None) -> pd.DataFrame:
    cfg = _resolve_config(config)
    return _load_artifact(cfg.scenarios_csv, "scenarios", cfg.snapshot_id)


def load_scenario_exposure(config: AppConfig | None = None) -> pd.DataFrame:
    cfg = _resolve_config(config)
    # scenario_exposure.csv is keyed by scenario_id and carries no snapshot column.
    return _load_artifact(cfg.scenario_exposure_csv, "scenario_exposure")


def _load_airports_cached(csv_path: str) -> pd.DataFrame:
    """Load ``airports.csv`` and normalize it to app-facing column names.

    ``airports.csv`` has no ``snapshot_id`` column: it is written per snapshot
    directory, so the path already identifies the snapshot.
    """
    df = _load_artifact(Path(csv_path), "airports")
    labels = df.rename(
        columns={
            "airport_id_canonical": "airport_id",
            "airport_code_raw": "iata_code",
        }
    )[["airport_id", "iata_code", "airport_name", "city", "state", "latitude", "longitude"]]
    labels["airport_id"] = labels["airport_id"].astype(int)
    labels["iata_code"] = labels["iata_code"].astype(str)
    # Precomputed once here so pages can label rows without repeating the concatenation.
    labels["airport_label"] = labels["iata_code"] + " · " + labels["airport_name"].astype(str)
    return labels


def load_airports(config: AppConfig | None = None) -> pd.DataFrame:
    """Airport reference for the snapshot: code, name, city, state, coordinates.

    Sourced from the processed ``airports.csv`` rather than the raw BTS master file.
    The raw tree is an ETL input, is gitignored, and is frequently absent on a machine
    that only has published artifacts, so the application must not depend on it.
    """
    cfg = _resolve_config(config)
    return _load_airports_cached(str(cfg.airports_csv))


def load_airports_geo(config: AppConfig | None = None) -> pd.DataFrame:
    """Metrics joined with airport identity and coordinates.

    One row per airport in the snapshot, carrying every metrics column plus
    ``iata_code``, ``airport_name``, ``city``, ``state``, ``latitude``, ``longitude``,
    and a display-ready ``airport_label``.
    """
    cfg = _resolve_config(config)
    metrics = load_metrics(cfg)
    return metrics.merge(load_airports(cfg), on="airport_id", how="left")


def label_airports(
    df: pd.DataFrame,
    config: AppConfig | None = None,
    *,
    id_column: str = "airport_id",
) -> pd.DataFrame:
    """Attach ``iata_code``, ``airport_name``, and ``airport_label`` to ``df``.

    Tables keyed by DOT airport id are unreadable without this: a reader recognizes
    ATL, not 10397. ``id_column`` allows labelling route endpoints as well as airports.
    """
    labels = load_airports(config)[["airport_id", "iata_code", "airport_name", "airport_label"]]
    if id_column != "airport_id":
        labels = labels.rename(columns={"airport_id": id_column})
    return df.merge(labels, on=id_column, how="left")
