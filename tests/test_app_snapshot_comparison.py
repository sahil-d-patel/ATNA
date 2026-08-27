"""Snapshot comparison page helpers.

The page answers whether the scores describe the network or one month's sampling, so
its discovery and verdict logic needs to be right: offering a snapshot that has no
artifacts, or calling an unstable metric stable, both mislead the reader.
"""

from __future__ import annotations

import pandas as pd
import pytest

from app.pages.snapshot_comparison import (
    MOSTLY_STABLE_THRESHOLD,
    STABLE_THRESHOLD,
    _available_snapshots,
    _movement_chart,
    _stability_verdict,
)


def test_only_complete_snapshots_are_offered(tmp_path) -> None:
    """A directory without both artifacts cannot be compared, so it must not appear."""
    complete = tmp_path / "2022-11"
    complete.mkdir()
    (complete / "metrics.csv").write_text("x\n")
    (complete / "airports.csv").write_text("x\n")

    metrics_only = tmp_path / "2022-12"
    metrics_only.mkdir()
    (metrics_only / "metrics.csv").write_text("x\n")

    (tmp_path / "empty").mkdir()

    assert _available_snapshots(str(tmp_path)) == ["2022-11"]


def test_missing_root_is_not_an_error(tmp_path) -> None:
    assert _available_snapshots(str(tmp_path / "absent")) == []


@pytest.mark.parametrize(
    ("rho", "expected"),
    [
        (0.999, "stable"),
        (STABLE_THRESHOLD, "stable"),
        (MOSTLY_STABLE_THRESHOLD, "mostly stable"),
        (0.80, "mostly stable"),
        (0.5, "unstable"),
        (-0.9, "unstable"),
    ],
)
def test_stability_verdicts(rho: float, expected: str) -> None:
    assert _stability_verdict(rho) == expected


def test_movement_chart_treats_snapshot_ids_as_categories() -> None:
    """Snapshot ids look like dates; Plotly would otherwise render a timeline."""
    movers = pd.DataFrame(
        {
            "code": ["EGE", "PAH"],
            "hub_score_base": [34.0, 35.1],
            "hub_score_comp": [66.9, 4.7],
            "movement": [32.9, -30.4],
        }
    )
    figure = _movement_chart(movers, "2022-11", "2022-12")
    assert figure.layout.xaxis.type == "category"
    assert list(figure.layout.xaxis.categoryarray) == ["2022-11", "2022-12"]
    assert len(figure.data) == 2, "one line per airport"
