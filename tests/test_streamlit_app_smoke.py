"""Streamlit smoke coverage for all app pages and empty-state resilience."""

from __future__ import annotations

from textwrap import dedent

import pytest
from streamlit.testing.v1 import AppTest

from app.config import load_app_config

# Artifact-backed pages can exceed AppTest's default ~3s script completion window on cold runs.
_RUN_TIMEOUT_S = 60.0


def _processed_artifacts_available() -> bool:
    """True only when the configured snapshot's processed artifact CSVs exist on disk."""
    try:
        cfg = load_app_config()
    except Exception:
        return False
    required = (
        cfg.metrics_csv,
        cfg.nodes_csv,
        cfg.edges_csv,
        cfg.route_metrics_csv,
        cfg.communities_csv,
    )
    return all(path.is_file() for path in required)


# The app pages render real processed artifacts; without them every page short-circuits
# to an error state, so the smoke assertions are only meaningful when the CSVs exist.
pytestmark = pytest.mark.skipif(
    not _processed_artifacts_available(),
    reason="processed artifact CSVs missing for configured snapshot",
)


def _run_page(function_import: str, function_name: str) -> AppTest:
    script = dedent(
        f"""
        from {function_import} import {function_name}
        {function_name}()
        """
    )
    app = AppTest.from_string(script)
    app.run(timeout=_RUN_TIMEOUT_S)
    return app


def _assert_no_exception(app: AppTest) -> None:
    assert len(app.exception) == 0


def test_smoke_all_seven_pages_render_without_exceptions() -> None:
    pages = [
        ("app.pages.overview", "render_overview_page"),
        ("app.pages.network_map", "render_network_map_page"),
        ("app.pages.airport_explorer", "render_airport_explorer_page"),
        ("app.pages.communities", "render_communities_page"),
        ("app.pages.route_explorer", "render_route_explorer_page"),
        ("app.pages.scenario_editor", "render_scenario_editor_page"),
        ("app.pages.methodology", "render_methodology_page"),
    ]
    for module_name, function_name in pages:
        app = _run_page(module_name, function_name)
        _assert_no_exception(app)


def test_empty_state_resilience_for_filterable_pages() -> None:
    network = _run_page("app.pages.network_map", "render_network_map_page")
    _assert_no_exception(network)
    if network.multiselect:
        network.multiselect[0].set_value([])
        network.run(timeout=_RUN_TIMEOUT_S)
        _assert_no_exception(network)
        assert any("No rows for current filters." in node.value for node in network.info)

    airport = _run_page("app.pages.airport_explorer", "render_airport_explorer_page")
    _assert_no_exception(airport)
    if len(airport.multiselect) > 0:
        airport.multiselect[0].set_value([])
        airport.run(timeout=_RUN_TIMEOUT_S)
        _assert_no_exception(airport)
        assert any("No rows for current filters." in node.value for node in airport.info)


def _find_button(app: AppTest, label: str):
    """Return the first button whose visible label matches, or ``None``."""
    for button in app.button:
        if button.label == label:
            return button
    return None


def test_scenario_editor_form_submit_airport_and_route_runs() -> None:
    # Airport removal via the quick-find selectbox + "Simulate removal" button.
    app = _run_page("app.pages.scenario_editor", "render_scenario_editor_page")
    _assert_no_exception(app)

    quick_find = app.selectbox[0]  # first selectbox on the page is the quick-find picker
    if len(quick_find.options) > 1:
        quick_find.set_value(quick_find.options[1])  # first real airport (index 0 is the placeholder)
        app.run(timeout=_RUN_TIMEOUT_S)
        simulate = _find_button(app, "Simulate removal")
        if simulate is not None:
            simulate.click()
            app.run(timeout=_RUN_TIMEOUT_S)
            _assert_no_exception(app)
            # A completed airport-removal run renders the metric-card + exposure sections.
            assert any("Before vs after" in node.value for node in app.subheader)
            assert any("Affected airports" in node.value for node in app.subheader)

    # Route removal via the route form's submit button.
    app = _run_page("app.pages.scenario_editor", "render_scenario_editor_page")
    _assert_no_exception(app)
    run_route = _find_button(app, "Run route removal scenario")
    assert run_route is not None, "route removal form submit button should render"
    run_route.click()
    app.run(timeout=_RUN_TIMEOUT_S)
    _assert_no_exception(app)
    assert any("Before vs after" in node.value for node in app.subheader)
    assert any("Affected airports" in node.value for node in app.subheader)
