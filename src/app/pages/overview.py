"""Overview page: snapshot totals, structural leaders, and the hub/bridge divergence."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from app.config import load_app_config
from app.data_loader import load_airports_geo, load_communities, load_nodes, load_route_metrics
from app.ui.components import show_table, show_table_count
from app.ui.formatters import format_integer
from app.ui.theme import HAIRLINE, INK_MUTED, SEQUENTIAL, apply_page_chrome, page_header

_RANKING_COLUMNS = ["iata_code", "airport_name", "hub_score", "bridge_score",
                    "vulnerability_score", "leiden_community_id"]


def _leaders_chart(geo_df: pd.DataFrame, column: str, title: str, limit: int = 12) -> go.Figure:
    """Horizontal bar chart of the top airports by one score.

    Horizontal because airport labels are words: rotated vertical labels would be
    unreadable at this count.
    """
    top = geo_df.nlargest(limit, column).sort_values(column)
    figure = go.Figure(
        go.Bar(
            x=top[column],
            y=top["iata_code"],
            orientation="h",
            marker={
                "color": top[column],
                "colorscale": SEQUENTIAL,
                "cmin": 0,
                "cmax": 100,
                "line": {"width": 0},
            },
            customdata=top["airport_name"],
            hovertemplate="<b>%{y}</b> · %{customdata}<br>Score %{x:.1f}<extra></extra>",
        )
    )
    figure.update_layout(
        title=title,
        height=max(260, 22 * len(top) + 70),
        xaxis={"range": [0, 100], "title": None},
        yaxis={"title": None, "showgrid": False},
        margin={"l": 8, "r": 8, "t": 44, "b": 8},
    )
    return figure


def _divergence_chart(geo_df: pd.DataFrame) -> go.Figure:
    """Hub score against bridge score, labelling the airports that disagree most.

    This is the project's central claim in one panel: traffic volume and structural
    importance are different properties. Airports far from the diagonal are the ones
    whose criticality a traffic table would miss, in either direction.
    """
    frame = geo_df.dropna(subset=["hub_score", "bridge_score"]).copy()
    frame["divergence"] = frame["bridge_score"] - frame["hub_score"]
    # Label only the sparse, mid-to-high-hub region. Raw top-divergence picks land in
    # the dense low-hub cluster, where every airport shares the same tied bridge score
    # and the text becomes an unreadable pile.
    labelable = frame.loc[frame["hub_score"] >= 25.0]
    outliers = labelable.nlargest(5, "divergence")

    figure = go.Figure()
    figure.add_trace(
        go.Scatter(
            x=[0, 100], y=[0, 100], mode="lines",
            line={"color": HAIRLINE, "width": 1, "dash": "dot"},
            hoverinfo="skip", showlegend=False,
        )
    )
    figure.add_trace(
        go.Scatter(
            x=frame["hub_score"],
            y=frame["bridge_score"],
            mode="markers",
            marker={
                "size": 9,
                "color": frame["vulnerability_score"],
                "colorscale": SEQUENTIAL,
                "cmin": 0, "cmax": 100,
                "line": {"width": 0.5, "color": "white"},
                "colorbar": {
                    "title": {"text": "Vulnerability", "font": {"size": 10}},
                    "thickness": 10, "len": 0.7, "outlinewidth": 0,
                },
            },
            customdata=frame[["iata_code", "airport_name"]],
            hovertemplate=(
                "<b>%{customdata[0]}</b> · %{customdata[1]}"
                "<br>Hub %{x:.1f}   Bridge %{y:.1f}<extra></extra>"
            ),
            showlegend=False,
        )
    )
    figure.add_trace(
        go.Scatter(
            x=outliers["hub_score"], y=outliers["bridge_score"],
            mode="text", text=outliers["iata_code"],
            textposition="middle right",
            textfont={"size": 10, "color": INK_MUTED},
            hoverinfo="skip", showlegend=False,
        )
    )
    figure.update_layout(
        title="Hub score against bridge score",
        height=420,
        xaxis={"title": "Hub score", "range": [-4, 104]},
        yaxis={"title": "Bridge score", "range": [-4, 104]},
    )
    return figure


def render_overview_page() -> None:
    """Render APP-01 overview dashboard."""
    apply_page_chrome()
    config = load_app_config()
    try:
        geo_df = load_airports_geo(config)
        nodes_df = load_nodes(config)
        route_metrics_df = load_route_metrics(config)
        communities_df = load_communities(config)
    except ValueError as exc:
        st.error(f"Unable to load overview artifacts: {exc}")
        return

    airport_count = int(geo_df["airport_id"].nunique())
    route_count = int(route_metrics_df.shape[0])
    total_flights = int(nodes_df["flights_out"].sum())
    community_count = int(communities_df["leiden_community_id"].nunique())
    cross_community = int((route_metrics_df["cross_community_flag"] > 0).sum())

    page_header(
        "Overview",
        "Structural summary of the U.S. domestic network for one monthly snapshot.",
        meta=f"Snapshot {config.snapshot_id}",
    )

    columns = st.columns(5)
    for column, (label, value, help_text) in zip(
        columns,
        [
            ("Airports", format_integer(airport_count), "Airports in the domestic slice."),
            ("Routes", format_integer(route_count), "Directed origin to destination pairs."),
            ("Departures", format_integer(total_flights), "Completed outbound flights."),
            ("Communities", format_integer(community_count), "Leiden partitions."),
            (
                "Cross-community",
                format_integer(cross_community),
                "Routes joining two different communities. These carry the structural load "
                "that holds regions together.",
            ),
        ],
        strict=True,
    ):
        with column:
            st.metric(label=label, value=value, help=help_text)

    st.subheader("Where volume and structure disagree")
    st.markdown(
        "Hub score follows traffic. Bridge score follows position. Airports above the "
        "diagonal carry more structural load than their volume suggests, and are the ones "
        "a passenger-count ranking would overlook."
    )
    st.plotly_chart(_divergence_chart(geo_df), width="stretch",
                    config={"displayModeBar": False})

    left, right = st.columns(2)
    with left:
        st.plotly_chart(
            _leaders_chart(geo_df, "hub_score", "Largest hubs"),
            width="stretch", config={"displayModeBar": False},
        )
    with right:
        st.plotly_chart(
            _leaders_chart(geo_df, "vulnerability_score", "Most vulnerable airports"),
            width="stretch", config={"displayModeBar": False},
        )

    st.subheader("Rankings")
    hubs, bridges, vulnerable = st.tabs(["Hubs", "Bridges", "Vulnerability"])
    for tab, score_column, caption in [
        (hubs, "hub_score", "Ranked by hub score: traffic strength, PageRank, and degree."),
        (bridges, "bridge_score", "Ranked by bridge score: betweenness on the inverse-weight graph."),
        (vulnerable, "vulnerability_score",
         "Ranked by vulnerability: modelled impact of removing the airport, blended with bridge score."),
    ]:
        with tab:
            st.caption(caption)
            ranked = geo_df.nlargest(15, score_column).loc[:, _RANKING_COLUMNS]
            if show_table(ranked):
                show_table_count(ranked, singular_label="airport")
