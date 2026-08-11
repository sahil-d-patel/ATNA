"""Airport explorer page: sortable airport matrix with per-airport drilldown."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from app.config import load_app_config
from app.data_loader import load_airports_geo, load_nodes
from app.ui.components import show_table, show_table_count
from app.ui.formatters import format_integer, format_score
from app.ui.theme import ACCENT, HAIRLINE, apply_page_chrome, page_header

_TABLE_COLUMNS = [
    "iata_code", "airport_name", "city", "state", "leiden_community_id",
    "hub_score", "bridge_score", "vulnerability_score",
    "pagerank", "betweenness", "flights_out", "flights_in", "degree_total",
]

_SORT_CHOICES = {
    "Vulnerability": "vulnerability_score",
    "Hub score": "hub_score",
    "Bridge score": "bridge_score",
    "PageRank": "pagerank",
    "Departures": "flights_out",
    "Code": "iata_code",
}


def _profile_chart(row: pd.Series) -> go.Figure:
    """Three-bar profile for one airport on the shared 0-100 percentile scale.

    A common axis is the point: it shows at a glance whether an airport's structural
    role matches its traffic, which single metric cards cannot convey.
    """
    labels = ["Hub", "Bridge", "Vulnerability"]
    values = [row["hub_score"], row["bridge_score"], row["vulnerability_score"]]
    figure = go.Figure(
        go.Bar(
            x=values, y=labels, orientation="h",
            marker={"color": ACCENT, "line": {"width": 0}},
            text=[f"{value:.1f}" for value in values],
            textposition="outside",
            hoverinfo="skip",
        )
    )
    figure.update_layout(
        height=170,
        xaxis={"range": [0, 112], "showgrid": True, "gridcolor": HAIRLINE, "title": None},
        yaxis={"title": None, "showgrid": False},
        margin={"l": 8, "r": 8, "t": 8, "b": 8},
    )
    return figure


def render_airport_explorer_page() -> None:
    """Render APP-03 airport explorer."""
    apply_page_chrome()
    config = load_app_config()
    try:
        geo_df = load_airports_geo(config)
        nodes_df = load_nodes(config)
    except ValueError as exc:
        st.error(f"Unable to load airport artifacts: {exc}")
        return

    airport_df = geo_df.merge(
        nodes_df.drop(columns=["snapshot_id"], errors="ignore"), on="airport_id", how="left"
    )

    page_header(
        "Airport Explorer",
        "Every airport in the snapshot, ranked and filterable by structural role.",
        meta=f"Snapshot {config.snapshot_id}",
    )

    search_column, community_column, sort_column, order_column = st.columns([2.2, 2.2, 1.6, 1.1])
    with search_column:
        query = st.text_input(
            "Search", value="", placeholder="Code, name, or city",
            help="Matches IATA code, airport name, or city.",
        )
    with community_column:
        community_options = sorted(
            int(value) for value in airport_df["leiden_community_id"].dropna().unique()
        )
        selected_communities = st.multiselect(
            "Communities", options=community_options, default=community_options
        )
    with sort_column:
        sort_label = st.selectbox("Sort by", options=list(_SORT_CHOICES), index=0)
    with order_column:
        descending = st.toggle("Desc", value=True)

    filtered = airport_df
    if query:
        needle = query.strip().casefold()
        haystack = (
            filtered["iata_code"].astype(str).str.casefold()
            + " " + filtered["airport_name"].astype(str).str.casefold()
            + " " + filtered["city"].astype(str).str.casefold()
        )
        filtered = filtered.loc[haystack.str.contains(needle, regex=False)]
    filtered = filtered.loc[filtered["leiden_community_id"].isin(selected_communities)]

    filtered = filtered.sort_values(
        by=_SORT_CHOICES[sort_label], ascending=not descending, kind="mergesort"
    )

    # Values stay numeric so the table's own column sorting compares numbers rather
    # than strings; presentation is handled by the shared column configuration.
    if not show_table(filtered, columns=_TABLE_COLUMNS):
        return
    show_table_count(filtered, singular_label="airport")

    st.subheader("Airport detail")
    labels = filtered["airport_label"].tolist()
    selected_label = st.selectbox("Airport", options=labels, index=0, label_visibility="collapsed")
    row = filtered.loc[filtered["airport_label"] == selected_label].head(1).iloc[0]

    left, right = st.columns([1.15, 1])
    with left:
        st.markdown(f"**{row['airport_name']}**")
        st.caption(f"{row['iata_code']}  ·  {row['city']}, {row['state']}  ·  community {int(row['leiden_community_id'])}")
        st.plotly_chart(_profile_chart(row), width="stretch", config={"displayModeBar": False})
    with right:
        top, bottom = st.columns(2)
        with top:
            st.metric("Departures", format_integer(row["flights_out"]))
            st.metric("Total degree", format_integer(row["degree_total"]))
        with bottom:
            st.metric("Arrivals", format_integer(row["flights_in"]))
            st.metric("PageRank", format_score(row["pagerank"], digits=5))
