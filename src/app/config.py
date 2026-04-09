"""Canonical Streamlit app config and artifact path resolution."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import yaml

# Repository root (src/app/config.py -> parents[2])
REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = REPO_ROOT / "config" / "atna.yaml"

_SNAPSHOT_ID_RE = re.compile(r"^\d{4}-\d{2}$")


@dataclass(frozen=True)
class AppConfig:
    """Resolved app artifact paths for one snapshot."""

    snapshot_id: str
    repo_root: Path
    config_path: Path
    processed_dir: Path
    edges_csv: Path
    nodes_csv: Path
    metrics_csv: Path
    communities_csv: Path
    route_metrics_csv: Path
    scenarios_csv: Path
    scenario_exposure_csv: Path


def _validate_snapshot_id(snapshot_id: str) -> None:
    if not isinstance(snapshot_id, str) or not _SNAPSHOT_ID_RE.fullmatch(snapshot_id):
        raise ValueError(f"snapshot_id must match YYYY-MM (got {snapshot_id!r})")


def _require_mapping(data: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = data.get(key)
    if not isinstance(value, Mapping):
        raise ValueError(f"Missing or invalid mapping at config key '{key}'")
    return value


def _require_template(section: Mapping[str, Any], key: str, context: Mapping[str, str]) -> str:
    raw_value = section.get(key)
    if not isinstance(raw_value, str) or not raw_value.strip():
        raise ValueError(f"Missing or invalid config key 'output.{key}'")
    return raw_value.format(**context)


def load_app_config(path: Path | str | None = None) -> AppConfig:
    """Load app artifact config from ``config/atna.yaml``."""
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
        raise ValueError("Missing or invalid config key 'snapshot_id'")
    _validate_snapshot_id(snapshot_id)

    output = _require_mapping(data, "output")
    context = {"snapshot_id": snapshot_id}
    root = REPO_ROOT.resolve()

    processed_rel = _require_template(output, "processed_dir", context)
    metrics_rel = _require_template(output, "metrics_csv", context)
    communities_rel = _require_template(output, "communities_csv", context)
    route_metrics_rel = _require_template(output, "route_metrics_csv", context)
    scenarios_rel = _require_template(output, "scenarios_csv", context)
    scenario_exposure_rel = _require_template(output, "scenario_exposure_csv", context)

    processed_dir = (root / processed_rel).resolve()

    return AppConfig(
        snapshot_id=snapshot_id,
        repo_root=root,
        config_path=config_path,
        processed_dir=processed_dir,
        edges_csv=(processed_dir / "edges.csv").resolve(),
        nodes_csv=(processed_dir / "nodes.csv").resolve(),
        metrics_csv=(root / metrics_rel).resolve(),
        communities_csv=(root / communities_rel).resolve(),
        route_metrics_csv=(root / route_metrics_rel).resolve(),
        scenarios_csv=(root / scenarios_rel).resolve(),
        scenario_exposure_csv=(root / scenario_exposure_rel).resolve(),
    )
