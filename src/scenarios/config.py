"""Load scenario artifact paths for the active snapshot."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import yaml

# Repository root (src/scenarios/config.py -> parents[2])
REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = REPO_ROOT / "config" / "atna.yaml"
_SNAPSHOT_ID_RE = re.compile(r"^\d{4}-\d{2}$")


@dataclass(frozen=True)
class ScenarioConfig:
    """Resolved scenario artifact paths for one snapshot."""

    snapshot_id: str
    repo_root: Path
    config_path: Path
    processed_dir: Path
    scenarios_csv: Path
    scenario_exposure_csv: Path


def _validate_snapshot_id(snapshot_id: str) -> None:
    if not isinstance(snapshot_id, str) or not _SNAPSHOT_ID_RE.fullmatch(snapshot_id):
        raise ValueError(f"snapshot_id must match YYYY-MM (got {snapshot_id!r})")


def _require_output_key(output: Mapping[str, Any], key: str) -> str:
    value = output.get(key)
    if not isinstance(value, str) or not value.strip():
        raise KeyError(f"config.output.{key} must be a non-empty string")
    return value


def load_scenario_config(path: Path | str | None = None) -> ScenarioConfig:
    """Load ``config/atna.yaml`` and resolve scenario artifact paths.

    Relative paths are resolved against repository root to mirror metrics config
    behavior and keep all scenario outputs under ``data/processed/{snapshot_id}/``.
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

    output = data.get("output")
    if not isinstance(output, Mapping):
        raise KeyError("Config is missing required 'output' mapping")

    ctx = {"snapshot_id": snapshot_id}
    processed_rel = _require_output_key(output, "processed_dir").format(**ctx)
    scenarios_rel = _require_output_key(output, "scenarios_csv").format(**ctx)
    exposure_rel = _require_output_key(output, "scenario_exposure_csv").format(**ctx)

    root = REPO_ROOT.resolve()
    processed_dir = (root / processed_rel).resolve()
    scenarios_csv = (root / scenarios_rel).resolve()
    scenario_exposure_csv = (root / exposure_rel).resolve()

    if scenarios_csv.parent != processed_dir:
        raise ValueError(
            "output.scenarios_csv must resolve inside output.processed_dir for active snapshot"
        )
    if scenario_exposure_csv.parent != processed_dir:
        raise ValueError(
            "output.scenario_exposure_csv must resolve inside output.processed_dir for active snapshot"
        )

    return ScenarioConfig(
        snapshot_id=snapshot_id,
        repo_root=root,
        config_path=config_path,
        processed_dir=processed_dir,
        scenarios_csv=scenarios_csv,
        scenario_exposure_csv=scenario_exposure_csv,
    )
