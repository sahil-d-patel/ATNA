"""Scenario artifact writers with schema-ordered CSV outputs."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

import pandas as pd

SCENARIOS_COLUMNS = [
    "scenario_id",
    "snapshot_id",
    "scenario_type",
    "edited_airports",
    "edited_routes",
    "impact_score",
    "network_health",
    "lcc_loss",
    "reachability_loss",
    "ripple_severity",
    "created_at",
]

SCENARIO_EXPOSURE_COLUMNS = [
    "scenario_id",
    "airport_id",
    "hop_level",
    "exposure_score",
    "exposure_rank",
]


def write_scenarios_csv(rows: Sequence[Mapping[str, Any]], path: Path) -> pd.DataFrame:
    """Write ``scenarios.csv`` using locked column order."""
    frame = pd.DataFrame(list(rows))
    _validate_columns(frame, SCENARIOS_COLUMNS, table_name="scenarios.csv")
    frame = frame[SCENARIOS_COLUMNS].copy()
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)
    return frame


def write_scenario_exposure_csv(
    rows: Sequence[Mapping[str, Any]], path: Path
) -> pd.DataFrame:
    """Write ``scenario_exposure.csv`` using locked column order."""
    frame = pd.DataFrame(list(rows))
    _validate_columns(
        frame, SCENARIO_EXPOSURE_COLUMNS, table_name="scenario_exposure.csv"
    )
    frame = frame[SCENARIO_EXPOSURE_COLUMNS].copy()
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)
    return frame


def _validate_columns(frame: pd.DataFrame, expected: list[str], *, table_name: str) -> None:
    missing = [col for col in expected if col not in frame.columns]
    if missing:
        raise ValueError(f"{table_name} rows missing required columns: {missing}")
