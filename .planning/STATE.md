# ATNA — Planning state

## Current position

| Field | Value |
|-------|--------|
| **Phase** | 3 of 5 — Scenario engine & vulnerability integration |
| **Plan** | 1 of 4 in phase (`03-01` complete) |
| **Status** | In progress — Phase 3 |
| **Last activity** | 2026-04-09 — Completed `03-01` scenario foundations (config contracts + immutable edits + tests) |

**Progress (all plans with SUMMARY):** 10 of 14 executable plans with summaries — ███████░░░ 71%

## Current milestone

**MVP** — Air Traffic Network Analysis (locked spec v1.0).

## Phase focus

**Phase 3** — Scenario engine & vulnerability integration (see `.planning/ROADMAP.md`).

## Last completed

- 2026-04-09: **`03-01-PLAN.md`** — scenario config contracts, typed scenario models, immutable `remove_airport`/`remove_route`, and contract tests. Summary: `.planning/phases/03-scenario-engine-vulnerability-integration/03-01-SUMMARY.md`.
- 2026-04-09: **`02-06-PLAN.md`** — community map smoke script + `validation_notes_phase2.md`; outputs in `outputs/maps/` including map, legend, and validation metrics JSON. Summary: `.planning/phases/02-graph-metrics-communities/02-06-SUMMARY.md` (checkpoint approved).
- 2026-04-09: **`02-05-PLAN.md`** — `route_criticality.py`, `tests/test_route_metrics.py`, route_metrics written by `run_metrics.py`. Summary: `.planning/phases/02-graph-metrics-communities/02-05-SUMMARY.md`.
- 2026-04-09: **`02-04-PLAN.md`** — `leiden_communities.py` (METR-05), `run_metrics.py`, `tests/test_communities.py` + `tests/test_hub_bridge_metrics.py` (communities.csv + id alignment). Summary: `.planning/phases/02-graph-metrics-communities/02-04-SUMMARY.md`.
- 2026-04-09: **`02-03-PLAN.md`** — `hub_bridge.py` (METR-04), `tables.py` (METR-02 QA), `run_metrics.py` + `tests/test_hub_bridge_metrics.py` (metrics.csv baseline). Summary: `.planning/phases/02-graph-metrics-communities/02-03-SUMMARY.md`.
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
| SCEN-01a | Scenario artifacts are canonical under **`data/processed/{snapshot_id}/`** via **`output.scenarios_csv`** and **`output.scenario_exposure_csv`** in `config/atna.yaml`. |
| SCEN-01b | Scenario graph edits use immutable primitives (`remove_airport`, `remove_route`) over copied **`nx.DiGraph`** with explicit validation failures for invalid payload/targets. |

## Blockers

None recorded.

## Notes

- Domain ecosystem research was **skipped** by user choice; rely on locked spec for scope.
- **METR-07** (vulnerability) depends on scenario impact; implementation order may compute vulnerability after SCEN-* or via batch—track during Phase 3 execution.

## Next actions

1. Execute `03-02-PLAN.md` (ripple propagation + scoring formulas).
2. Preserve scenario artifact path and immutability contracts from `03-01`.

## Session continuity

| Field | Value |
|-------|--------|
| **Last session** | 2026-04-09 |
| **Stopped at** | Completed `03-01-PLAN.md` |
| **Resume file** | None |
