"""Shared Streamlit UI primitives with empty-state guards."""

from __future__ import annotations

from typing import Iterable

import pandas as pd

try:
    import streamlit as st
except ModuleNotFoundError:  # pragma: no cover - fallback for non-UI test environments
    class _StreamlitFallback:
        @staticmethod
        def metric(*_args, **_kwargs):  # type: ignore[no-untyped-def]
            return None

        @staticmethod
        def info(*_args, **_kwargs):  # type: ignore[no-untyped-def]
            return None

        @staticmethod
        def dataframe(*_args, **_kwargs):  # type: ignore[no-untyped-def]
            return None

        @staticmethod
        def caption(*_args, **_kwargs):  # type: ignore[no-untyped-def]
            return None

    st = _StreamlitFallback()  # type: ignore[assignment]


EMPTY_FILTER_MESSAGE = "No rows for current filters."


def show_metric_card(label: str, value: object, help_text: str | None = None) -> None:
    """Render a metric card with optional help tooltip."""
    st.metric(label=label, value=value, help=help_text)


def show_empty_state(message: str = EMPTY_FILTER_MESSAGE) -> None:
    """Render a consistent empty-state message."""
    st.info(message)


def show_dataframe_safe(
    df: pd.DataFrame,
    *,
    columns: Iterable[str] | None = None,
    message: str = EMPTY_FILTER_MESSAGE,
    use_container_width: bool = True,
) -> bool:
    """Render dataframe only when rows exist; otherwise show empty-state message."""
    if columns is not None:
        selected = [col for col in columns if col in df.columns]
        df = df.loc[:, selected]

    if df.empty:
        show_empty_state(message)
        return False

    width = "stretch" if use_container_width else "content"
    st.dataframe(df, width=width)
    return True


def show_table_count(df: pd.DataFrame, singular_label: str = "row") -> None:
    """Render row-count caption for currently displayed table."""
    count = len(df.index)
    suffix = singular_label if count == 1 else f"{singular_label}s"
    st.caption(f"{count:,} {suffix}")
