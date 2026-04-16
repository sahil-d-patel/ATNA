---
phase: 02-graph-metrics-communities
plan: 04
subsystem: metrics
tags: [leiden, igraph, leidenalg, networkx, communities]

# Dependency graph
requires:
  - phase: 02-graph-metrics-communities
    provides: METR-01 graph builder + METR-03 centralities + METR-04 hub/bridge scores (02-03)
provides:
  - Leiden community partition (airport_id -> leiden_community_id)
  - communities.csv rollup per §6.5 / §7.9
  - metrics.csv populated leiden_community_id synchronized with communities.csv
affects: [route_metrics, cross_community_flag, streamlit-communities-page]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "NetworkX as analysis source of truth; igraph/leidenalg only for Leiden partitioning"
    - "Stable community id relabeling (0..K-1) to keep outputs deterministic across runs"

key-files:
  created:
    - src/metrics/leiden_communities.py
    - tests/test_communities.py
  modified:
    - src/metrics/run_metrics.py
    - tests/test_hub_bridge_metrics.py

key-decisions:
  - "Run Leiden on the full directed graph; isolated nodes become singleton communities"
  - "Serialize top airport id lists with '|' delimiter (AIRPORT_ID_LIST_DELIM)"

patterns-established:
  - "Write metrics.csv and communities.csv from the same in-memory analysis graph to guarantee ID alignment"

# Metrics
duration: 45min
completed: 2026-04-09
---

# Phase 2 Plan 04: METR-05 Leiden communities Summary

**Leiden partitioning + communities.csv rollups (traffic/density/top hubs/bridges) with consistent `leiden_community_id` across metrics artifacts**

## Performance

- **Duration:** 45min
- **Started:** 2026-04-09T05:22:00Z
- **Completed:** 2026-04-09T06:07:04Z
- **Tasks:** 3
- **Files modified:** 5

## Accomplishments
- Added Leiden community detection via NetworkX → igraph conversion using analysis weights
- Implemented communities.csv rollups per §6.5 and §7.9 (traffic, density, top hub/bridge lists)
- Wired pipeline to write communities.csv and populate metrics.csv `leiden_community_id`, with end-to-end ID alignment tests

## Task Commits

Each task was committed atomically:

1. **Task 1: Leiden partition** - `9c5536d` (feat)
2. **Task 2: communities.csv metrics** - `cc28428` (feat)
3. **Task 3: Merge into metrics.csv and integration test** - `17f86e6` (feat)

## Files Created/Modified
- `src/metrics/leiden_communities.py` - Leiden partition + communities.csv rollups (spec §6.5 / §7.9)
- `src/metrics/run_metrics.py` - Compute Leiden IDs in metrics.csv and write communities.csv using shared graph
- `tests/test_communities.py` - Unit + integration tests for traffic/density and CSV ID alignment
- `tests/test_hub_bridge_metrics.py` - Adjusted smoke assertions for assigned Leiden IDs and temp outputs

## Decisions Made
- Run Leiden on the full directed graph; isolated nodes become singleton communities.
- Use stable relabeling (sort by smallest airport_id) so `leiden_community_id` is deterministic.
- Serialize `top_*_airport_ids` with `|` delimiter.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `metrics.csv` and `communities.csv` are now synchronized on community IDs, ready for `route_metrics.csv` cross-community flags (§7.10) and Phase 4 Communities page consumption.

---
*Phase: 02-graph-metrics-communities*
*Completed: 2026-04-09*

