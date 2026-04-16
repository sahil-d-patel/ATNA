---
phase: 01-repository-data-foundation
plan: 04
subsystem: testing
tags: [python, pandas, pytest, etl, bts, nodes]

requires:
  - phase: 01-repository-data-foundation
    provides: airports.csv and edges.csv ETL (plan 01-03)
provides:
  - nodes.csv derived from edges with §6.3 columns
  - python -m etl.run_pipeline orchestration with optional --config
  - tests/test_etl_contracts.py column and join checks
  - data/reference/validation_notes_mvp.md (DATA-06)
affects:
  - Phase 2 graph metrics (consumes nodes/edges)
  - Future snapshot bumps (same pipeline)

tech-stack:
  added: []
  patterns:
    - "Nodes = edge aggregates: degrees are counts of directed route rows per airport"
    - "Single pipeline entry validates raw paths then builds airports → edges → nodes"

key-files:
  created:
    - src/etl/build_nodes.py
    - src/etl/run_pipeline.py
    - tests/test_etl_contracts.py
    - data/reference/validation_notes_mvp.md
  modified:
    - README.md
    - tests/test_etl_01_03.py

key-decisions:
  - "degree_out/in = number of edges.csv rows where airport is origin/destination (one row per directed route in the monthly aggregate)"
  - "flights_out/in = sum of flight_count on those edges; strength_* = sum of analysis_weight"

patterns-established:
  - "DATA-06 validation notes live in data/reference/ alongside manifests"

duration: 30min
completed: 2026-04-08
---

# Phase 1 Plan 04: Nodes, pipeline, validation — Summary

**§6.3 nodes.csv from edges (traffic + log1p strength sums), `etl.run_pipeline` entrypoint, pytest contracts for joins, and MVP validation notes linked from README**

## Performance

- **Duration:** ~30 min
- **Started:** 2026-04-08 (execution session)
- **Completed:** 2026-04-08
- **Tasks:** 3
- **Files modified:** 7

## Accomplishments

- `build_nodes.py` reads `edges.csv`, aggregates per-airport outbound/inbound flight totals, `analysis_weight` sums, and directed degrees (edge-row counts).
- `run_pipeline.py` loads YAML config, validates raw paths, runs airports → edges → nodes.
- `test_etl_contracts.py` enforces column lists, strength identity, edge endpoints ⊆ airports, and nodes airport set = airports table; `test_etl_01_03` roundtrip extended to `nodes.csv`.
- `validation_notes_mvp.md` documents snapshot `2025-12`, sources, row counts, exclusions, BTS quirks; README links to it and the contract tests.

## Task Commits

1. **Task 1: Build nodes.csv from edges** — `ba7739e` (feat)
2. **Task 2: Pipeline entrypoint and README** — `71f6d92` (feat)
3. **Task 3: Contracts, join QA, DATA-06 notes** — `1a22684` (test)

## Files Created/Modified

- `src/etl/build_nodes.py` — §6.3 table from processed edges
- `src/etl/run_pipeline.py` — CLI orchestration
- `tests/test_etl_contracts.py` — DATA-05 automated checks
- `tests/test_etl_01_03.py` — roundtrip includes nodes
- `data/reference/validation_notes_mvp.md` — DATA-06 dictionary
- `README.md` — ETL command and validation pointers

## Decisions Made

- **Degrees:** Count of rows in `edges.csv` with the airport as `origin_id` (`degree_out`) or `destination_id` (`degree_in`), matching one directed route per row in the monthly aggregate.
- **Flights:** `flights_out` / `flights_in` are sums of `flight_count` on those edges (not distinct-flight deduplication).

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 1 processed outputs (`airports.csv`, `edges.csv`, `nodes.csv`) are reproducible via one command and covered by pytest.
- Ready for Phase 2 graph metrics on top of processed tables.

---
*Phase: 01-repository-data-foundation*  
*Completed: 2026-04-08*
