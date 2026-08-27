"""Scenario editor page (APP-06): interactive geographic map with history and revert support."""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from app.config import AppConfig, load_app_config
from app.data_loader import load_airports_geo, load_edges
from app.scenario_service import list_route_pairs, run_ui_scenario
from app.ui.components import show_empty_state, show_table, show_table_count
from app.ui.formatters import format_integer, format_score
from app.ui.scenario_map import build_scenario_map
from app.ui.theme import apply_page_chrome, page_header

_GEO_MAP_KEY = "scenario_geo_map"
_SEARCH_PLACEHOLDER = "— search by name or code —"
_SCORE_COLUMNS = (
    "impact_score",
    "network_health",
    "lcc_loss",
    "reachability_loss",
    "ripple_severity",
)
_SS_AIRPORT = "se_airport_id"
_SS_RESULT = "se_result"
_SS_TYPE = "se_scenario_type"
_SS_HISTORY = "se_history"

# Cap on retained scenario runs. Each entry carries a full exposure DataFrame.
_MAX_HISTORY = 25

# Each history entry:
# {
#   "airport_id": int | None,
#   "label": str,            e.g. "ABE — Lehigh Valley International"
#   "scenario_type": str,    "airport" | "route"
#   "scenario_row": dict,
#   "exposure_df": pd.DataFrame,
# }


# ---------------------------------------------------------------------------
# Session state helpers
# ---------------------------------------------------------------------------

def _init_state() -> None:
    defaults: dict[str, Any] = {
        _SS_AIRPORT: None,
        _SS_RESULT: None,
        _SS_TYPE: None,
        _SS_HISTORY: [],
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


def _push_history(entry: dict[str, Any]) -> None:
    """Append a run to the history, discarding the oldest past ``_MAX_HISTORY``.

    Each entry holds a full exposure DataFrame, so an unbounded list grows session
    state without limit over a long demo. Undo walks back one entry at a time, so a
    bounded window keeps every realistic revert available.
    """
    history: list[dict[str, Any]] = st.session_state[_SS_HISTORY]
    history.append(entry)
    if len(history) > _MAX_HISTORY:
        del history[: len(history) - _MAX_HISTORY]


def _apply_state(entry: dict[str, Any] | None) -> None:
    """Restore session state from a history entry, or clear to baseline if None."""
    if entry is None:
        st.session_state[_SS_AIRPORT] = None
        st.session_state[_SS_RESULT] = None
        st.session_state[_SS_TYPE] = None
    else:
        st.session_state[_SS_AIRPORT] = entry["airport_id"]
        st.session_state[_SS_TYPE] = entry["scenario_type"]
        st.session_state[_SS_RESULT] = {
            "scenario_row": entry["scenario_row"],
            "exposure_df": entry["exposure_df"],
        }


# ---------------------------------------------------------------------------
# Result rendering
# ---------------------------------------------------------------------------

def _severity_info(impact_score: float) -> tuple[str, str]:
    """Return (label, streamlit method name) for the given impact score."""
    if impact_score < 20:
        return "Low impact", "success"
    elif impact_score < 50:
        return "Moderate impact", "warning"
    return "High impact", "error"


def _render_metric_cards(scenario_row: dict[str, object]) -> None:
    after_health = float(scenario_row["network_health"])
    after_impact = float(scenario_row["impact_score"])
    delta_health = after_health - 100.0
    delta_impact = after_impact

    severity_label, severity_fn = _severity_info(after_impact)
    getattr(st, severity_fn)(f"**{severity_label}** — impact score {after_impact:.1f}")

    st.subheader("Before vs after")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Network health (before)", "100.0")
    with c2:
        st.metric(
            "Network health (after)",
            f"{after_health:.1f}",
            delta=f"{delta_health:.1f} pts",
            delta_color="normal",
            help="Negative delta = network degraded. Red means worse.",
        )
    with c3:
        st.metric("Impact score (before)", "0.0")
    with c4:
        st.metric(
            "Impact score (after)",
            f"{after_impact:.1f}",
            delta=f"+{delta_impact:.1f} pts",
            delta_color="inverse",
            help="Positive delta = more disruption. Red means worse.",
        )

    d1, d2, d3 = st.columns(3)
    with d1:
        lcc = float(scenario_row["lcc_loss"])
        st.metric("LCC loss", f"{lcc:.1f}%", delta=f"+{lcc:.1f}%", delta_color="inverse",
                  help="Largest connected component lost as % of original.")
    with d2:
        reach = float(scenario_row["reachability_loss"])
        st.metric("Reachability loss", f"{reach:.1f}%", delta=f"+{reach:.1f}%", delta_color="inverse",
                  help="% of airport pairs that can no longer reach each other.")
    with d3:
        ripple = float(scenario_row["ripple_severity"])
        st.metric("Ripple severity", f"{ripple:.1f}%", delta=f"+{ripple:.1f}%", delta_color="inverse",
                  help="Weighted exposure across 2-hop ripple propagation.")


def _scenario_table(row: dict[str, object]) -> pd.DataFrame:
    return pd.DataFrame([row]).loc[
        :,
        [
            "scenario_id", "scenario_type", "impact_score", "network_health",
            "lcc_loss", "reachability_loss", "ripple_severity", "created_at",
        ],
    ]


def _render_exposure_outputs(exposure_df: pd.DataFrame) -> None:
    st.subheader("Affected airports")
    if exposure_df.empty:
        show_empty_state("No affected airports for this scenario.")
        return

    display = exposure_df.loc[:, ["airport_id", "hop_level", "exposure_score", "exposure_rank"]].copy()
    display["airport_id"] = display["airport_id"].map(format_integer)
    display["exposure_score"] = display["exposure_score"].map(format_score)
    if show_table(display, message="No affected airports for this scenario."):
        show_table_count(display, singular_label="airport")

    hop_counts = (
        exposure_df.groupby("hop_level", dropna=False)["airport_id"]
        .count().reset_index(name="airports")
    )
    hop_counts["hop_level"] = hop_counts["hop_level"].astype(int).astype(str)
    st.bar_chart(hop_counts.set_index("hop_level")["airports"])


# ---------------------------------------------------------------------------
# Internal: run and push an airport removal scenario
# ---------------------------------------------------------------------------

def _run_airport_scenario(
    airports_geo: pd.DataFrame,
    airport_id: int,
    config: Any,
) -> None:
    """Execute an airport removal, push to history, and update session state."""
    try:
        scenario_row, exp_df = run_ui_scenario(
            scenario_type="airport_removal",
            payload={"airport_id": airport_id},
            config=config,
        )
    except Exception as exc:  # pragma: no cover
        st.error(f"Scenario run failed: {exc}")
        return

    airport_row = airports_geo.loc[airports_geo["airport_id"] == airport_id]
    label = (
        f"{airport_row.iloc[0]['iata_code']} — {airport_row.iloc[0]['airport_name']}"
        if not airport_row.empty
        else f"Airport ID {airport_id}"
    )
    entry: dict[str, Any] = {
        "airport_id": airport_id,
        "label": label,
        "scenario_type": "airport",
        "scenario_row": scenario_row,
        "exposure_df": exp_df,
    }
    _push_history(entry)
    st.session_state[_SS_AIRPORT] = airport_id
    st.session_state[_SS_TYPE] = "airport"
    st.session_state[_SS_RESULT] = {"scenario_row": scenario_row, "exposure_df": exp_df}


# ---------------------------------------------------------------------------
# Page entry point
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Page sections
#
# Each section owns one region of the page and the state transitions that region
# can trigger. Splitting them apart keeps the orchestrating render function short
# enough to read in one pass, and makes it obvious which interactions rerun.
# ---------------------------------------------------------------------------

def _render_controls(
    airports_geo: pd.DataFrame, edges_df: pd.DataFrame, config: AppConfig
) -> float:
    """Quick-find search and the route-weight filter. Returns the weight threshold."""
    search_column, slider_column = st.columns([2, 3])

    with search_column:
        located = airports_geo.dropna(subset=["latitude", "longitude"])
        options = sorted(
            (located["iata_code"].astype(str) + " — " + located["airport_name"].astype(str)).tolist()
        )
        selected = st.selectbox(
            "Quick-find airport",
            options=[_SEARCH_PLACEHOLDER, *options],
            index=0,
            help="Type to filter. Select an airport then click Simulate.",
        )
        if selected != _SEARCH_PLACEHOLDER:
            iata_code = selected.split(" — ")[0]
            match = airports_geo.loc[airports_geo["iata_code"] == iata_code]
            if not match.empty and st.button("Simulate removal", key="quick_find_btn"):
                _run_airport_scenario(airports_geo, int(match.iloc[0]["airport_id"]), config)
                st.rerun()

    with slider_column:
        max_weight = float(edges_df["analysis_weight"].max())
        return st.slider(
            "Show routes with analysis weight ≥",
            min_value=0.0, max_value=max_weight, value=5.0, step=0.1,
            help="Higher = only busiest routes shown. Does not affect the simulation.",
        )


def _render_map(
    airports_geo: pd.DataFrame,
    edges_df: pd.DataFrame,
    weight_threshold: float,
    selected_airport_id: int | None,
    exposure_df: pd.DataFrame | None,
    config: AppConfig,
) -> None:
    """Draw the map and turn a click on an airport into a scenario run."""
    figure = build_scenario_map(
        airports_geo, edges_df, weight_threshold, selected_airport_id, exposure_df
    )
    event = st.plotly_chart(
        figure, on_select="rerun", selection_mode=["points"],
        key=_GEO_MAP_KEY, use_container_width=True,
    )

    selection = getattr(event, "selection", None)
    points = list(getattr(selection, "points", None) or [])
    if points:
        customdata = points[0].get("customdata") or []
        if customdata:
            clicked_id = int(customdata[0])
            # Re-running the airport already simulated would only reset the view.
            if clicked_id != selected_airport_id:
                _run_airport_scenario(airports_geo, clicked_id, config)
                st.rerun()

    st.caption(
        "**Map guide:** dot size follows hub score and dot color follows vulnerability, "
        "pale to dark as vulnerability rises. Airports affected by the simulated removal "
        "are shaded by exposure, teal through amber to red. The removed airport is marked ✕."
    )


def _render_status_bar(
    airports_geo: pd.DataFrame,
    selected_airport_id: int | None,
    result: dict[str, Any] | None,
    history: list[dict[str, Any]],
) -> None:
    """Current simulation summary, with undo and restore."""
    status_column, undo_column, restore_column = st.columns([5, 1, 1])

    with status_column:
        if selected_airport_id is not None and result:
            row = airports_geo.loc[airports_geo["airport_id"] == selected_airport_id]
            if not row.empty:
                airport = row.iloc[0]
                impact = float(result["scenario_row"]["impact_score"])
                severity_label, _ = _severity_info(impact)
                st.info(
                    f"**Simulating removal of:** {airport['iata_code']} — {airport['airport_name']}  \n"
                    f"Vulnerability {airport['vulnerability_score']:.1f} · "
                    f"Community {int(airport['leiden_community_id'])} · "
                    f"{severity_label} (impact {impact:.1f})"
                )
        elif result and st.session_state[_SS_TYPE] == "airport_set":
            st.info("**Correlated outage simulated.** See results below.")
        elif result and st.session_state[_SS_TYPE] == "route":
            st.info("**Route removal simulated.** See results below.")
        else:
            st.info("No active simulation. Click an airport on the map or use quick-find above.")

    with undo_column:
        st.write("")  # vertical alignment against the status box
        if st.button(
            "↩ Undo", key="undo_btn", disabled=not history,
            help="Revert to the previous scenario, or to baseline if only one step back.",
            use_container_width=True,
        ):
            history.pop()
            _apply_state(history[-1] if history else None)
            st.rerun()

    with restore_column:
        st.write("")
        if st.button(
            "Restore network", key="restore_btn", disabled=result is None,
            help="Clear all simulations and return the map to its baseline state.",
            use_container_width=True,
        ):
            st.session_state[_SS_HISTORY] = []
            _apply_state(None)
            st.rerun()


def _render_history(history: list[dict[str, Any]]) -> None:
    """Past runs, each restorable."""
    if not history:
        with st.expander("Scenario history (0 runs)"):
            st.caption("No scenarios run yet. Simulations appear here as you explore.")
        return

    plural = "s" if len(history) != 1 else ""
    with st.expander(f"Scenario history ({len(history)} run{plural})"):
        st.caption("Click **Load** on any row to restore that simulation.")
        for offset, entry in enumerate(reversed(history)):
            position = len(history) - 1 - offset
            impact = float(entry["scenario_row"]["impact_score"])
            health = float(entry["scenario_row"]["network_health"])
            severity_label, _ = _severity_info(impact)
            columns = st.columns([3, 2, 2, 2, 1])
            columns[0].write(f"**{entry['label']}**")
            columns[1].write(f"Impact: `{impact:.1f}`")
            columns[2].write(f"Health: `{health:.1f}`")
            columns[3].write(severity_label)
            if columns[4].button("Load", key=f"hist_load_{position}"):
                _apply_state(history[position])
                st.rerun()


def _render_results(result: dict[str, Any]) -> None:
    """Score cards, the raw scenario row, and the ripple exposure table."""
    _render_metric_cards(result["scenario_row"])

    with st.expander("Raw scenario data"):
        table = _scenario_table(result["scenario_row"]).copy()
        for column in _SCORE_COLUMNS:
            table[column] = table[column].map(format_score)
        show_table(table)

    _render_exposure_outputs(result["exposure_df"])


def _render_airport_set_form(
    airports_geo: pd.DataFrame, config: AppConfig
) -> None:
    """Remove several airports at once.

    A correlated outage - a carrier collapse, a regional storm - takes out a set of
    airports together, and the combined effect is not the sum of the individual ones:
    exposure accumulates wherever the removed airports share neighbours.
    """
    st.subheader("Correlated outage")
    st.caption(
        "Remove several airports simultaneously. Exposure accumulates where they share "
        "neighbours, so the result is not the sum of the individual removals."
    )

    located = airports_geo.dropna(subset=["latitude", "longitude"])
    by_label = dict(
        zip(located["airport_label"].astype(str), located["airport_id"].astype(int), strict=True)
    )

    with st.form("airport-set-form"):
        chosen = st.multiselect(
            "Airports to remove",
            options=sorted(by_label),
            help="Two or more airports, removed in a single scenario.",
        )
        submitted = st.form_submit_button("Run correlated outage")

    if not submitted:
        return
    if len(chosen) < 2:
        st.warning("Select at least two airports; one airport is the single-removal case above.")
        return

    airport_ids = [by_label[label] for label in chosen]
    try:
        scenario_row, exposure_df = run_ui_scenario(
            scenario_type="airport_set_removal",
            payload={"airport_ids": airport_ids},
            config=config,
        )
    except Exception as exc:  # pragma: no cover - engine failures are surfaced, not swallowed
        st.error(f"Scenario run failed: {exc}")
        return

    codes = ", ".join(label.split(" · ")[0] for label in chosen)
    _push_history(
        {
            "airport_id": None,
            "label": f"Outage: {codes}",
            "scenario_type": "airport_set",
            "scenario_row": scenario_row,
            "exposure_df": exposure_df,
        }
    )
    st.session_state[_SS_AIRPORT] = None
    st.session_state[_SS_TYPE] = "airport_set"
    st.session_state[_SS_RESULT] = {"scenario_row": scenario_row, "exposure_df": exposure_df}
    st.rerun()


def _render_route_form(
    airports_geo: pd.DataFrame, route_pairs: list[tuple[int, int]], config: AppConfig
) -> None:
    """Route removal by explicit selection, for routes with no obvious map target."""
    st.subheader("Route removal")
    st.caption("Remove a specific directed route and run the scenario engine.")

    # Codes, not DOT ids: a dropdown of numeric pairs is unusable for choosing a route.
    code_by_id = dict(
        zip(
            airports_geo["airport_id"].astype(int),
            airports_geo["iata_code"].astype(str),
            strict=True,
        )
    )
    route_labels = {
        f"{code_by_id.get(origin, origin)} → {code_by_id.get(destination, destination)}":
            (origin, destination)
        for origin, destination in route_pairs
    }

    with st.form("route-removal-form"):
        selected_label = st.selectbox("Route to remove", options=list(route_labels), index=0)
        submitted = st.form_submit_button("Run route removal scenario")

    if not submitted:
        return

    origin_id, destination_id = route_labels[selected_label]
    try:
        scenario_row, exposure_df = run_ui_scenario(
            scenario_type="route_removal",
            payload={"origin_id": int(origin_id), "destination_id": int(destination_id)},
            config=config,
        )
    except Exception as exc:  # pragma: no cover - engine failures are surfaced, not swallowed
        st.error(f"Scenario run failed: {exc}")
        return

    label = (
        f"Route: {code_by_id.get(origin_id, origin_id)} → "
        f"{code_by_id.get(destination_id, destination_id)}"
    )
    _push_history(
        {
            "airport_id": None,
            "label": label,
            "scenario_type": "route",
            "scenario_row": scenario_row,
            "exposure_df": exposure_df,
        }
    )
    st.session_state[_SS_AIRPORT] = None
    st.session_state[_SS_TYPE] = "route"
    st.session_state[_SS_RESULT] = {"scenario_row": scenario_row, "exposure_df": exposure_df}
    st.rerun()


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------

def render_scenario_editor_page() -> None:
    """Render APP-06 scenario editor with interactive map, history, and revert support."""
    apply_page_chrome()
    config = load_app_config()
    try:
        airports_geo = load_airports_geo(config)
        edges_df = load_edges(config)
        route_pairs = list_route_pairs(config)
    except ValueError as exc:
        st.error(f"Unable to load scenario artifacts: {exc}")
        return

    page_header(
        "Scenario Editor",
        "Simulate removing an airport or route. Click the map, or use quick-find below.",
        meta=f"Snapshot {config.snapshot_id}",
    )

    _init_state()
    selected_airport_id: int | None = st.session_state[_SS_AIRPORT]
    result: dict[str, Any] | None = st.session_state[_SS_RESULT]
    history: list[dict[str, Any]] = st.session_state[_SS_HISTORY]

    weight_threshold = _render_controls(airports_geo, edges_df, config)
    _render_map(
        airports_geo, edges_df, weight_threshold, selected_airport_id,
        result["exposure_df"] if result else None, config,
    )
    _render_status_bar(airports_geo, selected_airport_id, result, history)
    _render_history(history)

    st.divider()

    # ``result`` read above is still current: every mutation path (map click,
    # quick-find, undo, restore, history load, route form) calls st.rerun() before
    # control returns here, so there is no stale-read window.
    if result:
        _render_results(result)
        st.divider()

    _render_airport_set_form(airports_geo, config)

    _render_route_form(airports_geo, route_pairs, config)

    if not result:
        st.info(
            "Click an airport on the map, use quick-find, or submit a route removal "
            "to run a simulation."
        )
