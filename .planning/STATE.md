# ATNA — Planning state

## Current position

| Field | Value |
|-------|--------|
| **Phase** | 2 of 5 — Graph metrics & communities |
| **Plan** | 2 of 6 in phase (`02-02` complete) |
| **Status** | In progress — Phase 2 |
| **Last activity** | 2026-04-09 — Completed `02-02-PLAN.md` (METR-03 centralities) |

**Progress (all plans with SUMMARY):** 5 of 10 executable plans with summaries — █████░░░░░ 50%

## Current milestone

**MVP** — Air Traffic Network Analysis (locked spec v1.0).

## Phase focus

**Phase 2** — Graph metrics & communities (see `.planning/ROADMAP.md`).

## Last completed

- 2026-04-09: **`02-02-PLAN.md`** — `percentile.py`, `centralities.py` (METR-03), `tests/test_centralities.py`. Summary: `.planning/phases/02-graph-metrics-communities/02-02-SUMMARY.md`.
- 2026-04-09: **`02-01-PLAN.md`** — `src/metrics` package, deps, `MetricsConfig`, `graph_builder` (METR-01), `tests/test_metrics_graph.py`. Summary: `.planning/phases/02-graph-metrics-communities/02-01-SUMMARY.md`.

## Decisions (accumulated)

| ID | Decision |
|----|----------|
| REPO-02 | Canonical schema/metrics/UI contract is **`organization/ATNA_MVP_Technical_Spec_and_Workflow.md`** only; see `docs/specs/README.md`. |
| DATA-01 | **`data/raw/`** must not be silently overwritten; use new paths/suffixes for refreshes. |
| CFG-01 | Pipeline paths and MVP **`snapshot_id`** live in **`config/atna.yaml`**; loader resolves paths from repo root via `src/etl/config.py`. |
| DATA-02/03 | **§6.1/§6.2 ETL** uses DOT `*_AIRPORT_ID` joins; **`pct_delayed`** = share with **`ARR_DELAY` > 15** min (non-null delays); **`analysis_weight`** = **`numpy.log1p(flight_count)`**; **`timezone`** from master **`UTC_LOCAL_TIME_VARIATION`**. |
| DATA-04 | **`nodes.csv`** built from **`edges.csv`**: **`flights_*`** = sum of **`flight_count`**; **`strength_*`** = sum of **`analysis_weight`**; **`degree_*`** = counts of edge rows incident as origin/destination (one row per directed route). |
| METR-01a | **`src/metrics/config.py`** resolves **`metrics.csv`**, **`communities.csv`**, **`route_metrics.csv`** under **`data/processed/{snapshot_id}/`** from repo root; graph uses **`analysis_weight`** only on **`DiGraph`** edges. |

## Blockers

None recorded.

## Notes

- Domain ecosystem research was **skipped** by user choice; rely on locked spec for scope.
- **METR-07** (vulnerability) depends on scenario impact; implementation order may compute vulnerability after SCEN-* or via batch—track during Phase 2/3 integration.

## Next actions

1. Execute **`02-03-PLAN.md`** — hub/bridge and partial metrics.csv.
2. Continue Phase 2 plans per roadmap.

## Session continuity

| Field | Value |
|-------|--------|
| **Last session** | 2026-04-09 |
| **Stopped at** | Completed `02-01-PLAN.md` |
| **Resume file** | None |
