"""Airport explorer page with sortable table and drilldown."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from app.config import load_app_config
from app.data_loader import load_metrics, load_nodes
from app.ui.components import EMPTY_FILTER_MESSAGE, show_dataframe_safe, show_empty_state, show_metric_card
from app.ui.formatters import format_integer, format_score


def _build_airport_table(metrics_df: pd.DataFrame, nodes_df: pd.DataFrame) -> pd.DataFrame:
    merged = metrics_df.merge(nodes_df, on=["snapshot_id", "airport_id"], how="left")
    return merged.loc[
        :,
        [
            "airport_id",
            "leiden_community_id",
            "hub_score",
            "bridge_score",
            "vulnerability_score",
            "pagerank",
            "betweenness",
            "eigenvector",
            "flights_out",
            "flights_in",
            "degree_total",
        ],
    ].copy()


def render_airport_explorer_page() -> None:
    """Render APP-03 airport explorer."""
    config = load_app_config()
    metrics_df = load_metrics(config)
    nodes_df = load_nodes(config)
    airport_df = _build_airport_table(metrics_df, nodes_df)

    st.title("APP-03 Airport Explorer")
    st.caption(
        f"Snapshot `{config.snapshot_id}` sortable airport matrix with vulnerability-aware drilldown."
    )

    airport_query = st.text_input("Airport ID contains", value="")
    community_options = sorted(int(v) for v in airport_df["leiden_community_id"].dropna().unique())
    selected_communities = st.multiselect(
        "Community filter",
        options=community_options,
        default=community_options,
    )

    filtered = airport_df.copy()
    if airport_query:
        filtered = filtered.loc[
            filtered["airport_id"].astype(str).str.contains(airport_query.strip(), regex=False)
        ]
    if selected_communities:
        filtered = filtered.loc[filtered["leiden_community_id"].isin(selected_communities)]
    else:
        filtered = filtered.iloc[0:0]

    sort_options = ["vulnerability_score", "hub_score", "bridge_score", "pagerank", "airport_id"]
    sort_column = st.selectbox("Sort by", options=sort_options, index=0)
    descending = st.toggle("Descending", value=True)
    filtered = filtered.sort_values(by=sort_column, ascending=not descending, kind="mergesort")

    if not show_dataframe_safe(filtered, message=EMPTY_FILTER_MESSAGE):
        return

    detail_ids = filtered["airport_id"].astype(int).tolist()
    selected_airport_id = st.selectbox("Airport drilldown", options=detail_ids, index=0)
    detail_row = filtered.loc[filtered["airport_id"] == selected_airport_id].head(1)
    if detail_row.empty:
        show_empty_state(EMPTY_FILTER_MESSAGE)
        return

    row = detail_row.iloc[0]
    st.subheader(f"Airport {int(row['airport_id'])} details")
    col1, col2, col3 = st.columns(3)
    with col1:
        show_metric_card("Vulnerability score", format_score(row["vulnerability_score"]))
        show_metric_card("Hub score", format_score(row["hub_score"]))
    with col2:
        show_metric_card("Bridge score", format_score(row["bridge_score"]))
        show_metric_card("PageRank", format_score(row["pagerank"], digits=6))
    with col3:
        show_metric_card("Community", format_integer(row["leiden_community_id"]))
        show_metric_card("Total degree", format_integer(row["degree_total"]))

    st.caption(
        f"Traffic proxy: outbound={format_integer(row['flights_out'])}, "
        f"inbound={format_integer(row['flights_in'])}"
    )
