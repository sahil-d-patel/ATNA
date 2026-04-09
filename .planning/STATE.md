# ATNA — Planning state

## Current position

| Field | Value |
|-------|--------|
| **Phase** | 1 of 5 — Repository & data foundation |
| **Plan** | 01-03 complete; next **01-04** (nodes, pipeline, validation notes) |
| **Status** | In progress — Phase 1 |
| **Last activity** | 2026-04-08 — Completed `01-03-PLAN.md` |

**Progress (Phase 1 plans):** ███░ 3/4 (75%)

## Current milestone

**MVP** — Air Traffic Network Analysis (locked spec v1.0).

## Phase focus

**Phase 1** — Data foundation (see `.planning/ROADMAP.md`).

## Last completed

- 2026-04-08: **`01-03-PLAN.md`** — `load_raw.py`, `build_airports.py`, `build_edges.py`, pytest contracts, §6.1/§6.2 CSVs under `data/processed/{snapshot_id}/`. Summary: `.planning/phases/01-repository-data-foundation/01-03-SUMMARY.md`.

## Decisions (accumulated)

| ID | Decision |
|----|----------|
| REPO-02 | Canonical schema/metrics/UI contract is **`organization/ATNA_MVP_Technical_Spec_and_Workflow.md`** only; see `docs/specs/README.md`. |
| DATA-01 | **`data/raw/`** must not be silently overwritten; use new paths/suffixes for refreshes. |
| CFG-01 | Pipeline paths and MVP **`snapshot_id`** live in **`config/atna.yaml`**; loader resolves paths from repo root via `src/etl/config.py`. |
| DATA-02/03 | **§6.1/§6.2 ETL** uses DOT `*_AIRPORT_ID` joins; **`pct_delayed`** = share with **`ARR_DELAY` > 15** min (non-null delays); **`analysis_weight`** = **`numpy.log1p(flight_count)`**; **`timezone`** from master **`UTC_LOCAL_TIME_VARIATION`**. |

## Blockers

None recorded.

## Notes

- Domain ecosystem research was **skipped** by user choice; rely on locked spec for scope.
- **METR-07** (vulnerability) depends on scenario impact; implementation order may compute vulnerability after SCEN-* or via batch—track during Phase 2/3 integration.

## Next actions

1. Execute **`01-04-PLAN.md`** — `nodes.csv`, pipeline entrypoint, validation notes.

## Session continuity

| Field | Value |
|-------|--------|
| **Last session** | 2026-04-08 |
| **Stopped at** | Completed `01-03-PLAN.md` |
| **Resume file** | None |
