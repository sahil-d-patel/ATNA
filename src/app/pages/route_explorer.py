"""Route explorer page: per-route structural criticality and cross-community behavior."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from app.config import load_app_config
from app.data_loader import load_airports, load_route_metrics
from app.ui.components import show_empty_state, show_table, show_table_count
from app.ui.formatters import format_integer, format_percent, format_score
from app.ui.theme import ACCENT, SEVERITY, apply_page_chrome, page_header

_ALL_ROUTES = "All routes"
_CROSS_ONLY = "Cross-community only"
_WITHIN_ONLY = "Within-community only"

_TABLE_COLUMNS = ["route", "origin_label", "destination_label", "analysis_weight",
                  "relation", "route_criticality_score"]


def _label_routes(routes: pd.DataFrame, airports: pd.DataFrame) -> pd.DataFrame:
    """Attach readable endpoint labels to each directed route."""
    codes = airports.set_index("airport_id")["iata_code"]
    names = airports.set_index("airport_id")["airport_name"]

    labelled = routes.copy()
    origin_code = labelled["origin_id"].map(codes)
    destination_code = labelled["destination_id"].map(codes)
    labelled["route"] = origin_code + " → " + destination_code
    labelled["origin_label"] = labelled["origin_id"].map(names)
    labelled["destination_label"] = labelled["destination_id"].map(names)
    labelled["relation"] = _relation_labels(labelled["cross_community_flag"])
    return labelled


def _relation_labels(flag_column: pd.Series) -> pd.Series:
    """Render the 0/100 cross-community flag as words."""
    return flag_column.astype(int).map({100: "Cross-community", 0: "Within community"})


def _criticality_chart(routes: pd.DataFrame, limit: int) -> go.Figure:
    """Top routes by criticality, colored by whether they join two communities."""
    top = routes.nlargest(limit, "route_criticality_score").sort_values("route_criticality_score")
    colors = [
        SEVERITY["moderate"] if relation == "Cross-community" else ACCENT
        for relation in top["relation"]
    ]
    figure = go.Figure(
        go.Bar(
            x=top["route_criticality_score"], y=top["route"], orientation="h",
            marker={"color": colors, "line": {"width": 0}},
            customdata=top[["origin_label", "destination_label", "relation"]],
            hovertemplate=(
                "<b>%{y}</b><br>%{customdata[0]} to %{customdata[1]}"
                "<br>%{customdata[2]}<br>Criticality %{x:.1f}<extra></extra>"
            ),
        )
    )
    figure.update_layout(
        title="Most structurally critical routes",
        height=max(280, 21 * len(top) + 70),
        xaxis={"range": [0, 100], "title": None},
        yaxis={"title": None, "showgrid": False},
        margin={"l": 8, "r": 8, "t": 44, "b": 8},
    )
    return figure


def render_route_explorer_page() -> None:
    """Render APP-05 route exploration."""
    apply_page_chrome()
    config = load_app_config()
    try:
        route_df = load_route_metrics(config)
        airports_df = load_airports(config)
    except ValueError as exc:
        st.error(f"Unable to load route artifacts: {exc}")
        return

    if route_df.empty:
        show_empty_state("No route metrics available for this snapshot.")
        return

    page_header(
        "Route Explorer",
        "Routes ranked by structural importance rather than raw traffic.",
        meta=f"Snapshot {config.snapshot_id}",
    )
    st.markdown(
        "Criticality blends a route's weight percentile with a bonus for joining two "
        "communities: `0.70 * P(weight) + 0.30 * cross_community_flag`. A modest route "
        "that is one of the few links between regions outranks a busier route buried "
        "inside a single community."
    )

    routes = _label_routes(route_df, airports_df)

    threshold_column, relation_column, count_column = st.columns([2.6, 1.9, 1.5])
    with threshold_column:
        crit_min = float(routes["route_criticality_score"].min())
        crit_max = float(routes["route_criticality_score"].max())
        threshold = st.slider(
            "Minimum criticality", min_value=round(crit_min, 1), max_value=round(crit_max, 1),
            value=round(crit_min, 1), step=0.5,
        )
    with relation_column:
        relation_filter = st.selectbox(
            "Community relation", options=[_ALL_ROUTES, _CROSS_ONLY, _WITHIN_ONLY]
        )
    with count_column:
        chart_limit = st.slider("Routes charted", min_value=5, max_value=40, value=15, step=5)

    filtered = routes.loc[routes["route_criticality_score"] >= threshold]
    if relation_filter == _CROSS_ONLY:
        filtered = filtered.loc[filtered["relation"] == "Cross-community"]
    elif relation_filter == _WITHIN_ONLY:
        filtered = filtered.loc[filtered["relation"] == "Within community"]

    if filtered.empty:
        show_empty_state("No routes match the current filters.")
        return

    cross_share = (filtered["relation"] == "Cross-community").mean()
    metrics = st.columns(3)
    metrics[0].metric("Routes in view", format_integer(len(filtered.index)))
    metrics[1].metric("Mean criticality", format_score(filtered["route_criticality_score"].mean(), digits=1))
    metrics[2].metric(
        "Cross-community share", format_percent(cross_share, digits=1),
        help="Share of routes in view that join two different Leiden communities.",
    )

    st.plotly_chart(
        _criticality_chart(filtered, chart_limit),
        width="stretch", config={"displayModeBar": False},
    )

    st.subheader("Route ranking")
    ranked = filtered.sort_values("route_criticality_score", ascending=False)
    if show_table(ranked, columns=_TABLE_COLUMNS):
        show_table_count(ranked, singular_label="route")
