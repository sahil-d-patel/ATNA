"""Methodology page (APP-07): implementation-aligned formulas and caveats."""

from __future__ import annotations

import streamlit as st


def render_methodology_page() -> None:
    """Render APP-07 methodology content aligned to implementation."""
    st.title("APP-07 Methodology")
    st.caption("Data/model assumptions, formulas, and caveats used by this implementation.")

    st.header("Data pipeline and graph model")
    st.markdown(
        """
        - **Snapshot policy:** Monthly snapshots (`snapshot_id = YYYY-MM`) from processed artifacts.
        - **Primary graph:** Directed weighted airport network where edge weight is `analysis_weight`.
        - **Weight definition:** `analysis_weight = log1p(flight_count)`.
        - **App behavior:** Pages read precomputed artifacts (`metrics.csv`, `communities.csv`, `route_metrics.csv`,
          `scenarios.csv`, `scenario_exposure.csv`) through app loaders with required-column guards.
        """
    )

    st.header("Airport-level metrics")
    st.markdown(
        """
        The metrics engine computes centrality and percentile-scaled composites for comparison:
        """
    )
    st.latex(r"P(metric) = \text{percentile rank scaled to } [0, 100]")
    st.latex(
        r"HubScore(i) = 0.50 \cdot P(s_{total}(i)) + 0.30 \cdot P(PageRank(i)) + 0.20 \cdot P(deg_{total}(i))"
    )
    st.latex(r"BridgeScore(i) = P(Betweenness(i))")
    st.latex(r"Vulnerability(i) = 0.60 \cdot P(ImpactScore(remove\ i)) + 0.40 \cdot P(BridgeScore(i))")

    st.header("Community and route metrics")
    st.markdown(
        """
        **Leiden communities** partition airports into groups used by APP-04 and APP-05.
        """
    )
    st.latex(r"CommunityTraffic(C) = \sum_{(i,j)\in C} w(i,j)")
    st.latex(r"InternalDensity(C) = \frac{\text{internal edges}(C)}{|C| \cdot (|C|-1)}")
    st.latex(r"RouteCriticality(i,j) = 0.70 \cdot P(w(i,j)) + 0.30 \cdot CrossCommunity(i,j)")
    st.markdown(
        """
        `CrossCommunity(i,j)` is implemented as:
        - `100` when origin and destination belong to different Leiden communities
        - `0` otherwise
        """
    )

    st.header("Scenario ripple and aggregate scores")
    st.markdown(
        """
        Ripple propagation uses a locked 2-hop structural approximation with dependency weight:
        """
    )
    st.latex(r"W(i,j) = w(i,j) + w(j,i)")
    st.latex(r"Share(i,j) = \frac{W(i,j)}{\sum_k W(i,k)}")
    st.latex(r"E1(j \mid r) = Shock(r) \cdot Share(r,j)")
    st.latex(r"E2(k \mid r) = \lambda \cdot \sum_j \left[E1(j \mid r)\cdot Share(j,k)\right]")
    st.markdown(
        """
        Locked constants in implementation:
        - `Shock(airport removal) = 100`
        - `lambda = 0.35`
        - Hop depth is capped at 2 (hop 3+ ignored)
        """
    )
    st.latex(r"LCC\_Loss = 100 \cdot \left(1 - \frac{LCC_{post}}{LCC_{pre}}\right)")
    st.latex(r"Reachability\_Loss = 100 \cdot \left(1 - \frac{ReachablePairs_{post}}{ReachablePairs_{pre}}\right)")
    st.latex(r"RippleSeverity = 100 \cdot \frac{\#\{airports: exposure \ge 10\}}{total\_airports}")
    st.latex(r"ImpactScore = 0.40 \cdot LCC\_Loss + 0.30 \cdot Reachability\_Loss + 0.30 \cdot RippleSeverity")
    st.latex(r"NetworkHealth = 100 - ImpactScore")

    st.header("Known limitations")
    st.markdown(
        """
        - This is a **structural network analytics MVP**, not an operational delay simulator.
        - Ripple exposure is a simplified local dependency approximation and does not model airline operations.
        - Outputs depend on snapshot aggregation; interpretation should be month-specific.
        - Composite scores are percentile-based and are best used for ranking/comparison inside a snapshot.
        - Data quality constraints upstream (missing routes/airports) can affect downstream metrics.
        """
    )
