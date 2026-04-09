---
phase: 01-repository-data-foundation
plan: 03
subsystem: etl
tags: [pandas, numpy, pytest, BTS, yaml, DATA-02, DATA-03]

requires:
  - phase: 01-repository-data-foundation
    provides: config loader (01-02), raw layout and manifests
provides:
  - load_raw.py with snapshot-filtered master, on-time, T-100 and U.S. domestic helpers
  - build_airports.py and build_edges.py writing §6.1 / §6.2 CSVs under data/processed/{snapshot_id}/
  - pytest contract tests for loaders and column contracts
affects:
  - 01-04 (nodes.csv, pipeline entrypoint)
  - Phase 2 graph metrics (consumes airports/edges)

tech-stack:
  added: []
  patterns:
    - "Config-driven paths via AtnaConfig; PYTHONPATH=src + pytest.ini for imports"
    - "Join graph keys on DOT ORIGIN_AIRPORT_ID/DEST_AIRPORT_ID; master for country filter"

key-files:
  created:
    - src/etl/load_raw.py
    - src/etl/build_airports.py
    - src/etl/build_edges.py
    - pytest.ini
    - tests/test_etl_01_03.py
  modified:
    - src/etl/__init__.py

key-decisions:
  - "pct_delayed uses ARR_DELAY > 15 minutes (BTS-style on-time threshold) among flights with non-null ARR_DELAY"
  - "timezone maps from master UTC_LOCAL_TIME_VARIATION (numeric offset as stored by BTS)"
  - "Generated airports.csv/edges.csv are produced locally under data/processed/{snapshot_id}/ (not committed as binary artifacts)"

patterns-established:
  - "analysis_weight = numpy.log1p(flight_count); route_key = origin__dest__YYYY-MM"

duration: 25min
completed: 2026-04-08
---

# Phase 1 Plan 3: ETL airports and edges Summary

**Config-driven pandas ETL from BTS master, on-time, and T-100 CSVs to spec §6.1 `airports.csv` and §6.2 `edges.csv`, with pytest column contracts and log1p edge weights.**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-04-08T00:00:00Z (approx.)
- **Completed:** 2026-04-08T00:25:00Z (approx.)
- **Tasks:** 3
- **Files modified/created:** 6

## Accomplishments

- Raw loaders with Int64 IDs, YEAR/MONTH snapshot filter, and U.S.–U.S. legs via master `AIRPORT_COUNTRY_CODE_ISO == US`
- `airports.csv` with one row per airport in the MVP slice (IDs from filtered on-time), §6.1 column order
- `edges.csv` from non-cancelled on-time aggregates merged with T-100 passenger/seat sums; `analysis_weight = log1p(flight_count)`; `route_key` per spec
- `pytest.ini` and `tests/test_etl_01_03.py` verifying non-empty loads, uniqueness, weights, and route_key pattern

## Task Commits

Each task was committed atomically:

1. **Task 1: Raw loaders filtered to snapshot** — `6adddbd` (feat)
2. **Task 2: Build airports.csv** — `7284b73` (feat)
3. **Task 3: Build edges.csv and ETL tests** — `9305b36` (feat)

**Plan metadata:** committed with `STATE.md` as `docs(1-03): complete ETL airports/edges plan`.

## Files Created/Modified

- `src/etl/load_raw.py` — Read/filter master, on-time, T-100; U.S. domestic masks; `assert_raw_files_exist`
- `src/etl/build_airports.py` — §6.1 table and `build_airports` writer
- `src/etl/build_edges.py` — Route aggregation, T-100 merge, §6.2 writer
- `pytest.ini` — `pythonpath = src`, `testpaths = tests`
- `tests/test_etl_01_03.py` — Loader sanity, airports uniqueness, edges weights/route_key, temp CSV roundtrip
- `src/etl/__init__.py` — Public exports for pipeline use

## Decisions Made

- **Delayed flights:** `pct_delayed` = share of flights with non-null `ARR_DELAY` strictly greater than 15 minutes (industry on-time definition).
- **Timezone:** Use master `UTC_LOCAL_TIME_VARIATION` as the `timezone` column (may be numeric minutes offset in source data).
- **Processed artifacts:** CSV outputs are written to `data/processed/{snapshot_id}/` when the pipeline runs; they are not required to be version-controlled (large, reproducible from raw + config).

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - raw files for `snapshot_id: 2025-12` were present; `pytest tests/test_etl_01_03.py` passed (5 tests, ~16s).

## User Setup Required

None - no external service configuration required. Run ETL with `PYTHONPATH=src` (or `pytest` / IDE using `pytest.ini`).

## Next Phase Readiness

- Ready for **01-04**: `nodes.csv`, pipeline entrypoint, broader validation notes (DATA-04–DATA-06).
- **Note:** Ensure README documents the `PYTHONPATH=src` convention for one-off `python -c` runs if not already covered.

---
*Phase: 01-repository-data-foundation*  
*Completed: 2026-04-08*
