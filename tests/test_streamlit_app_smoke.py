"""Streamlit smoke coverage for all app pages and empty-state resilience."""

from __future__ import annotations

from textwrap import dedent

from streamlit.testing.v1 import AppTest


def _run_page(function_import: str, function_name: str) -> AppTest:
    script = dedent(
        f"""
        from {function_import} import {function_name}
        {function_name}()
        """
    )
    app = AppTest.from_string(script)
    app.run()
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
        network.run()
        _assert_no_exception(network)
        assert any("No rows for current filters." in node.value for node in network.info)

    airport = _run_page("app.pages.airport_explorer", "render_airport_explorer_page")
    _assert_no_exception(airport)
    if len(airport.multiselect) > 0:
        airport.multiselect[0].set_value([])
        airport.run()
        _assert_no_exception(airport)
        assert any("No rows for current filters." in node.value for node in airport.info)


def test_scenario_editor_form_submit_airport_and_route_runs() -> None:
    app = _run_page("app.pages.scenario_editor", "render_scenario_editor_page")
    _assert_no_exception(app)

    if app.button:
        app.button[0].click()
        app.run()
        _assert_no_exception(app)
        assert any("Scenario result row" in node.value for node in app.subheader)

    app = _run_page("app.pages.scenario_editor", "render_scenario_editor_page")
    _assert_no_exception(app)
    if app.radio:
        app.radio[0].set_value("Route removal")
    if app.button:
        app.button[0].click()
    app.run()
    _assert_no_exception(app)
    assert any("Affected airports" in node.value for node in app.subheader)
