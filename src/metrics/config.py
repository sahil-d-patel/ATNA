"""Load pipeline YAML: snapshot, paths, and metrics artifact locations."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import yaml

# Repository root (src/metrics/config.py -> parents[2])
REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = REPO_ROOT / "config" / "atna.yaml"

_SNAPSHOT_ID_RE = re.compile(r"^\d{4}-\d{2}$")


@dataclass(frozen=True)
class MetricsConfig:
    """Resolved pipeline and metrics artifact paths for one MVP snapshot."""

    snapshot_id: str
    repo_root: Path
    config_path: Path
    raw_on_time: Path
    raw_t100: Path
    raw_master_airport: Path
    processed_dir: Path
    edges_csv: Path
    metrics_csv: Path
    communities_csv: Path
    route_metrics_csv: Path


def _validate_snapshot_id(snapshot_id: str) -> None:
    if not isinstance(snapshot_id, str) or not _SNAPSHOT_ID_RE.fullmatch(snapshot_id):
        raise ValueError(
            f"snapshot_id must match YYYY-MM (got {snapshot_id!r})"
        )


def _snapshot_year_month(snapshot_id: str) -> tuple[str, str]:
    _validate_snapshot_id(snapshot_id)
    y, m = snapshot_id.split("-", 1)
    return y, m


def _format_templates(
    data: Mapping[str, Any], snapshot_id: str
) -> tuple[str, str, str, str, str, str, str]:
    raw = data["raw"]
    out = data["output"]
    year, month = _snapshot_year_month(snapshot_id)
    ctx = {"year": year, "month": month, "snapshot_id": snapshot_id}
    on_time = str(raw["on_time_glob"]).format(**ctx)
    t100 = str(raw["t100_glob"]).format(**ctx)
    master = str(raw["master_airport_file"])
    processed = str(out["processed_dir"]).format(**ctx)
    metrics = str(out["metrics_csv"]).format(**ctx)
    communities = str(out["communities_csv"]).format(**ctx)
    route_metrics = str(out["route_metrics_csv"]).format(**ctx)
    return on_time, t100, master, processed, metrics, communities, route_metrics


def load_config(path: Path | str | None = None) -> MetricsConfig:
    """Load ``config/atna.yaml``, validate ``snapshot_id``, resolve paths from repo root.

    Relative paths in YAML are resolved against ``REPO_ROOT``, matching ``etl.config``.

    Args:
        path: YAML file path; default ``<repo>/config/atna.yaml``.
    """
    config_path = Path(path) if path is not None else DEFAULT_CONFIG_PATH
    config_path = config_path.resolve()
    if not config_path.is_file():
        raise FileNotFoundError(f"Config not found: {config_path}")

    with open(config_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not isinstance(data, Mapping):
        raise ValueError("Config root must be a mapping")

    snapshot_id = data.get("snapshot_id")
    if not isinstance(snapshot_id, str):
        raise TypeError(
            f"snapshot_id must be a non-empty string, got {type(snapshot_id).__name__}"
        )
    _validate_snapshot_id(snapshot_id)

    (
        on_time_rel,
        t100_rel,
        master_rel,
        processed_rel,
        metrics_rel,
        communities_rel,
        route_metrics_rel,
    ) = _format_templates(data, snapshot_id)
    root = REPO_ROOT.resolve()
    processed_dir = (root / processed_rel).resolve()

    return MetricsConfig(
        snapshot_id=snapshot_id,
        repo_root=root,
        config_path=config_path,
        raw_on_time=(root / on_time_rel).resolve(),
        raw_t100=(root / t100_rel).resolve(),
        raw_master_airport=(root / master_rel).resolve(),
        processed_dir=processed_dir,
        edges_csv=(processed_dir / "edges.csv").resolve(),
        metrics_csv=(root / metrics_rel).resolve(),
        communities_csv=(root / communities_rel).resolve(),
        route_metrics_csv=(root / route_metrics_rel).resolve(),
    )
