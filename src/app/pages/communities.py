"""Communities page: Leiden partitions, their composition, and their leading airports."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from app.config import load_app_config
from app.data_loader import load_airports, load_airports_geo, load_communities
from app.ui.components import show_empty_state, show_table, show_table_count
from app.ui.formatters import format_integer, format_score
from app.ui.theme import COMMUNITY_COLORS, apply_page_chrome, page_header

_ALL_COMMUNITIES = "All communities"
_MEMBER_COLUMNS = ["iata_code", "airport_name", "city", "state",
                   "hub_score", "bridge_score", "vulnerability_score"]


def _resolve_ranked_ids(raw_ids: object, code_by_id: dict[int, str]) -> str:
    """Turn a pipe-delimited airport-id list into readable IATA codes.

    ``communities.csv`` stores ids because it is a data contract; a reader needs codes.
    Unresolvable ids are passed through rather than dropped, so a join problem stays
    visible instead of silently shrinking the list.
    """
    text = "" if raw_ids is None else str(raw_ids).strip()
    if not text:
        return "N/A"
    codes = [
        code_by_id.get(int(part), part)
        for part in (piece.strip() for piece in text.split("|"))
        if part
    ]
    return ", ".join(str(code) for code in codes)


def _composition_chart(geo_df: pd.DataFrame) -> go.Figure:
    """Stacked view of how many airports sit in each community, by structural role."""
    grouped = (
        geo_df.groupby("leiden_community_id")
        .agg(airports=("airport_id", "size"), traffic=("hub_score", "mean"))
        .reset_index()
        .sort_values("leiden_community_id")
    )
    figure = go.Figure(
        go.Bar(
            x=grouped["leiden_community_id"].astype(str),
            y=grouped["airports"],
            marker={
                "color": [COMMUNITY_COLORS[int(c) % len(COMMUNITY_COLORS)]
                          for c in grouped["leiden_community_id"]],
                "line": {"width": 0},
            },
            customdata=grouped["traffic"],
            hovertemplate=(
                "Community %{x}<br>%{y} airports<br>Mean hub score %{customdata:.1f}<extra></extra>"
            ),
        )
    )
    figure.update_layout(
        title="Airports per community",
        height=240,
        xaxis={"title": "Community", "showgrid": False},
        yaxis={"title": "Airports"},
    )
    return figure


def render_communities_page() -> None:
    """Render APP-04 communities analysis."""
    apply_page_chrome()
    config = load_app_config()
    try:
        communities_df = load_communities(config)
        geo_df = load_airports_geo(config)
        airports_df = load_airports(config)
    except ValueError as exc:
        st.error(f"Unable to load community artifacts: {exc}")
        return

    page_header(
        "Communities",
        "Leiden partitions of the network, and the airports that anchor each one.",
        meta=f"Snapshot {config.snapshot_id}",
    )

    code_by_id = dict(
        zip(airports_df["airport_id"].astype(int), airports_df["iata_code"], strict=True)
    )
    community_ids = sorted(communities_df["leiden_community_id"].astype(int).unique().tolist())

    filter_column, top_k_column = st.columns([2, 3])
    with filter_column:
        selected = st.selectbox(
            "Community", options=[_ALL_COMMUNITIES, *[str(cid) for cid in community_ids]],
            help="Filter every card and table below to one Leiden community.",
        )
    with top_k_column:
        top_k = st.slider("Top airports to list", min_value=3, max_value=20, value=8, step=1)

    if selected == _ALL_COMMUNITIES:
        selected_communities, selected_members = communities_df, geo_df
    else:
        community_id = int(selected)
        selected_communities = communities_df.loc[
            communities_df["leiden_community_id"].astype(int) == community_id
        ]
        selected_members = geo_df.loc[
            geo_df["leiden_community_id"].astype(int) == community_id
        ]

    if selected_communities.empty:
        show_empty_state("No communities match the current filters.")
        return

    metrics = st.columns(4)
    metrics[0].metric("Communities", format_integer(selected_communities["leiden_community_id"].nunique()))
    metrics[1].metric("Airports in view", format_integer(len(selected_members.index)))
    metrics[2].metric(
        "Community traffic",
        format_score(selected_communities["community_traffic"].sum(), digits=1),
        help="Sum of internal analysis weight for the communities in view.",
    )
    metrics[3].metric(
        "Mean internal density",
        format_score(selected_communities["internal_density"].mean() * 100, digits=1) + "%",
        help="internal_edges(C) / (|C| * (|C| - 1)), averaged over the communities in view.",
    )

    if selected == _ALL_COMMUNITIES:
        st.plotly_chart(_composition_chart(geo_df), width="stretch",
                        config={"displayModeBar": False})

    st.subheader("Community summary")
    summary = selected_communities.sort_values("leiden_community_id").copy()
    summary["top_hub_airport_ids"] = summary["top_hub_airport_ids"].map(
        lambda ids: _resolve_ranked_ids(ids, code_by_id)
    )
    summary["top_bridge_airport_ids"] = summary["top_bridge_airport_ids"].map(
        lambda ids: _resolve_ranked_ids(ids, code_by_id)
    )
    summary = summary.rename(
        columns={"top_hub_airport_ids": "Top hubs", "top_bridge_airport_ids": "Top bridges"}
    )
    if show_table(
        summary,
        columns=["leiden_community_id", "community_size", "community_traffic",
                 "internal_density", "Top hubs", "Top bridges"],
    ):
        show_table_count(summary, singular_label="community")

    hubs_tab, bridges_tab, vulnerable_tab = st.tabs(["Top hubs", "Top bridges", "Most vulnerable"])
    for tab, column in [
        (hubs_tab, "hub_score"),
        (bridges_tab, "bridge_score"),
        (vulnerable_tab, "vulnerability_score"),
    ]:
        with tab:
            ranked = selected_members.nlargest(top_k, column).loc[:, _MEMBER_COLUMNS]
            if show_table(ranked):
                show_table_count(ranked, singular_label="airport")
