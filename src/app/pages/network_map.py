"""Network map page with threshold-safe filtering."""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from app.config import load_app_config
from app.data_loader import load_edges, load_metrics, load_route_metrics
from app.ui.components import EMPTY_FILTER_MESSAGE, show_empty_state


def _build_plot(edges_df: pd.DataFrame, airport_xy: pd.DataFrame) -> go.Figure:
    fig = go.Figure()

    airport_lookup = airport_xy.set_index("airport_id")
    valid = edges_df.loc[
        edges_df["origin_id"].isin(airport_lookup.index)
        & edges_df["destination_id"].isin(airport_lookup.index)
    ]
    origins = valid["origin_id"]
    destinations = valid["destination_id"]

    # Interleave endpoint coordinates as [origin, destination, None, ...] so each
    # route renders as a separate line segment without a Python-level row loop.
    ox = airport_lookup.loc[origins, "hub_score"].to_numpy()
    oy = airport_lookup.loc[origins, "bridge_score"].to_numpy()
    dx = airport_lookup.loc[destinations, "hub_score"].to_numpy()
    dy = airport_lookup.loc[destinations, "bridge_score"].to_numpy()
    separators = np.full(len(valid), None, dtype=object)
    line_x = np.column_stack([ox, dx, separators]).ravel().tolist()
    line_y = np.column_stack([oy, dy, separators]).ravel().tolist()

    # Vectorized rounding + astype(str) instead of a per-row lambda: hover text is
    # rebuilt for every route on each rerun, so Python-level formatting here scales
    # directly with edge count.
    route_text = (
        origins.astype(int).astype(str) + " -> " + destinations.astype(int).astype(str)
        + "<br>month=" + valid["month"].astype(int).astype(str)
        + "<br>analysis_weight=" + valid["analysis_weight"].round(3).astype(str)
        + "<br>flight_count=" + valid["flight_count"].astype(int).astype(str)
        + "<br>route_criticality="
        + pd.to_numeric(valid["route_criticality_score"]).round(3).astype(str)
    ).to_numpy(dtype=object)
    blanks = np.full(len(valid), "", dtype=object)
    line_text = np.column_stack([route_text, route_text, blanks]).ravel().tolist()

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
            text=(
                "airport=" + airport_xy["airport_id"].astype(int).astype(str)
                + "<br>community=" + airport_xy["leiden_community_id"].astype(int).astype(str)
                + "<br>vulnerability=" + airport_xy["vulnerability_score"].round(3).astype(str)
            ),
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
    try:
        edges_df = load_edges(config)
        metrics_df = load_metrics(config)
        route_metrics_df = load_route_metrics(config)
    except ValueError as exc:
        st.error(f"Unable to load network map artifacts: {exc}")
        return

    st.title("Network Map")
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
