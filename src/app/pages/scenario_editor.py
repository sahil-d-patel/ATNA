"""Scenario editor page (APP-06): interactive geographic map with history and revert support."""

from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from app.config import load_app_config
from app.data_loader import load_airports_geo, load_edges
from app.scenario_service import list_route_pairs, run_ui_scenario
from app.ui.components import show_dataframe_safe, show_empty_state, show_table_count
from app.ui.formatters import format_integer, format_score

_GEO_MAP_KEY = "scenario_geo_map"
_SS_AIRPORT = "se_airport_id"
_SS_RESULT = "se_result"
_SS_TYPE = "se_scenario_type"
_SS_HISTORY = "se_history"

# Each history entry:
# {
#   "airport_id": int | None,
#   "label": str,            e.g. "ABE — Lehigh Valley International"
#   "scenario_type": str,    "airport" | "route"
#   "scenario_row": dict,
#   "exposure_df": pd.DataFrame,
# }


# ---------------------------------------------------------------------------
# Session state helpers
# ---------------------------------------------------------------------------

def _init_state() -> None:
    defaults: dict[str, Any] = {
        _SS_AIRPORT: None,
        _SS_RESULT: None,
        _SS_TYPE: None,
        _SS_HISTORY: [],
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


def _push_history(entry: dict[str, Any]) -> None:
    st.session_state[_SS_HISTORY].append(entry)


def _apply_state(entry: dict[str, Any] | None) -> None:
    """Restore session state from a history entry, or clear to baseline if None."""
    if entry is None:
        st.session_state[_SS_AIRPORT] = None
        st.session_state[_SS_RESULT] = None
        st.session_state[_SS_TYPE] = None
    else:
        st.session_state[_SS_AIRPORT] = entry["airport_id"]
        st.session_state[_SS_TYPE] = entry["scenario_type"]
        st.session_state[_SS_RESULT] = {
            "scenario_row": entry["scenario_row"],
            "exposure_df": entry["exposure_df"],
        }


# ---------------------------------------------------------------------------
# Map builder
# ---------------------------------------------------------------------------

def _build_geo_map(
    airports_geo: pd.DataFrame,
    edges_df: pd.DataFrame,
    weight_threshold: float,
    selected_airport_id: int | None,
    exposure_df: pd.DataFrame | None,
) -> go.Figure:
    fig = go.Figure()
    airport_lookup = airports_geo.dropna(subset=["latitude", "longitude"]).set_index("airport_id")

    # Route lines (filtered by weight)
    heavy_edges = edges_df.loc[edges_df["analysis_weight"] >= weight_threshold]
    lats: list[float | None] = []
    lons: list[float | None] = []
    for _, route in heavy_edges.iterrows():
        o, d = int(route["origin_id"]), int(route["destination_id"])
        if o not in airport_lookup.index or d not in airport_lookup.index:
            continue
        lats += [airport_lookup.at[o, "latitude"], airport_lookup.at[d, "latitude"], None]
        lons += [airport_lookup.at[o, "longitude"], airport_lookup.at[d, "longitude"], None]

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
                        "colorscale": [[0, "#ffd580"], [0.5, "#ff7b00"], [1, "#c0392b"]],
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
                "colorscale": "Viridis",
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
        title={
            "text": (
                "Click any airport to simulate its removal from the network"
                if not has_scenario
                else "Simulation active — click another airport to re-run, or revert below"
            ),
            "x": 0.01, "xanchor": "left", "font": {"size": 13},
        },
        geo={
            "scope": "usa",
            "projection_type": "albers usa",
            "showland": True, "landcolor": "#f5f5f5",
            "showocean": True, "oceancolor": "#e9f3fb",
            "showlakes": True, "lakecolor": "#e9f3fb",
            "showcoastlines": True, "coastlinecolor": "#c0c0c0",
            "showframe": False, "bgcolor": "rgba(0,0,0,0)",
        },
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


# ---------------------------------------------------------------------------
# Result rendering
# ---------------------------------------------------------------------------

def _severity_info(impact_score: float) -> tuple[str, str]:
    """Return (label, streamlit method name) for the given impact score."""
    if impact_score < 20:
        return "Low impact", "success"
    elif impact_score < 50:
        return "Moderate impact", "warning"
    return "High impact", "error"


def _render_metric_cards(scenario_row: dict[str, object]) -> None:
    after_health = float(scenario_row["network_health"])
    after_impact = float(scenario_row["impact_score"])
    delta_health = after_health - 100.0
    delta_impact = after_impact

    severity_label, severity_fn = _severity_info(after_impact)
    getattr(st, severity_fn)(f"**{severity_label}** — impact score {after_impact:.1f}")

    st.subheader("Before vs after")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Network health (before)", "100.0")
    with c2:
        st.metric(
            "Network health (after)",
            f"{after_health:.1f}",
            delta=f"{delta_health:.1f} pts",
            delta_color="normal",
            help="Negative delta = network degraded. Red means worse.",
        )
    with c3:
        st.metric("Impact score (before)", "0.0")
    with c4:
        st.metric(
            "Impact score (after)",
            f"{after_impact:.1f}",
            delta=f"+{delta_impact:.1f} pts",
            delta_color="inverse",
            help="Positive delta = more disruption. Red means worse.",
        )

    d1, d2, d3 = st.columns(3)
    with d1:
        lcc = float(scenario_row["lcc_loss"])
        st.metric("LCC loss", f"{lcc:.1f}%", delta=f"+{lcc:.1f}%", delta_color="inverse",
                  help="Largest connected component lost as % of original.")
    with d2:
        reach = float(scenario_row["reachability_loss"])
        st.metric("Reachability loss", f"{reach:.1f}%", delta=f"+{reach:.1f}%", delta_color="inverse",
                  help="% of airport pairs that can no longer reach each other.")
    with d3:
        ripple = float(scenario_row["ripple_severity"])
        st.metric("Ripple severity", f"{ripple:.1f}%", delta=f"+{ripple:.1f}%", delta_color="inverse",
                  help="Weighted exposure across 2-hop ripple propagation.")


def _scenario_table(row: dict[str, object]) -> pd.DataFrame:
    return pd.DataFrame([row]).loc[
        :,
        [
            "scenario_id", "scenario_type", "impact_score", "network_health",
            "lcc_loss", "reachability_loss", "ripple_severity", "created_at",
        ],
    ]


def _render_exposure_outputs(exposure_df: pd.DataFrame) -> None:
    st.subheader("Affected airports")
    if exposure_df.empty:
        show_empty_state("No affected airports for this scenario.")
        return

    display = exposure_df.loc[:, ["airport_id", "hop_level", "exposure_score", "exposure_rank"]].copy()
    display["airport_id"] = display["airport_id"].map(format_integer)
    display["exposure_score"] = display["exposure_score"].map(format_score)
    if show_dataframe_safe(display, message="No affected airports for this scenario."):
        show_table_count(display, singular_label="airport")

    hop_counts = (
        exposure_df.groupby("hop_level", dropna=False)["airport_id"]
        .count().reset_index(name="airports")
    )
    hop_counts["hop_level"] = hop_counts["hop_level"].astype(int).astype(str)
    st.bar_chart(hop_counts.set_index("hop_level")["airports"])


# ---------------------------------------------------------------------------
# Page entry point
# ---------------------------------------------------------------------------

def render_scenario_editor_page() -> None:
    """Render APP-06 scenario editor with interactive map, history, and revert support."""
    config = load_app_config()
    airports_geo = load_airports_geo(config)
    edges_df = load_edges(config)
    route_pairs = list_route_pairs(config)

    st.title("Scenario Editor")
    st.caption(
        f"Snapshot `{config.snapshot_id}` — simulate the effect of removing an airport or route. "
        "Click directly on the map, or use the quick-find search below."
    )

    _init_state()

    selected_airport_id: int | None = st.session_state[_SS_AIRPORT]
    result: dict | None = st.session_state[_SS_RESULT]
    history: list[dict] = st.session_state[_SS_HISTORY]

    # ----------------------------------------------------------------
    # Quick-find + route weight controls (above map)
    # ----------------------------------------------------------------
    col_search, col_slider = st.columns([2, 3])

    with col_search:
        airport_options = sorted(
            airports_geo.dropna(subset=["latitude", "longitude"])
            .apply(lambda r: f"{r['iata_code']} — {r['airport_name']}", axis=1)
            .tolist()
        )
        search_label = st.selectbox(
            "Quick-find airport",
            options=["— search by name or code —"] + airport_options,
            index=0,
            help="Type to filter. Select an airport then click Simulate.",
        )
        if search_label != "— search by name or code —":
            iata_code = search_label.split(" — ")[0]
            match = airports_geo.loc[airports_geo["iata_code"] == iata_code]
            if not match.empty and st.button("Simulate removal", key="quick_find_btn"):
                clicked_id = int(match.iloc[0]["airport_id"])
                _run_airport_scenario(airports_geo, clicked_id, config)
                st.rerun()

    with col_slider:
        max_weight = float(edges_df["analysis_weight"].max())
        weight_threshold = st.slider(
            "Show routes with analysis weight ≥",
            min_value=0.0, max_value=max_weight, value=5.0, step=0.1,
            help="Higher = only busiest routes shown. Does not affect the simulation.",
        )

    # ----------------------------------------------------------------
    # Interactive map
    # ----------------------------------------------------------------
    exposure_df_for_map = result["exposure_df"] if result else None
    fig = _build_geo_map(airports_geo, edges_df, weight_threshold, selected_airport_id, exposure_df_for_map)
    event = st.plotly_chart(
        fig, on_select="rerun", selection_mode=["points"],
        key=_GEO_MAP_KEY, use_container_width=True,
    )

    # Handle map click
    selection = getattr(event, "selection", None)
    points = list(getattr(selection, "points", None) or [])
    if points:
        pt = points[0]
        customdata = pt.get("customdata") or []
        if customdata:
            clicked_id = int(customdata[0])
            if clicked_id != selected_airport_id:
                _run_airport_scenario(airports_geo, clicked_id, config)
                st.rerun()

    st.caption(
        "**Map guide:** dot size = hub score, dot color = vulnerability score (yellow → purple = low → high). "
        "Orange/red dots = airports affected by the simulated removal. ✕ = removed airport."
    )

    # ----------------------------------------------------------------
    # Status bar + revert controls
    # ----------------------------------------------------------------
    status_col, btn_col1, btn_col2 = st.columns([5, 1, 1])

    with status_col:
        if selected_airport_id is not None and result:
            airport_row = airports_geo.loc[airports_geo["airport_id"] == selected_airport_id]
            if not airport_row.empty:
                r = airport_row.iloc[0]
                impact = float(result["scenario_row"]["impact_score"])
                severity_label, _ = _severity_info(impact)
                st.info(
                    f"**Simulating removal of:** {r['iata_code']} — {r['airport_name']}  \n"
                    f"Vulnerability {r['vulnerability_score']:.1f} · Community {int(r['leiden_community_id'])} · "
                    f"{severity_label} (impact {impact:.1f})"
                )
        elif result and st.session_state[_SS_TYPE] == "route":
            st.info(f"**Route removal simulated.** See results below.")
        else:
            st.info("No active simulation. Click an airport on the map or use quick-find above.")

    with btn_col1:
        st.write("")  # vertical alignment spacer
        undo_disabled = len(history) == 0
        if st.button(
            "↩ Undo",
            key="undo_btn",
            disabled=undo_disabled,
            help="Revert to the previous scenario, or to baseline if only one step back.",
            use_container_width=True,
        ):
            history.pop()
            _apply_state(history[-1] if history else None)
            st.rerun()

    with btn_col2:
        st.write("")
        restore_disabled = result is None
        if st.button(
            "Restore network",
            key="restore_btn",
            disabled=restore_disabled,
            help="Clear all simulations and return the map to its baseline state.",
            use_container_width=True,
        ):
            st.session_state[_SS_HISTORY] = []
            _apply_state(None)
            st.rerun()

    # ----------------------------------------------------------------
    # Scenario history panel
    # ----------------------------------------------------------------
    if history:
        with st.expander(f"Scenario history ({len(history)} run{'s' if len(history) != 1 else ''})"):
            st.caption("Click **Load** on any row to restore that simulation.")
            for idx, entry in enumerate(reversed(history)):
                pos = len(history) - 1 - idx
                impact = float(entry["scenario_row"]["impact_score"])
                health = float(entry["scenario_row"]["network_health"])
                severity_label, _ = _severity_info(impact)
                h_col1, h_col2, h_col3, h_col4, h_col5 = st.columns([3, 2, 2, 2, 1])
                with h_col1:
                    st.write(f"**{entry['label']}**")
                with h_col2:
                    st.write(f"Impact: `{impact:.1f}`")
                with h_col3:
                    st.write(f"Health: `{health:.1f}`")
                with h_col4:
                    st.write(severity_label)
                with h_col5:
                    if st.button("Load", key=f"hist_load_{pos}"):
                        _apply_state(history[pos])
                        st.rerun()
    else:
        with st.expander("Scenario history (0 runs)"):
            st.caption("No scenarios run yet. Simulations appear here as you explore.")

    st.divider()

    # ----------------------------------------------------------------
    # Simulation results
    # ----------------------------------------------------------------
    result = st.session_state.get(_SS_RESULT)
    if result:
        _render_metric_cards(result["scenario_row"])

        with st.expander("Raw scenario data"):
            result_table = _scenario_table(result["scenario_row"]).copy()
            for col in ("impact_score", "network_health", "lcc_loss", "reachability_loss", "ripple_severity"):
                result_table[col] = result_table[col].map(format_score)
            show_dataframe_safe(result_table)

        _render_exposure_outputs(result["exposure_df"])
        st.divider()

    # ----------------------------------------------------------------
    # Route removal form
    # ----------------------------------------------------------------
    st.subheader("Route removal")
    st.caption("Remove a specific directed route and run the scenario engine.")

    route_labels = {f"{o} \u2192 {d}": (o, d) for o, d in route_pairs}
    with st.form("route-removal-form"):
        selected_route_label = st.selectbox(
            "Route to remove",
            options=list(route_labels.keys()),
            index=0,
        )
        route_submitted = st.form_submit_button("Run route removal scenario")

    if route_submitted:
        origin_id, destination_id = route_labels[selected_route_label]
        try:
            scenario_row, exp_df = run_ui_scenario(
                scenario_type="route_removal",
                payload={"origin_id": int(origin_id), "destination_id": int(destination_id)},
                config=config,
            )
        except Exception as exc:  # pragma: no cover
            st.error(f"Scenario run failed: {exc}")
            return
        label = f"Route: {origin_id} \u2192 {destination_id}"
        entry: dict[str, Any] = {
            "airport_id": None,
            "label": label,
            "scenario_type": "route",
            "scenario_row": scenario_row,
            "exposure_df": exp_df,
        }
        _push_history(entry)
        st.session_state[_SS_AIRPORT] = None
        st.session_state[_SS_TYPE] = "route"
        st.session_state[_SS_RESULT] = {"scenario_row": scenario_row, "exposure_df": exp_df}
        st.rerun()

    if not result:
        st.info("Click an airport on the map, use quick-find, or submit a route removal to run a simulation.")


# ---------------------------------------------------------------------------
# Internal: run and push an airport removal scenario
# ---------------------------------------------------------------------------

def _run_airport_scenario(
    airports_geo: pd.DataFrame,
    airport_id: int,
    config: Any,
) -> None:
    """Execute an airport removal, push to history, and update session state."""
    try:
        scenario_row, exp_df = run_ui_scenario(
            scenario_type="airport_removal",
            payload={"airport_id": airport_id},
            config=config,
        )
    except Exception as exc:  # pragma: no cover
        st.error(f"Scenario run failed: {exc}")
        return

    airport_row = airports_geo.loc[airports_geo["airport_id"] == airport_id]
    label = (
        f"{airport_row.iloc[0]['iata_code']} \u2014 {airport_row.iloc[0]['airport_name']}"
        if not airport_row.empty
        else f"Airport ID {airport_id}"
    )
    entry: dict[str, Any] = {
        "airport_id": airport_id,
        "label": label,
        "scenario_type": "airport",
        "scenario_row": scenario_row,
        "exposure_df": exp_df,
    }
    _push_history(entry)
    st.session_state[_SS_AIRPORT] = airport_id
    st.session_state[_SS_TYPE] = "airport"
    st.session_state[_SS_RESULT] = {"scenario_row": scenario_row, "exposure_df": exp_df}
