"""Snapshot comparison: are the scores measuring structure, or one month's sampling?

A score that swings between consecutive months is describing the sample, not the
network. This page answers that question directly for whichever snapshots have been
built, and shows the airports that moved most — because an aggregate correlation hides
exactly the cases worth looking at.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from scipy import stats

from app.config import REPO_ROOT
from app.data_loader import _load_artifact
from app.streamlit_compat import st as compat_st
from app.ui.components import show_empty_state, show_table, show_table_count
from app.ui.theme import ACCENT, HAIRLINE, INK_MUTED, apply_page_chrome, page_header

PROCESSED_ROOT = REPO_ROOT / "data" / "processed"

SCORES = {
    "hub_score": "Hub score",
    "bridge_score": "Bridge score",
    "vulnerability_score": "Vulnerability",
}

# Above this, the ranking is reproducing itself between months rather than drifting.
STABLE_THRESHOLD = 0.90
MOSTLY_STABLE_THRESHOLD = 0.75


@compat_st.cache_data(show_spinner=False)
def _available_snapshots(root: str) -> list[str]:
    """Snapshot directories that actually contain the artifacts this page needs."""
    base = Path(root)
    if not base.is_dir():
        return []
    return sorted(
        entry.name
        for entry in base.iterdir()
        if entry.is_dir()
        and (entry / "metrics.csv").is_file()
        and (entry / "airports.csv").is_file()
    )


def _load_snapshot(snapshot_id: str) -> tuple[pd.DataFrame, pd.Series]:
    """Metrics for a snapshot, plus its airport-code lookup."""
    directory = PROCESSED_ROOT / snapshot_id
    metrics = _load_artifact(directory / "metrics.csv", "metrics", snapshot_id)
    airports = _load_artifact(directory / "airports.csv", "airports")
    codes = airports.set_index("airport_id_canonical")["airport_code_raw"]
    return metrics, codes


def _stability_verdict(rho: float) -> str:
    if rho >= STABLE_THRESHOLD:
        return "stable"
    if rho >= MOSTLY_STABLE_THRESHOLD:
        return "mostly stable"
    return "unstable"


def _movement_chart(movers: pd.DataFrame, baseline_id: str, comparison_id: str) -> go.Figure:
    """Slope chart: one line per airport, baseline score to comparison score."""
    figure = go.Figure()
    for _, row in movers.iterrows():
        rising = row["movement"] > 0
        figure.add_trace(
            go.Scatter(
                x=[baseline_id, comparison_id],
                y=[row["hub_score_base"], row["hub_score_comp"]],
                mode="lines+markers+text",
                line={"color": ACCENT if rising else INK_MUTED, "width": 1.6},
                marker={"size": 7},
                text=["", f"  {row['code']}"],
                textposition="middle right",
                textfont={"size": 10},
                hovertemplate=(
                    f"<b>{row['code']}</b><br>{baseline_id}: %{{y:.1f}}<extra></extra>"
                ),
                showlegend=False,
            )
        )
    figure.update_layout(
        title="Largest hub-score movements",
        height=430,
        # Snapshot ids look like dates, and Plotly will happily parse "2022-11" into
        # one and render a November timeline. They are two discrete categories.
        xaxis={
            "type": "category",
            "categoryorder": "array",
            "categoryarray": [baseline_id, comparison_id],
            "showgrid": False,
            "title": None,
        },
        yaxis={"title": "Hub score", "range": [0, 105], "gridcolor": HAIRLINE},
        margin={"l": 8, "r": 60, "t": 44, "b": 8},
    )
    return figure


def render_snapshot_comparison_page() -> None:
    """Render the snapshot stability comparison."""
    apply_page_chrome()
    page_header(
        "Snapshot Comparison",
        "Whether the scores describe the network or just one month of sampling.",
    )

    snapshots = _available_snapshots(str(PROCESSED_ROOT))
    if len(snapshots) < 2:
        show_empty_state(
            "Comparison needs two built snapshots. Only "
            f"{len(snapshots)} is available: {', '.join(snapshots) or 'none'}. "
            "Build another with a second config, for example "
            "`config/atna-2022-11.yaml`."
        )
        return

    baseline_column, comparison_column = st.columns(2)
    with baseline_column:
        baseline_id = st.selectbox("Baseline", options=snapshots, index=0)
    with comparison_column:
        others = [s for s in snapshots if s != baseline_id]
        comparison_id = st.selectbox("Compare against", options=others, index=0)

    try:
        baseline, codes = _load_snapshot(baseline_id)
        comparison, _ = _load_snapshot(comparison_id)
    except ValueError as exc:
        st.error(f"Unable to load snapshots: {exc}")
        return

    merged = baseline.merge(
        comparison, on="airport_id", suffixes=("_base", "_comp"), how="inner"
    )
    if merged.empty:
        show_empty_state("These snapshots share no airports.")
        return

    counts = st.columns(3)
    counts[0].metric("Airports in both", f"{len(merged):,}")
    counts[1].metric(f"Only in {baseline_id}", f"{len(baseline) - len(merged):,}")
    counts[2].metric(f"Only in {comparison_id}", f"{len(comparison) - len(merged):,}")

    st.subheader("Rank agreement")
    st.markdown(
        "Spearman correlation between the two months. A structural metric should "
        "reproduce its own ranking; a score that does not is describing the sample."
    )

    rows = []
    for column, label in SCORES.items():
        result = stats.spearmanr(merged[f"{column}_base"], merged[f"{column}_comp"])
        rows.append(
            {
                "Score": label,
                "Spearman rho": round(float(result.statistic), 3),
                "Verdict": _stability_verdict(float(result.statistic)),
            }
        )
    show_table(pd.DataFrame(rows))

    st.subheader("What moved")
    st.markdown(
        "The exceptions are the useful part, because the aggregate correlation hides "
        "them. A seasonal airport *should* move; a mover with no plausible explanation "
        "is worth investigating."
    )
    mover_count = st.slider("Airports to show", min_value=4, max_value=20, value=8, step=2)

    merged["movement"] = merged["hub_score_comp"] - merged["hub_score_base"]
    merged["code"] = merged["airport_id"].map(codes).fillna(merged["airport_id"].astype(str))
    movers = merged.reindex(merged["movement"].abs().nlargest(mover_count).index)

    st.plotly_chart(
        _movement_chart(movers, baseline_id, comparison_id),
        width="stretch",
        config={"displayModeBar": False},
    )

    table = movers.loc[:, ["code", "hub_score_base", "hub_score_comp", "movement"]].rename(
        columns={
            "code": "Code",
            "hub_score_base": baseline_id,
            "hub_score_comp": comparison_id,
            "movement": "Change",
        }
    )
    if show_table(table):
        show_table_count(table, singular_label="airport")
