"""Methodology page (APP-07): implementation-aligned formulas and caveats."""

from __future__ import annotations

import streamlit as st


def render_methodology_page() -> None:
    """Render APP-07 methodology content aligned to implementation."""
    st.title("Methodology")
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
        Ripple propagation uses a 2-hop structural approximation with dependency weight:
        """
    )
    st.latex(r"W(i,j) = w(i,j) + w(j,i)")
    st.latex(r"Share(i,j) = \frac{W(i,j)}{\sum_k W(i,k)}")
    st.latex(r"E1(j \mid r) = Shock(r) \cdot Share(r,j)")
    st.latex(r"E2(k \mid r) = \lambda \cdot \sum_j \left[E1(j \mid r)\cdot Share(j,k)\right]")
    st.markdown(
        """
        Constants used in the implementation:
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
        These are properties of the specified model, verified against this
        implementation. They affect how the scores should be read.
        """
    )

    st.subheader("What the ripple model does and does not claim")
    st.markdown(
        """
        Ripple exposure once favoured low-degree airports. A fixed shock of 100 was
        conserved regardless of the removed airport's size, and `Share` divided it
        among that airport's neighbours, so the larger the airport the thinner its own
        shock spread. On a real 348-airport snapshot **every major hub scored exactly
        zero**, and severity — a count of airports above a fixed threshold — took only
        **nine distinct values across 348 airports**.

        Both are fixed. The shock is now proportional to the removed airport's strength
        (§8.6) and severity is the traffic-weighted mean exposure (§9.3). Severity now
        takes 332 distinct values and ranks ATL, DFW, DEN, ORD.

        The pair was chosen by testing it against the December 2022 disruption rather
        than by argument: it raised agreement with what actually happened from
        ρ = +0.387 to **+0.411**, and from +0.386 to **+0.457** once airport size is
        controlled for.

        What it still does not claim: this is a *structural* propagation over route
        dependencies, capped at two hops. It does not model aircraft rotations, crew
        legality, or passenger rebooking, and it does not predict delay minutes.
        """
    )

    st.subheader("Connectivity terms are measured in traffic, not airports")
    st.markdown(
        """
        Both connectivity terms once counted airports and reachable pairs equally,
        which treated losing ATL and losing ANC as the same event. On a 50-airport
        snapshot each term took only **two distinct values across all fifty
        airports**, so `ImpactScore` collapsed onto its ripple term and peripheral
        airports outranked the largest hubs.

        Both are now weighted by the traffic at the airports involved (spec §9.1,
        §9.2), which restores the discrimination: the same snapshot yields fifty
        distinct values, and ORD and ATL rank first and second.

        This remains a *structural* measure. It says what a removal does to the
        network's ability to carry traffic, not how many passengers were actually
        disrupted on any given day.
        """
    )

    st.subheader("Percentile ties are resolved by the max rule")
    st.markdown(
        """
        The specification defines `P()` as a percentile rank scaled to 0 through 100
        but does not state how ties are broken. Every composite here uses the same
        max-rank rule, so tied values all receive the rank of the highest member of
        their group and the top value always reaches exactly 100.

        This matters because some inputs are coarse. `ImpactScore` in particular often
        takes only a handful of distinct values across a snapshot, which produces large
        tie groups and percentile jumps. Comparing two airports whose underlying scores
        are tied is not meaningful.
        """
    )

    st.subheader("Eigenvector centrality is scoped to the connected core")
    st.markdown(
        """
        Eigenvector centrality is well defined only inside a strongly connected
        component. It used to be abandoned entirely — an empty column — whenever the
        snapshot as a whole was not strongly connected, which cost every airport in the
        giant component a value it could legitimately have carried.

        It is now computed on the largest strongly connected component, which holds
        nearly every airport on a real snapshot, and left undefined outside it. An
        airport that genuinely cannot carry a comparable value shows no value rather
        than a misleading one, and the pipeline logs how many airports were in scope.
        """
    )

    st.subheader("Scope")
    st.markdown(
        """
        - Structural network analytics, not an operational or delay simulator. Ripple
          exposure approximates local dependency and models no airline operations.
        - One month per snapshot. Scores rank airports *within* a snapshot and are not
          comparable across months without recomputing percentiles jointly.
        - U.S. domestic only, filtered on the master coordinate country code.
        - Missing routes or airports upstream propagate into every downstream metric.
        """
    )
