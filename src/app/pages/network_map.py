"""Network map page: the route network drawn over U.S. geography."""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from app.config import load_app_config
from app.data_loader import load_airports_geo, load_edges, load_route_metrics
from app.ui.components import EMPTY_FILTER_MESSAGE, show_empty_state
from app.ui.theme import (
    COMMUNITY_COLORS,
    GEO_LAYOUT,
    HAIRLINE,
    apply_page_chrome,
    page_header,
)

# Cross-community routes are the interesting ones but also numerous, so they are
# tinted rather than emphasised: at 40% of all routes, a heavy stroke buries the map.
_ROUTE_COLOR = "rgba(120,113,108,0.22)"
_CROSS_COLOR = "rgba(180,83,9,0.30)"


def _route_segments(
    routes: pd.DataFrame, coords: pd.DataFrame
) -> tuple[list[float | None], list[float | None]]:
    """Interleave endpoint coordinates as [origin, destination, None, ...].

    One trace of separated segments instead of one trace per route: Plotly validates
    per trace, so a few hundred traces would dominate render time.
    """
    origin = coords.reindex(routes["origin_id"])
    destination = coords.reindex(routes["destination_id"])
    separator = np.full(len(routes), None, dtype=object)

    lons = np.column_stack(
        [origin["longitude"].to_numpy(), destination["longitude"].to_numpy(), separator]
    ).ravel()
    lats = np.column_stack(
        [origin["latitude"].to_numpy(), destination["latitude"].to_numpy(), separator]
    ).ravel()
    return lons.tolist(), lats.tolist()


def _build_map(
    routes: pd.DataFrame, airports: pd.DataFrame, coords: pd.DataFrame, *, show_cross: bool
) -> go.Figure:
    figure = go.Figure()

    within = routes.loc[routes["cross_community_flag"].astype(int) == 0]
    across = routes.loc[routes["cross_community_flag"].astype(int) == 100]

    for subset, color, name in [
        (within, _ROUTE_COLOR, "Within community"),
        (across, _CROSS_COLOR, "Cross-community"),
    ]:
        if subset.empty or (name == "Cross-community" and not show_cross):
            continue
        lons, lats = _route_segments(subset, coords)
        figure.add_trace(
            go.Scattergeo(
                lon=lons, lat=lats, mode="lines",
                line={"width": 0.8 if name == "Cross-community" else 0.6, "color": color},
                hoverinfo="skip", name=name,
            )
        )

    figure.add_trace(
        go.Scattergeo(
            lon=airports["longitude"], lat=airports["latitude"], mode="markers",
            marker={
                # Area, not radius, tracks the score: doubling a marker's width would
                # quadruple its perceived weight.
                "size": 6 + np.sqrt(airports["hub_score"].clip(lower=0)) * 1.9,
                "color": [
                    COMMUNITY_COLORS[int(c) % len(COMMUNITY_COLORS)]
                    for c in airports["leiden_community_id"]
                ],
                "line": {"width": 0.7, "color": "white"},
                "opacity": 0.92,
            },
            customdata=airports[
                ["iata_code", "airport_name", "hub_score", "bridge_score",
                 "vulnerability_score", "leiden_community_id"]
            ],
            hovertemplate=(
                "<b>%{customdata[0]}</b> · %{customdata[1]}"
                "<br>Hub %{customdata[2]:.1f}   Bridge %{customdata[3]:.1f}"
                "<br>Vulnerability %{customdata[4]:.1f}   Community %{customdata[5]}"
                "<extra></extra>"
            ),
            name="Airports",
            showlegend=False,
        )
    )

    figure.update_layout(
        uirevision="network-map",
        geo=GEO_LAYOUT,
        height=620,
        margin={"l": 0, "r": 0, "t": 10, "b": 0},
        legend={
            "orientation": "h", "yanchor": "bottom", "y": 0.01,
            "xanchor": "left", "x": 0.01, "bgcolor": "rgba(255,255,255,0.9)",
            "bordercolor": HAIRLINE, "borderwidth": 1,
        },
    )
    return figure


def render_network_map_page() -> None:
    """Render APP-02 network map."""
    apply_page_chrome()
    config = load_app_config()
    try:
        edges_df = load_edges(config)
        route_metrics_df = load_route_metrics(config)
        geo_df = load_airports_geo(config)
    except ValueError as exc:
        st.error(f"Unable to load network map artifacts: {exc}")
        return

    page_header(
        "Network Map",
        "Routes over U.S. geography. Marker size follows hub score, color follows community.",
        meta=f"Snapshot {config.snapshot_id}",
    )

    routes = edges_df.merge(
        route_metrics_df.loc[
            :, ["origin_id", "destination_id", "cross_community_flag", "route_criticality_score"]
        ],
        on=["origin_id", "destination_id"],
        how="inner",
    )

    weight_column, community_column, cross_column = st.columns([2.4, 2.4, 1.4])
    with weight_column:
        max_weight = float(edges_df["analysis_weight"].max())
        min_weight = st.slider(
            "Minimum route weight", min_value=0.0, max_value=round(max_weight, 2),
            value=0.0, step=0.1,
            help="Analysis weight is log1p(flight_count). Raise this to reveal the trunk network.",
        )
    with community_column:
        community_options = sorted(
            int(value) for value in geo_df["leiden_community_id"].dropna().unique()
        )
        selected_communities = st.multiselect(
            "Communities", options=community_options, default=community_options
        )
    with cross_column:
        show_cross = st.toggle("Cross-community", value=True,
                               help="Highlight routes that join two communities.")

    airports = geo_df.loc[
        geo_df["leiden_community_id"].isin(selected_communities)
    ].dropna(subset=["latitude", "longitude"])
    if airports.empty:
        show_empty_state(EMPTY_FILTER_MESSAGE)
        return

    visible_ids = set(airports["airport_id"].astype(int))
    routes = routes.loc[
        (routes["analysis_weight"] >= min_weight)
        & routes["origin_id"].isin(visible_ids)
        & routes["destination_id"].isin(visible_ids)
    ]
    if routes.empty:
        show_empty_state(EMPTY_FILTER_MESSAGE)
        return

    coords = airports.set_index("airport_id")[["latitude", "longitude"]]
    st.plotly_chart(
        _build_map(routes, airports, coords, show_cross=show_cross),
        width="stretch",
        config={"displayModeBar": False, "scrollZoom": True},
    )

    cross_count = int((routes["cross_community_flag"].astype(int) == 100).sum())
    st.caption(
        f"{len(airports):,} airports  ·  {len(routes):,} routes shown  ·  "
        f"{cross_count:,} cross-community"
    )
