"""Shared Streamlit UI primitives with empty-state guards.

Table rendering goes through :func:`show_table` so that column labels, number
formatting, and score bars stay identical on every page. Pages describe what a column
means; they do not each re-invent how a percentile should look.
"""

from __future__ import annotations

from collections.abc import Iterable

import pandas as pd

from app.streamlit_compat import st

EMPTY_FILTER_MESSAGE = "No rows match the current filters."

# Human-readable headers for the artifact column names, applied automatically.
COLUMN_LABELS: dict[str, str] = {
    "airport_id": "ID",
    "iata_code": "Code",
    "airport_name": "Airport",
    "airport_label": "Airport",
    "city": "City",
    "state": "State",
    "origin_id": "Origin",
    "destination_id": "Destination",
    "origin_label": "Origin",
    "destination_label": "Destination",
    "hub_score": "Hub",
    "bridge_score": "Bridge",
    "vulnerability_score": "Vulnerability",
    "route_criticality_score": "Criticality",
    "exposure_score": "Exposure",
    "exposure_rank": "Rank",
    "hop_level": "Hop",
    "pagerank": "PageRank",
    "betweenness": "Betweenness",
    "eigenvector": "Eigenvector",
    "leiden_community_id": "Community",
    "community_size": "Airports",
    "community_traffic": "Traffic",
    "internal_density": "Density",
    "analysis_weight": "Weight",
    "flight_count": "Flights",
    "passenger_count": "Passengers",
    "strength_total": "Strength",
    "degree_total": "Degree",
    "flights_out": "Departures",
    "flights_in": "Arrivals",
    "cross_community_flag": "Cross-community",
    "route": "Route",
    "relation": "Relation",
}

# Columns on the shared 0-100 percentile scale, rendered as bars so relative standing
# is legible without reading every digit.
_SCORE_COLUMNS = frozenset(
    {
        "hub_score",
        "bridge_score",
        "vulnerability_score",
        "route_criticality_score",
        "exposure_score",
    }
)

_INTEGER_COLUMNS = frozenset(
    {
        "airport_id",
        "origin_id",
        "destination_id",
        "flight_count",
        "passenger_count",
        "seat_count",
        "community_size",
        "degree_total",
        "flights_out",
        "flights_in",
        "exposure_rank",
        "hop_level",
        "leiden_community_id",
    }
)

_PRECISE_COLUMNS = frozenset({"pagerank", "betweenness", "eigenvector", "internal_density"})


def show_metric_card(label: str, value: object, help_text: str | None = None) -> None:
    """Render a metric card with optional help tooltip."""
    st.metric(label=label, value=value, help=help_text)


def show_empty_state(message: str = EMPTY_FILTER_MESSAGE) -> None:
    """Render a consistent empty-state message."""
    st.info(message)


def build_column_config(df: pd.DataFrame) -> dict[str, object]:
    """Column configuration for ``df``: readable headers and typed formatting.

    Percentile scores become bars on a fixed 0-100 domain, so bar length is comparable
    across tables rather than rescaling to whatever happens to be in view.
    """
    config: dict[str, object] = {}
    for column in df.columns:
        label = COLUMN_LABELS.get(column, column.replace("_", " ").capitalize())
        if column in _SCORE_COLUMNS and pd.api.types.is_numeric_dtype(df[column]):
            config[column] = st.column_config.ProgressColumn(
                label, format="%.1f", min_value=0.0, max_value=100.0
            )
        elif column in _INTEGER_COLUMNS and pd.api.types.is_numeric_dtype(df[column]):
            config[column] = st.column_config.NumberColumn(label, format="%d")
        elif column in _PRECISE_COLUMNS and pd.api.types.is_numeric_dtype(df[column]):
            config[column] = st.column_config.NumberColumn(label, format="%.4f")
        elif pd.api.types.is_float_dtype(df[column]):
            config[column] = st.column_config.NumberColumn(label, format="%.2f")
        else:
            config[column] = st.column_config.Column(label)
    return config


def show_table(
    df: pd.DataFrame,
    *,
    columns: Iterable[str] | None = None,
    message: str = EMPTY_FILTER_MESSAGE,
    height: int | None = None,
    hide_index: bool = True,
) -> bool:
    """Render a dataframe with shared formatting, or an empty state when it has no rows.

    Returns ``True`` when rows were rendered, so callers can chain a row-count caption.
    """
    if columns is not None:
        selected = [column for column in columns if column in df.columns]
        df = df.loc[:, selected]

    if df.empty:
        show_empty_state(message)
        return False

    # `height=None` is rejected outright rather than treated as "auto", so only pass it
    # when the caller actually asked for a fixed height.
    extra = {"height": height} if height is not None else {}
    st.dataframe(
        df,
        width="stretch",
        hide_index=hide_index,
        column_config=build_column_config(df),
        **extra,
    )
    return True


def show_dataframe_safe(
    df: pd.DataFrame,
    *,
    columns: Iterable[str] | None = None,
    message: str = EMPTY_FILTER_MESSAGE,
    use_container_width: bool = True,
) -> bool:
    """Backwards-compatible alias for :func:`show_table`."""
    del use_container_width  # width is always "stretch" now
    return show_table(df, columns=columns, message=message)


def show_table_count(df: pd.DataFrame, singular_label: str = "row") -> None:
    """Render row-count caption for currently displayed table."""
    count = len(df.index)
    suffix = singular_label if count == 1 else f"{singular_label}s"
    st.caption(f"{count:,} {suffix}")
