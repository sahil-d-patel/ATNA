# Methodology

## Section Goal
Explain the modeling stack from graph construction to composite metrics and scenario scoring, so readers can understand how each visual is produced and what claims are justified.

## Related Visuals
- `visuals/network_map_min_analysis_weight_5.png`
- `visuals/community_map_2025-12.png`
- `visuals/top_5_critical_routes.png`
- `visuals/vulnerability_map.png`
- `visuals/DFW_removal_impact.png`
- `visuals/Yellowstone_airport_removal_impact.png`

## Analytical Pipeline
1. Build directed weighted graph from processed monthly route data.
2. Compute centralities and percentile scaling for comparability.
3. Detect communities with Leiden for meso-scale structure.
4. Score routes for criticality (weight + cross-community role).
5. Run removal scenarios and ripple propagation.
6. Aggregate impact into network-level health indicators.

## Core Definitions
- **Node:** airport.
- **Directed edge:** origin->destination route.
- **Analysis weight:** `log1p(flight_count)` for stability across wide traffic ranges.
- **Percentile scaling:** converts heterogeneous metrics onto common `[0,100]` scale.

## Airport Metrics
- **Hub Score:** blend of total strength, PageRank, and total degree percentiles.
- **Bridge Score:** betweenness percentile.
- **Vulnerability:** weighted blend of scenario impact percentile and bridge percentile.

Interpretation:
- Hub captures concentration and influence.
- Bridge captures structural brokerage.
- Vulnerability captures likely system consequence under failure.

## Community and Route Metrics
- **Leiden communities** partition airports into structure-based groups.
- **Cross-community flag:** binary structure indicator (same vs different community).
- **Route criticality:** weighted route importance blended with cross-community role.

This combination is what enables the route-level narrative in `top_5_critical_routes.png`.

## Scenario Methodology
- Two scenario families:
  - airport removal,
  - route removal.
- Ripple is propagated as a locked 2-hop structural approximation with hop discount (`lambda = 0.35`).
- Aggregates:
  - `LCC Loss`,
  - `Reachability Loss`,
  - `Ripple Severity`,
  - `Impact Score`,
  - `Network Health = 100 - Impact Score`.

## Visual-to-Method Mapping
- `network_map_min_analysis_weight_5.png` -> graph topology + filtered weighted links.
- `community_map_2025-12.png` -> Leiden partition output.
- `top_5_critical_routes.png` -> route criticality ranking.
- `vulnerability_map.png` -> vulnerability composition at airport level.
- `DFW_removal_impact.png` / `Yellowstone_airport_removal_impact.png` -> scenario engine outcomes and comparative disruption spread.

## Validation and Reliability Notes
- Community interpretation is paired with deterministic legend anchoring for snapshot-specific consistency.
- Scenario invariants are tested (e.g., second hop weaker than first under discounting).
- Metrics are intended for ranking/comparison inside a snapshot, not absolute causal prediction.
