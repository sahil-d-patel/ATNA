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

    st.subheader("Ripple severity favours low-degree airports")
    st.markdown(
        """
        Removing an airport releases a fixed shock of 100, distributed across its
        neighbours in proportion to `Share(i,j)`, which normalises by that airport's
        *own* total dependency. A hub with 60 neighbours therefore spreads roughly 1.7
        to each, below the severity threshold of 10, and scores a ripple severity of
        **zero**. A peripheral airport with four neighbours concentrates 25 onto each
        and scores highly.

        The effect is structural, not a defect in the data: the more connected an
        airport is, the thinner its shock spreads. Consequently the vulnerability
        ranking can place mid-size airports above the largest hubs. Read
        `ripple_severity` as *concentration of local dependency*, not as
        network-wide importance.
        """
    )

    st.subheader("Connectivity terms go flat on well-connected networks")
    st.markdown(
        """
        `LCC_Loss` and `Reachability_Loss` only separate airports when removing one
        actually disconnects part of the network. If every airport has at least two
        independent paths into the core, no single removal disconnects anything, and
        both terms collapse to the same constant for every airport: losing 1 node of
        N, and the ordered pairs that node accounted for.

        When that happens, `ImpactScore` reduces to its ripple term alone, since the
        other two contribute an identical constant to every airport. This is
        observable on any densely connected snapshot, and it is worth checking the
        spread of those two columns before drawing conclusions from impact.
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

    st.subheader("Eigenvector centrality requires strong connectivity")
    st.markdown(
        """
        Eigenvector centrality is a secondary metric. It is well defined only on a
        strongly connected graph; when the snapshot is not strongly connected the
        column is written as empty rather than being filled with a value that would not
        mean what it appears to mean. The pipeline logs a warning when this happens.
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
