"""Overview page with snapshot KPIs and airport rankings."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from app.config import load_app_config
from app.data_loader import load_metrics, load_nodes, load_route_metrics
from app.ui.components import show_dataframe_safe, show_metric_card, show_table_count
from app.ui.formatters import format_integer, format_score


def _top_rankings(metrics_df: pd.DataFrame, column: str, limit: int) -> pd.DataFrame:
    ranked = (
        metrics_df.sort_values(by=column, ascending=False)
        .loc[:, ["airport_id", column, "leiden_community_id"]]
        .head(limit)
        .copy()
    )
    ranked[column] = ranked[column].map(lambda value: format_score(value, digits=3))
    return ranked

def render_overview_page() -> None:
    """Render APP-01 overview dashboard."""
    config = load_app_config()
    metrics_df = load_metrics(config)
    nodes_df = load_nodes(config)
    route_metrics_df = load_route_metrics(config)

    airport_count = int(metrics_df["airport_id"].nunique())
    route_count = int(route_metrics_df.shape[0])
    total_flights = int(nodes_df["flights_out"].sum())
    total_analysis_weight = float(route_metrics_df["analysis_weight"].sum())

    st.title("APP-01 Overview")
    st.caption(
        f"Snapshot `{config.snapshot_id}` with {format_integer(airport_count)} airports "
        f"and {format_integer(route_count)} directed routes."
    )

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        show_metric_card("Airports", format_integer(airport_count))
    with col2:
        show_metric_card("Routes", format_integer(route_count))
    with col3:
        show_metric_card("Flights (outbound sum)", format_integer(total_flights))
    with col4:
        show_metric_card("Total analysis weight", format_score(total_analysis_weight, digits=1))

    st.subheader("Top Hubs")
    hubs = _top_rankings(metrics_df, "hub_score", limit=10)
    if show_dataframe_safe(hubs):
        show_table_count(hubs, singular_label="airport")

    st.subheader("Top Bridge Airports")
    bridges = _top_rankings(metrics_df, "bridge_score", limit=10)
    if show_dataframe_safe(bridges):
        show_table_count(bridges, singular_label="airport")

    st.subheader("Top Vulnerability Scores")
    vulnerability = _top_rankings(metrics_df, "vulnerability_score", limit=10)
    if show_dataframe_safe(vulnerability):
        show_table_count(vulnerability, singular_label="airport")
