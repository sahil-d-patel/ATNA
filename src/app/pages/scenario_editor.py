"""Scenario editor page (APP-06): canonical engine-backed scenario execution."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from app.scenario_service import list_airport_ids, list_route_pairs, run_ui_scenario
from app.ui.components import show_dataframe_safe, show_empty_state, show_metric_card, show_table_count
from app.ui.formatters import format_integer, format_percent, format_score


def _scenario_table(row: dict[str, object]) -> pd.DataFrame:
    return pd.DataFrame([row]).loc[
        :,
        [
            "scenario_id",
            "scenario_type",
            "impact_score",
            "network_health",
            "lcc_loss",
            "reachability_loss",
            "ripple_severity",
            "created_at",
        ],
    ]


def _render_before_after_cards(scenario_row: dict[str, object]) -> None:
    before_network_health = 100.0
    after_network_health = float(scenario_row["network_health"])
    before_impact = 0.0
    after_impact = float(scenario_row["impact_score"])

    st.subheader("Before vs after")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        show_metric_card("Before: network health", format_score(before_network_health))
    with c2:
        show_metric_card("After: network health", format_score(after_network_health))
    with c3:
        show_metric_card("Before: impact score", format_score(before_impact))
    with c4:
        show_metric_card("After: impact score", format_score(after_impact))

    d1, d2, d3 = st.columns(3)
    with d1:
        show_metric_card("LCC loss", format_percent(float(scenario_row["lcc_loss"]) / 100.0, digits=2))
    with d2:
        show_metric_card(
            "Reachability loss",
            format_percent(float(scenario_row["reachability_loss"]) / 100.0, digits=2),
        )
    with d3:
        show_metric_card(
            "Ripple severity",
            format_percent(float(scenario_row["ripple_severity"]) / 100.0, digits=2),
        )


def _render_exposure_outputs(exposure_df: pd.DataFrame) -> None:
    st.subheader("Affected airports")
    if exposure_df.empty:
        show_empty_state("No affected airports for this scenario.")
        return

    display = exposure_df.loc[
        :, ["airport_id", "hop_level", "exposure_score", "exposure_rank"]
    ].copy()
    display["airport_id"] = display["airport_id"].map(format_integer)
    display["exposure_score"] = display["exposure_score"].map(format_score)
    if show_dataframe_safe(display, message="No affected airports for this scenario."):
        show_table_count(display, singular_label="airport")

    hop_counts = (
        exposure_df.groupby("hop_level", dropna=False)["airport_id"].count().reset_index(name="airports")
    )
    hop_counts["hop_level"] = hop_counts["hop_level"].astype(int).astype(str)
    st.bar_chart(hop_counts.set_index("hop_level")["airports"])


def render_scenario_editor_page() -> None:
    """Render APP-06 scenario editor."""
    st.title("APP-06 Scenario Editor")
    st.caption("Run canonical scenario engine simulations and inspect before/after network outcomes.")

    airport_ids = list_airport_ids()
    route_pairs = list_route_pairs()

    route_labels = {f"{origin} -> {destination}": (origin, destination) for origin, destination in route_pairs}
    if "scenario_editor_result" not in st.session_state:
        st.session_state["scenario_editor_result"] = None

    with st.form("scenario-editor-form"):
        scenario_mode = st.radio(
            "Scenario type",
            options=("Airport removal", "Route removal"),
            horizontal=True,
        )
        if scenario_mode == "Airport removal":
            selected_airport = st.selectbox("Airport to remove", options=airport_ids, index=0)
            payload = {"airport_id": int(selected_airport)}
            scenario_type = "airport_removal"
        else:
            selected_route_label = st.selectbox("Route to remove", options=list(route_labels.keys()), index=0)
            origin_id, destination_id = route_labels[selected_route_label]
            payload = {"origin_id": int(origin_id), "destination_id": int(destination_id)}
            scenario_type = "route_removal"

        submitted = st.form_submit_button("Run scenario")

    if submitted:
        try:
            scenario_row, exposure_df = run_ui_scenario(scenario_type=scenario_type, payload=payload)
        except Exception as exc:  # pragma: no cover - streamlit rendering branch
            st.error(f"Scenario run failed: {exc}")
            return
        st.session_state["scenario_editor_result"] = {
            "scenario_row": scenario_row,
            "exposure_df": exposure_df,
        }

    result = st.session_state.get("scenario_editor_result")
    if not result:
        st.info("Submit a scenario to view score cards and affected-airport outputs.")
        return

    scenario_row = result["scenario_row"]
    exposure_df = result["exposure_df"]

    _render_before_after_cards(scenario_row)
    st.subheader("Scenario result row")
    result_table = _scenario_table(scenario_row).copy()
    for col in ("impact_score", "network_health", "lcc_loss", "reachability_loss", "ripple_severity"):
        result_table[col] = result_table[col].map(format_score)
    show_dataframe_safe(result_table)
    _render_exposure_outputs(exposure_df)
