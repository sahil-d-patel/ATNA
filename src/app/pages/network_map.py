"""Network map page with threshold-safe filtering."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from app.config import load_app_config
from app.data_loader import load_edges, load_metrics, load_route_metrics
from app.ui.components import EMPTY_FILTER_MESSAGE, show_empty_state


def _build_plot(filtered_edges: pd.DataFrame, airport_xy: pd.DataFrame) -> go.Figure:
    fig = go.Figure()

    airport_lookup = airport_xy.set_index("airport_id")
    line_x: list[float | None] = []
    line_y: list[float | None] = []
    line_text: list[str] = []
    for _, route in filtered_edges.iterrows():
        origin = int(route["origin_id"])
        destination = int(route["destination_id"])
        if origin not in airport_lookup.index or destination not in airport_lookup.index:
            continue

        ox, oy = airport_lookup.at[origin, "hub_score"], airport_lookup.at[origin, "bridge_score"]
        dx, dy = airport_lookup.at[destination, "hub_score"], airport_lookup.at[destination, "bridge_score"]
        route_text = (
            f"{origin} -> {destination}<br>"
            f"month={int(route['month'])}<br>"
            f"analysis_weight={route['analysis_weight']:.3f}<br>"
            f"flight_count={int(route['flight_count'])}<br>"
            f"route_criticality={float(route.get('route_criticality_score', float('nan'))):.3f}"
        )
        line_x.extend([ox, dx, None])
        line_y.extend([oy, dy, None])
        line_text.extend([route_text, route_text, ""])

    fig.add_trace(
        go.Scatter(
            x=line_x,
            y=line_y,
            mode="lines",
            hoverinfo="text",
            text=line_text,
            line={"width": 1, "color": "rgba(120,120,120,0.35)"},
            showlegend=False,
        )
    )

    fig.add_trace(
        go.Scatter(
            x=airport_xy["hub_score"],
            y=airport_xy["bridge_score"],
            mode="markers",
            text=[
                (
                    f"airport={int(row.airport_id)}<br>"
                    f"community={int(row.leiden_community_id)}<br>"
                    f"vulnerability={row.vulnerability_score:.3f}"
                )
                for row in airport_xy.itertuples(index=False)
            ],
            hoverinfo="text",
            marker={
                "size": airport_xy["vulnerability_score"].clip(lower=5) / 4 + 5,
                "color": airport_xy["vulnerability_score"],
                "colorscale": "Viridis",
                "showscale": True,
                "colorbar": {"title": "Vulnerability"},
                "line": {"width": 0.5, "color": "white"},
            },
            showlegend=False,
        )
    )
    fig.update_layout(
        xaxis_title="Hub score",
        yaxis_title="Bridge score",
        title="Airport network projection (routes + airport risk context)",
        margin={"l": 10, "r": 10, "t": 50, "b": 10},
    )
    return fig


def render_network_map_page() -> None:
    """Render APP-02 network map."""
    config = load_app_config()
    edges_df = load_edges(config)
    metrics_df = load_metrics(config)
    route_metrics_df = load_route_metrics(config)

    st.title("APP-02 Network Map")
    st.caption(
        f"Snapshot `{config.snapshot_id}` routes visualized with month and analysis-weight filters."
    )

    month_options = sorted(int(month) for month in edges_df["month"].dropna().unique())
    selected_months = st.multiselect(
        "Months",
        options=month_options,
        default=month_options,
        help="Filters route rows by month while keeping airport context stable.",
    )

    max_weight = float(edges_df["analysis_weight"].max())
    min_weight = st.slider(
        "Minimum analysis weight",
        min_value=0.0,
        max_value=max_weight,
        value=0.0,
        step=0.1,
    )

    filtered_edges = edges_df.loc[edges_df["analysis_weight"] >= min_weight].copy()
    if selected_months:
        filtered_edges = filtered_edges.loc[filtered_edges["month"].isin(selected_months)]
    else:
        filtered_edges = filtered_edges.iloc[0:0]

    if filtered_edges.empty:
        show_empty_state(EMPTY_FILTER_MESSAGE)
        return

    airport_ids = pd.unique(
        pd.concat([filtered_edges["origin_id"], filtered_edges["destination_id"]], ignore_index=True)
    )
    airport_xy = metrics_df.loc[metrics_df["airport_id"].isin(airport_ids)].copy()
    if airport_xy.empty:
        show_empty_state(EMPTY_FILTER_MESSAGE)
        return

    merged = filtered_edges.merge(
        route_metrics_df.loc[:, ["origin_id", "destination_id", "route_criticality_score"]],
        on=["origin_id", "destination_id"],
        how="left",
    )
    fig = _build_plot(merged, airport_xy)
    st.plotly_chart(fig, width="stretch")
