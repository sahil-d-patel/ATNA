"""Payload validation for correlated-outage scenarios reaching the engine from the UI."""

from __future__ import annotations

import pytest

from app.scenario_service import _normalize_payload
from scenarios.models import ScenarioType

SET = ScenarioType.AIRPORT_SET_REMOVAL


def test_widget_values_are_coerced_to_ints() -> None:
    """Multiselect values arrive as whatever the lookup held; the engine wants ints."""
    assert _normalize_payload(SET, {"airport_ids": ["10397", 13930]}) == {
        "airport_ids": [10397, 13930]
    }


def test_missing_key_is_rejected() -> None:
    with pytest.raises(ValueError, match="requires airport_ids"):
        _normalize_payload(SET, {})


def test_empty_selection_is_rejected() -> None:
    with pytest.raises(ValueError, match="at least one airport"):
        _normalize_payload(SET, {"airport_ids": []})


def test_repeated_airport_is_rejected() -> None:
    with pytest.raises(ValueError, match="must not repeat"):
        _normalize_payload(SET, {"airport_ids": [10397, 10397]})


def test_a_bare_string_is_not_a_sequence_of_ids() -> None:
    """A string is iterable, so it would otherwise be read character by character."""
    with pytest.raises(TypeError, match="sequence of airport ids"):
        _normalize_payload(SET, {"airport_ids": "10397"})


def test_non_numeric_entry_names_the_field() -> None:
    with pytest.raises(ValueError, match="airport_id must be an integer"):
        _normalize_payload(SET, {"airport_ids": [10397, "ATL"]})
