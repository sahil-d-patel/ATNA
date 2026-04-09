# Phase 2 validation notes — Graph metrics & communities

**Date:** 2026-04-09  
**Snapshot:** 2025-12  

## Environment

- **Python:** 3.11.9
- **networkx:** 3.6.1
- **python-igraph:** 0.11.9
- **leidenalg:** 0.10.2
- **pandas:** 2.3.3
- **numpy:** 2.4.1

## Sanity narrative (hub vs bridge vs PageRank)

- **Hub score**: Highest values concentrate on major traffic hubs (high total strength + high PageRank + high degree), as expected per §7.6.
- **Bridge score**: Highlights structural connectors (high betweenness) and is not intended to be identical to raw traffic rankings per Phase 2 context.
- **PageRank**: Provides a link-structure view of importance on the directed weighted analysis graph (§7.4); used as a hub component, but inspected on its own for plausibility.

## METR-02 reconciliation

- `nodes.csv` strength/degree are cross-checked against graph-derived values (Phase 2 plan `02-03`).

## Route criticality spot-checks

- `route_metrics.csv` includes:
  - `cross_community_flag ∈ {0,100}`
  - `route_criticality_score = 0.70*P(w(i,j)) + 0.30*CrossCommunity(i,j)` (§7.10)
- Cross-community routes should be neither 0% nor 100% in typical snapshots (sanity band enforced in tests with skip for degenerate cases).

For this snapshot, cross-community share observed ~46% (sanity OK).

## Validation artifacts

- **Map image:** `outputs/maps/phase2_community_map_2025-12.png`
- **Community mapping legend:** `outputs/maps/phase2_community_legend_2025-12.csv`
  - Includes raw `leiden_community_id` plus anchored display labels (`C01`, `C02`, ...)
  - Anchoring rule is deterministic per snapshot (sorted by community size, tie-break by min airport id)
- **Numeric checks:** `outputs/maps/phase2_validation_metrics_2025-12.json`
  - Includes cross-community route share and METR-02 reconciliation pass/fail status

The map is a smoke-test visualization, not a standalone proof. Use the legend and JSON metrics artifact together for auditable validation.

## Reproducibility stance

- Centralities and Leiden are computed from processed `edges.csv` / `nodes.csv` and config snapshot id.
- Raw Leiden IDs may vary across environments; use the anchored display labels in the legend artifact for run-to-run visual comparison.

## Deferred

- `vulnerability_score` remains **NaN** until Phase 3 (scenario impact integration; METR-07).

