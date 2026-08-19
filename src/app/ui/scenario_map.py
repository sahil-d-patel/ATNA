"""Geographic figure for the scenario editor.

Kept apart from the page module because building this map is a self-contained
rendering concern: it takes the baseline geography, the routes to draw, and an
optional exposure frame, and returns a figure. Nothing here reads or writes session
state, which makes the map testable without a Streamlit runtime.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from app.ui.theme import GEO_LAYOUT, SEQUENTIAL, SEVERITY


def build_scenario_map(
    airports_geo: pd.DataFrame,
    edges_df: pd.DataFrame,
    weight_threshold: float,
    selected_airport_id: int | None,
    exposure_df: pd.DataFrame | None,
) -> go.Figure:
    fig = go.Figure()
    airport_lookup = airports_geo.dropna(subset=["latitude", "longitude"]).set_index("airport_id")

    # Route lines (filtered by weight). Interleave endpoint coordinates as
    # [origin, destination, None, ...] so each route is a separate line segment,
    # built vectorially rather than with a Python-level row loop.
    heavy_edges = edges_df.loc[edges_df["analysis_weight"] >= weight_threshold]
    valid_edges = heavy_edges.loc[
        heavy_edges["origin_id"].isin(airport_lookup.index)
        & heavy_edges["destination_id"].isin(airport_lookup.index)
    ]
    origins = valid_edges["origin_id"]
    destinations = valid_edges["destination_id"]
    separators = np.full(len(valid_edges), None, dtype=object)
    lats = np.column_stack([
        airport_lookup.loc[origins, "latitude"].to_numpy(),
        airport_lookup.loc[destinations, "latitude"].to_numpy(),
        separators,
    ]).ravel().tolist()
    lons = np.column_stack([
        airport_lookup.loc[origins, "longitude"].to_numpy(),
        airport_lookup.loc[destinations, "longitude"].to_numpy(),
        separators,
    ]).ravel().tolist()

    fig.add_trace(
        go.Scattergeo(
            lat=lats, lon=lons, mode="lines",
            line={"width": 0.4, "color": "rgba(80,80,80,0.18)"},
            hoverinfo="skip", showlegend=False,
        )
    )

    # Affected airports overlay
    affected_ids: set[int] = set()
    if exposure_df is not None and not exposure_df.empty:
        affected_ids = {int(i) for i in exposure_df["airport_id"]}
        exp_lookup = exposure_df.set_index("airport_id")
        affected = airports_geo.loc[
            airports_geo["airport_id"].isin(affected_ids)
        ].dropna(subset=["latitude", "longitude"]).copy()

        if not affected.empty:
            affected["aff_exposure"] = affected["airport_id"].map(exp_lookup["exposure_score"]).fillna(0)
            affected["aff_hop"] = affected["airport_id"].map(exp_lookup["hop_level"]).fillna(2).astype(int)
            fig.add_trace(
                go.Scattergeo(
                    lat=affected["latitude"], lon=affected["longitude"],
                    mode="markers",
                    marker={
                        "size": 11,
                        "color": affected["aff_exposure"],
                        "colorscale": [[0, SEVERITY["negligible"]], [0.5, SEVERITY["moderate"]],
                                       [1, SEVERITY["severe"]]],
                        "cmin": 0,
                        "cmax": float(affected["aff_exposure"].max()) or 1.0,
                        "showscale": True,
                        "colorbar": {"title": "Exposure", "x": 1.02, "len": 0.5, "y": 0.75},
                        "line": {"width": 1.2, "color": "#7f0000"},
                        "opacity": 0.92,
                    },
                    customdata=affected[["airport_id", "iata_code", "airport_name", "aff_hop", "aff_exposure"]].values,
                    text=[
                        (
                            f"<b>AFFECTED</b>: {row.iata_code} (ID {int(row.airport_id)})<br>"
                            f"{row.airport_name}<br>"
                            f"Hop {int(row.aff_hop)} — exposure {row.aff_exposure:.1f}"
                        )
                        for row in affected.itertuples(index=False)
                    ],
                    hoverinfo="text", name="Affected airports", showlegend=True,
                )
            )

    # Baseline airports (dimmed when a scenario is active)
    base = airports_geo.loc[~airports_geo["airport_id"].isin(affected_ids)]
    if selected_airport_id is not None:
        base = base.loc[base["airport_id"] != selected_airport_id]
    base = base.dropna(subset=["latitude", "longitude"])

    has_scenario = selected_airport_id is not None or len(affected_ids) > 0
    node_opacity = 0.35 if has_scenario else 0.9

    fig.add_trace(
        go.Scattergeo(
            lat=base["latitude"], lon=base["longitude"],
            mode="markers",
            marker={
                "size": (base["hub_score"].clip(lower=10.0) / 8.0 + 3.0).clip(upper=18.0),
                "color": base["vulnerability_score"],
                "colorscale": SEQUENTIAL,
                "showscale": not has_scenario,
                "colorbar": {"title": "Vulnerability", "len": 0.5, "y": 0.25},
                "opacity": node_opacity,
                "line": {"width": 0.5, "color": "white"},
            },
            customdata=base[["airport_id", "iata_code", "airport_name"]].values,
            text=[
                (
                    f"<b>{row.iata_code}</b> — {row.airport_name}<br>"
                    f"ID: {int(row.airport_id)}<br>"
                    f"Vulnerability: {row.vulnerability_score:.1f}  |  Community: {int(row.leiden_community_id)}<br>"
                    f"<i>Click to simulate removal</i>"
                )
                for row in base.itertuples(index=False)
            ],
            hoverinfo="text", name="Airports", showlegend=True,
        )
    )

    # Removed airport marker (red X)
    if selected_airport_id is not None:
        removed = airports_geo.loc[
            airports_geo["airport_id"] == selected_airport_id
        ].dropna(subset=["latitude", "longitude"])
        if not removed.empty:
            r = removed.iloc[0]
            fig.add_trace(
                go.Scattergeo(
                    lat=[r["latitude"]], lon=[r["longitude"]],
                    mode="markers+text",
                    marker={
                        "symbol": "x", "size": 18, "color": "#e74c3c",
                        "line": {"width": 2.5, "color": "#7f0000"}, "opacity": 1.0,
                    },
                    text=[f"✕ {r['iata_code']}"],
                    textposition="top center",
                    textfont={"size": 11, "color": "#c0392b"},
                    hovertext=(
                        f"<b>REMOVED</b>: {r['iata_code']} (ID {int(r['airport_id'])})<br>"
                        f"{r['airport_name']}<br><i>Click Undo or Restore network below to revert</i>"
                    ),
                    hoverinfo="text", name="Removed airport", showlegend=True,
                )
            )

    fig.update_layout(
        # Plotly resets camera state whenever a figure is replaced, and this figure is
        # rebuilt on every rerun. A constant uirevision tells plotly.js to preserve the
        # user's zoom and pan across those rebuilds, so simulating a removal no longer
        # throws the map back to the full-country view.
        uirevision="scenario-editor-map",
        title={
            "text": (
                "Click any airport to simulate its removal from the network"
                if not has_scenario
                else "Simulation active — click another airport to re-run, or revert below"
            ),
            "x": 0.01, "xanchor": "left", "font": {"size": 13},
        },
        geo=GEO_LAYOUT,
        legend={
            "orientation": "h", "yanchor": "bottom", "y": -0.06,
            "xanchor": "left", "x": 0, "font": {"size": 11},
        },
        margin={"l": 0, "r": 0, "t": 36, "b": 0},
        height=530,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig
