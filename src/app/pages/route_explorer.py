"""Route explorer page (APP-05): route criticality and cross-community analysis."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from app.data_loader import load_route_metrics
from app.ui.components import show_dataframe_safe, show_empty_state, show_metric_card, show_table_count
from app.ui.formatters import format_integer, format_percent, format_score

def _apply_cross_filter(df: pd.DataFrame, cross_filter: str) -> pd.DataFrame:
    if cross_filter == "Cross-community only":
        return df.loc[df["cross_community_flag"].astype(int) == 100].copy()
    if cross_filter == "Within-community only":
        return df.loc[df["cross_community_flag"].astype(int) == 0].copy()
    return df.copy()


def render_route_explorer_page() -> None:
    """Render APP-05 route exploration."""
    st.title("APP-05 Route Explorer")
    st.caption("Inspect per-route structural criticality and cross-community behavior.")

    try:
        route_df = load_route_metrics()
    except ValueError as exc:
        st.error(f"Unable to load route metrics artifact: {exc}")
        return

    if route_df.empty:
        show_empty_state("No route metrics available for this snapshot.")
        return

    st.markdown(
        """
        **Metric semantics**
        - `cross_community_flag`: `100` when origin and destination are in different Leiden communities, else `0`.
        - `route_criticality_score`: `0.70 * P(analysis_weight) + 0.30 * cross_community_flag`.
        - `analysis_weight`: edge weight from `edges.csv` (`log1p(flight_count)`).
        """
    )

    crit_min = float(route_df["route_criticality_score"].min())
    crit_max = float(route_df["route_criticality_score"].max())
    weight_min = float(route_df["analysis_weight"].min())
    weight_max = float(route_df["analysis_weight"].max())

    c1, c2, c3 = st.columns(3)
    with c1:
        criticality_threshold = st.slider(
            "Minimum route criticality score",
            min_value=crit_min,
            max_value=crit_max,
            value=crit_min,
            step=max((crit_max - crit_min) / 100.0, 0.01),
            help="Routes below this threshold are filtered out.",
        )
    with c2:
        min_analysis_weight = st.slider(
            "Minimum analysis_weight",
            min_value=weight_min,
            max_value=weight_max,
            value=weight_min,
            step=max((weight_max - weight_min) / 100.0, 0.01),
        )
    with c3:
        cross_filter = st.selectbox(
            "Community relation",
            options=["All routes", "Cross-community only", "Within-community only"],
        )

    sort_col = st.selectbox(
        "Sort by",
        options=["route_criticality_score", "analysis_weight", "origin_id", "destination_id"],
        index=0,
    )
    sort_desc = st.toggle("Descending sort", value=True)
    top_n_chart = st.slider("Top routes in bar chart", min_value=5, max_value=50, value=15, step=1)

    filtered = route_df.loc[
        (route_df["route_criticality_score"] >= float(criticality_threshold))
        & (route_df["analysis_weight"] >= float(min_analysis_weight))
    ].copy()
    filtered = _apply_cross_filter(filtered, cross_filter)
    filtered = filtered.sort_values(sort_col, ascending=not sort_desc).reset_index(drop=True)

    if filtered.empty:
        show_empty_state("No routes for current filters.")
        return

    cross_share = (filtered["cross_community_flag"].astype(int) == 100).mean()
    m1, m2, m3 = st.columns(3)
    with m1:
        show_metric_card("Routes in view", format_integer(len(filtered.index)))
    with m2:
        show_metric_card("Avg. criticality", format_score(filtered["route_criticality_score"].mean()))
    with m3:
        show_metric_card("Cross-community share", format_percent(cross_share, digits=2))

    st.subheader("Route ranking table")
    display_df = filtered.loc[
        :,
        [
            "origin_id",
            "destination_id",
            "analysis_weight",
            "cross_community_flag",
            "route_criticality_score",
        ],
    ].copy()
    display_df["analysis_weight"] = display_df["analysis_weight"].map(format_score)
    display_df["cross_community_flag"] = display_df["cross_community_flag"].map(
        lambda v: "Cross-community" if int(v) == 100 else "Within-community"
    )
    display_df["route_criticality_score"] = display_df["route_criticality_score"].map(format_score)
    if show_dataframe_safe(display_df):
        show_table_count(display_df, singular_label="route")

    st.subheader("Top critical routes")
    chart_df = (
        filtered.sort_values("route_criticality_score", ascending=False)
        .head(top_n_chart)
        .copy()
    )
    chart_df["route_label"] = (
        chart_df["origin_id"].astype(int).astype(str) + " -> " + chart_df["destination_id"].astype(int).astype(str)
    )
    st.bar_chart(chart_df.set_index("route_label")["route_criticality_score"])
