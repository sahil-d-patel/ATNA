"""Design tokens, the shared Plotly template, and page chrome.

The visual language is deliberately plain. Surfaces are warm neutrals, exactly one
accent marks interactive affordances, and saturated color is reserved for encoding
data. A reader should be able to assume that anything colorful on screen carries
meaning rather than decoration.

Every page calls :func:`apply_page_chrome` once, before rendering anything, so the
Plotly template is registered and the stylesheet is present.
"""

from __future__ import annotations

import plotly.graph_objects as go
import plotly.io as pio

from app.streamlit_compat import st

# --- Palette -----------------------------------------------------------------
# Warm neutrals rather than blue-grays: they sit better under the map's land fill
# and keep the teal accent the only cool color on the page.
INK = "#1C1917"
INK_MUTED = "#57534E"
# Darkened from #A8A29E, which measured 2.5:1 on the canvas and failed WCAG AA.
# This clears 4.5:1 on both the canvas and raised surfaces.
INK_FAINT = "#78716C"
SURFACE = "#FFFFFF"
CANVAS = "#FAFAF9"
HAIRLINE = "#E7E5E4"

ACCENT = "#0F766E"
ACCENT_SOFT = "#CCFBF1"

# Severity ramp for scenario impact. Four steps, because a continuous scale invites
# false precision on a score that is itself a coarse blend.
SEVERITY = {
    "negligible": "#0F766E",
    "moderate": "#B45309",
    "severe": "#B91C1C",
}

# Sequential ramp for 0-100 percentile scores. Single hue family, light to dark, so
# it stays readable in grayscale and for the most common color vision deficiencies.
SEQUENTIAL = [
    [0.00, "#F0FDFA"],
    [0.25, "#99F6E4"],
    [0.50, "#2DD4BF"],
    [0.75, "#0D9488"],
    [1.00, "#134E4A"],
]

# Qualitative palette for Leiden communities. Ordered for maximum separation between
# adjacent entries, since neighboring communities often sit next to each other.
COMMUNITY_COLORS = [
    "#0F766E",
    "#B45309",
    "#1E40AF",
    "#9D174D",
    "#3F6212",
    "#6D28D9",
    "#0E7490",
    "#9A3412",
]

# Geography styling, shared by every map so the basemap never competes with markers.
GEO_LAYOUT = {
    "scope": "usa",
    "projection_type": "albers usa",
    "showland": True,
    "landcolor": "#F5F5F4",
    "showocean": True,
    "oceancolor": "#EFF6F6",
    "showlakes": False,
    "subunitcolor": "#E7E5E4",
    "subunitwidth": 0.6,
    "countrycolor": "#D6D3D1",
    "bgcolor": "rgba(0,0,0,0)",
}

_TEMPLATE_NAME = "atna"

_STYLESHEET = """
<style>
  /* Tighten the default top padding so pages start near the viewport top. */
  .block-container { padding-top: 2.4rem; max-width: 1500px; }

  /* Typographic scale. Streamlit's defaults are sized for prose, not dashboards. */
  h1 { font-size: 1.6rem !important; font-weight: 650 !important; letter-spacing: -0.015em; }
  h2 { font-size: 1.15rem !important; font-weight: 640 !important; margin-top: 1.9rem !important; }
  h3 { font-size: 0.95rem !important; font-weight: 640 !important; }

  /* Numerals line up in columns only with tabular figures. */
  [data-testid="stMetricValue"], [data-testid="stDataFrame"] {
      font-variant-numeric: tabular-nums;
  }
  [data-testid="stMetricValue"] { font-size: 1.55rem !important; font-weight: 620 !important; }
  [data-testid="stMetricLabel"] {
      font-size: 0.74rem !important;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      color: #57534E !important;
  }

  /* Metrics read as one instrument cluster rather than four floating numbers. */
  [data-testid="stMetric"] {
      background: #FFFFFF;
      border: 1px solid #E7E5E4;
      border-radius: 6px;
      padding: 0.85rem 1rem;
  }

  /* Quieter chrome: the sidebar is navigation, not content. */
  [data-testid="stSidebarNav"] { padding-top: 0.5rem; }
  section[data-testid="stSidebar"] { border-right: 1px solid #E7E5E4; }

  /* Dataframes sit flush in their container with a single hairline. */
  [data-testid="stDataFrame"] { border: 1px solid #E7E5E4; border-radius: 6px; }

  /* Captions carry provenance and counts, so keep them legible but recessive. */
  [data-testid="stCaptionContainer"] { color: #57534E !important; font-size: 0.8rem !important; }
</style>
"""


def _build_template() -> go.layout.Template:
    """Plotly template matching the application surface."""
    return go.layout.Template(
        layout={
            "font": {"family": "system-ui, -apple-system, Segoe UI, sans-serif",
                     "size": 12, "color": INK},
            "title": {"font": {"size": 14, "color": INK}, "x": 0.0, "xanchor": "left"},
            "paper_bgcolor": "rgba(0,0,0,0)",
            "plot_bgcolor": "rgba(0,0,0,0)",
            "colorway": COMMUNITY_COLORS,
            "colorscale": {"sequential": SEQUENTIAL},
            "margin": {"l": 8, "r": 8, "t": 44, "b": 8},
            "xaxis": {
                "gridcolor": HAIRLINE, "zerolinecolor": HAIRLINE, "linecolor": HAIRLINE,
                "ticks": "outside", "tickcolor": HAIRLINE, "ticklen": 4,
                "title": {"font": {"size": 11, "color": INK_MUTED}},
            },
            "yaxis": {
                "gridcolor": HAIRLINE, "zerolinecolor": HAIRLINE, "linecolor": HAIRLINE,
                "ticks": "outside", "tickcolor": HAIRLINE, "ticklen": 4,
                "title": {"font": {"size": 11, "color": INK_MUTED}},
            },
            "legend": {
                "bgcolor": "rgba(255,255,255,0.85)", "bordercolor": HAIRLINE,
                "borderwidth": 1, "font": {"size": 11},
            },
            "hoverlabel": {
                "bgcolor": SURFACE, "bordercolor": HAIRLINE,
                "font": {"size": 11, "color": INK},
            },
            "geo": GEO_LAYOUT,
        }
    )


def register_plotly_template() -> None:
    """Register and select the ATNA template. Safe to call repeatedly."""
    if _TEMPLATE_NAME not in pio.templates:
        pio.templates[_TEMPLATE_NAME] = _build_template()
    pio.templates.default = _TEMPLATE_NAME


def apply_page_chrome() -> None:
    """Install the stylesheet and Plotly template. Call once per page render."""
    register_plotly_template()
    st.markdown(_STYLESHEET, unsafe_allow_html=True)


def page_header(title: str, description: str, *, meta: str | None = None) -> None:
    """Standard page heading: title, one line of orientation, optional provenance.

    Keeping the description to a single sentence is intentional. A dashboard page
    should say what the reader is looking at and then get out of the way.
    """
    st.title(title)
    st.caption(description if meta is None else f"{description}  ·  {meta}")


def severity_for(impact_score: float) -> tuple[str, str]:
    """Map an impact score to a (label, color) pair.

    Thresholds are presentational only and never feed a stored artifact.
    """
    if impact_score >= 40.0:
        return "Severe", SEVERITY["severe"]
    if impact_score >= 15.0:
        return "Moderate", SEVERITY["moderate"]
    return "Negligible", SEVERITY["negligible"]
