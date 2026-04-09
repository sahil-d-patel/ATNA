# ATNA — Planning state

## Current position

| Field | Value |
|-------|--------|
| **Phase** | 2 of 5 — Graph metrics & communities |
| **Plan** | — (not started) |
| **Status** | Phase 1 verified — Phase 2 next |
| **Last activity** | 2026-04-09 — `/gsd-execute-phase 1` complete; verifier **passed** (`01-VERIFICATION.md`) |

**Progress (Phase 1 plans):** Complete — verified (`01-VERIFICATION.md`).

## Current milestone

**MVP** — Air Traffic Network Analysis (locked spec v1.0).

## Phase focus

**Phase 2** — Graph metrics & communities (see `.planning/ROADMAP.md`).

## Last completed

- 2026-04-09: **Phase 1** — All four plans executed; goal verified in `.planning/phases/01-repository-data-foundation/01-VERIFICATION.md` (status: passed).
- 2026-04-08: **`01-04-PLAN.md`** — `build_nodes.py`, `run_pipeline.py`, `test_etl_contracts.py`, `validation_notes_mvp.md`, README ETL + validation links. Summary: `.planning/phases/01-repository-data-foundation/01-04-SUMMARY.md`.

## Decisions (accumulated)

| ID | Decision |
|----|----------|
| REPO-02 | Canonical schema/metrics/UI contract is **`organization/ATNA_MVP_Technical_Spec_and_Workflow.md`** only; see `docs/specs/README.md`. |
| DATA-01 | **`data/raw/`** must not be silently overwritten; use new paths/suffixes for refreshes. |
| CFG-01 | Pipeline paths and MVP **`snapshot_id`** live in **`config/atna.yaml`**; loader resolves paths from repo root via `src/etl/config.py`. |
| DATA-02/03 | **§6.1/§6.2 ETL** uses DOT `*_AIRPORT_ID` joins; **`pct_delayed`** = share with **`ARR_DELAY` > 15** min (non-null delays); **`analysis_weight`** = **`numpy.log1p(flight_count)`**; **`timezone`** from master **`UTC_LOCAL_TIME_VARIATION`**. |
| DATA-04 | **`nodes.csv`** built from **`edges.csv`**: **`flights_*`** = sum of **`flight_count`**; **`strength_*`** = sum of **`analysis_weight`**; **`degree_*`** = counts of edge rows incident as origin/destination (one row per directed route). |

## Blockers

None recorded.

## Notes

- Domain ecosystem research was **skipped** by user choice; rely on locked spec for scope.
- **METR-07** (vulnerability) depends on scenario impact; implementation order may compute vulnerability after SCEN-* or via batch—track during Phase 2/3 integration.

## Next actions

1. `/gsd-discuss-phase 2` — graph metrics & communities (context and approach).
2. `/gsd-plan-phase 2` — executable plans when ready.

## Session continuity

| Field | Value |
|-------|--------|
| **Last session** | 2026-04-09 |
| **Stopped at** | Phase 1 verified; roadmap/state updated for Phase 2 |
| **Resume file** | None |
