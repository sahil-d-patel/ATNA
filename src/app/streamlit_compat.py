"""Shared Streamlit import shim for headless (non-UI) environments.

Exposes a module-level ``st`` that is the real Streamlit package when it is
installed, or a minimal fallback that stubs the subset of Streamlit attributes
the app touches at import/render time. Centralizing the fallback here keeps a
single source of truth for the stub instead of duplicating it in every module
that must import cleanly without Streamlit (e.g. non-UI unit tests).
"""

from __future__ import annotations

try:
    import streamlit as st
except ModuleNotFoundError:  # pragma: no cover - fallback for non-UI test environments
    class _StreamlitFallback:
        @staticmethod
        def cache_data(func=None, **_kwargs):  # type: ignore[no-untyped-def]
            if func is None:
                def decorator(inner):  # type: ignore[no-untyped-def]
                    return inner
                return decorator
            return func

        @staticmethod
        def cache_resource(func=None, **_kwargs):  # type: ignore[no-untyped-def]
            if func is None:
                def decorator(inner):  # type: ignore[no-untyped-def]
                    return inner
                return decorator
            return func

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
