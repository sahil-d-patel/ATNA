"""Communities page (APP-04): Leiden community exploration."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from app.data_loader import load_communities, load_metrics
from app.ui.components import show_dataframe_safe, show_empty_state, show_metric_card, show_table_count
from app.ui.formatters import format_integer, format_percent, format_score

def _community_options(communities_df: pd.DataFrame) -> list[str]:
    community_ids = sorted(communities_df["leiden_community_id"].astype(int).unique().tolist())
    return ["All communities", *[str(cid) for cid in community_ids]]


def _filter_by_selected_community(
    communities_df: pd.DataFrame, metrics_df: pd.DataFrame, selected: str
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if selected == "All communities":
        return communities_df.copy(), metrics_df.copy()
    community_id = int(selected)
    return (
        communities_df.loc[communities_df["leiden_community_id"].astype(int) == community_id].copy(),
        metrics_df.loc[metrics_df["leiden_community_id"].astype(int) == community_id].copy(),
    )


def _split_ranked_ids(raw_ids: object) -> str:
    if raw_ids is None:
        return "N/A"
    text = str(raw_ids).strip()
    if not text:
        return "N/A"
    return ", ".join(part.strip() for part in text.split("|") if part.strip())


def render_communities_page() -> None:
    """Render APP-04 communities analysis."""
    st.title("APP-04 Communities")
    st.caption("Explore Leiden partitions, community-level structure, and top members by hub/bridge role.")

    try:
        communities_df = load_communities()
        metrics_df = load_metrics()
    except ValueError as exc:
        st.error(f"Unable to load community artifacts: {exc}")
        return

    options = _community_options(communities_df)
    selected_community = st.selectbox(
        "Select community",
        options=options,
        help="Filter all cards and tables to a single Leiden community.",
    )
    top_k = st.slider("Top airports to show", min_value=3, max_value=20, value=10, step=1)

    selected_communities, selected_metrics = _filter_by_selected_community(
        communities_df, metrics_df, selected_community
    )

    if selected_communities.empty:
        show_empty_state("No communities for current filters.")
        return

    total_communities = selected_communities["leiden_community_id"].nunique()
    total_airports = len(selected_metrics.index)
    total_traffic = selected_communities["community_traffic"].sum()
    avg_internal_density = selected_communities["internal_density"].mean()

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        show_metric_card("Communities", format_integer(total_communities))
    with c2:
        show_metric_card("Airports in view", format_integer(total_airports))
    with c3:
        show_metric_card(
            "Community traffic (sum)",
            format_score(total_traffic, digits=2),
            help_text="Sum of community_traffic for selected rows in communities.csv.",
        )
    with c4:
        show_metric_card(
            "Avg. internal density",
            format_percent(avg_internal_density, digits=2),
            help_text="Average of InternalDensity(C)=internal_edges(C)/( |C|*(|C|-1) ).",
        )

    st.subheader("Community summary")
    summary_df = selected_communities.copy()
    summary_df["community_size"] = summary_df["community_size"].map(format_integer)
    summary_df["community_traffic"] = summary_df["community_traffic"].map(lambda v: format_score(v, digits=2))
    summary_df["internal_density"] = summary_df["internal_density"].map(lambda v: format_percent(v, digits=2))
    summary_df["top_hub_airport_ids"] = summary_df["top_hub_airport_ids"].map(_split_ranked_ids)
    summary_df["top_bridge_airport_ids"] = summary_df["top_bridge_airport_ids"].map(_split_ranked_ids)
    show_dataframe_safe(
        summary_df.sort_values("leiden_community_id"),
        columns=[
            "leiden_community_id",
            "community_size",
            "community_traffic",
            "internal_density",
            "top_hub_airport_ids",
            "top_bridge_airport_ids",
        ],
    )
    show_table_count(summary_df, singular_label="community")

    st.subheader("Top hub airports")
    hub_df = (
        selected_metrics.sort_values("hub_score", ascending=False)
        .head(top_k)
        .loc[:, ["airport_id", "leiden_community_id", "hub_score", "bridge_score", "vulnerability_score"]]
        .copy()
    )
    hub_df["hub_score"] = hub_df["hub_score"].map(format_score)
    hub_df["bridge_score"] = hub_df["bridge_score"].map(format_score)
    hub_df["vulnerability_score"] = hub_df["vulnerability_score"].map(format_score)
    if show_dataframe_safe(hub_df):
        show_table_count(hub_df, singular_label="airport")

    st.subheader("Top bridge airports")
    bridge_df = (
        selected_metrics.sort_values("bridge_score", ascending=False)
        .head(top_k)
        .loc[:, ["airport_id", "leiden_community_id", "bridge_score", "hub_score", "vulnerability_score"]]
        .copy()
    )
    bridge_df["bridge_score"] = bridge_df["bridge_score"].map(format_score)
    bridge_df["hub_score"] = bridge_df["hub_score"].map(format_score)
    bridge_df["vulnerability_score"] = bridge_df["vulnerability_score"].map(format_score)
    if show_dataframe_safe(bridge_df):
        show_table_count(bridge_df, singular_label="airport")
