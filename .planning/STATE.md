# ATNA — Planning state

## Current position

| Field | Value |
|-------|--------|
| **Phase** | 4 of 5 — Streamlit application |
| **Plan** | 2 of 5 in phase |
| **Status** | In progress — Phase 4 |
| **Last activity** | 2026-04-09 — Completed `04-02` Streamlit explicit seven-page router and import-safe page scaffolds |

**Progress (all plans with SUMMARY):** 15 of 19 executable plans with summaries — ████████░░ 79%

## Current milestone

**MVP** — Air Traffic Network Analysis (locked spec v1.0).

## Phase focus

**Phase 4** — Streamlit application (see `.planning/ROADMAP.md`).

## Last completed

- 2026-04-09: **`04-02-PLAN.md`** — implemented `src/app/streamlit_app.py` with explicit `st.Page` + `st.navigation` router (APP-01..APP-07) and created seven callable page scaffolds under `src/app/pages/`. Summary: `.planning/phases/04-streamlit-application/04-02-SUMMARY.md`.
- 2026-04-09: **`04-01-PLAN.md`** — implemented `src/app/config.py` (canonical snapshot/artifact resolver), `src/app/data_loader.py` (cached schema-validated loaders), and `src/app/ui/components.py` + `src/app/ui/formatters.py` (empty-state-safe UI primitives). Summary: `.planning/phases/04-streamlit-application/04-01-SUMMARY.md`.
- 2026-04-09: **`03-04-PLAN.md`** — implemented `src/scenarios/vulnerability.py` (deterministic airport-removal batch vulnerability computation), integrated scoring into `src/metrics/run_metrics.py`, and added METR-07 merge-safety/reproducibility coverage in `tests/test_vulnerability_metrics_integration.py`. Summary: `.planning/phases/03-scenario-engine-vulnerability-integration/03-04-SUMMARY.md`.
- 2026-04-09: **`03-03-PLAN.md`** — implemented `src/scenarios/engine.py` (deterministic scenario orchestration and IDs), `src/scenarios/artifacts.py` (schema-ordered CSV writers), `src/scenarios/run_scenarios.py` (deterministic mixed 3-scenario CLI), and `tests/test_scenario_engine_artifacts.py` (contracts + invariants + temp-config batch test). Summary: `.planning/phases/03-scenario-engine-vulnerability-integration/03-03-SUMMARY.md`.
- 2026-04-09: **`03-02-PLAN.md`** — implemented `src/scenarios/ripple.py` (2-hop propagation, lambda discount, route endpoint seeding), `src/scenarios/scoring.py` (locked aggregate formulas + guards), and `tests/test_scenario_ripple_scoring.py` (deterministic invariants). Summary: `.planning/phases/03-scenario-engine-vulnerability-integration/03-02-SUMMARY.md`.
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
| SCEN-02a | Ripple propagation is locked to exactly two hops with **`lambda=0.35`**, using dependency weights **`W(i,j)=w(i,j)+w(j,i)`** and explicit hop provenance metadata. |
| SCEN-03a | Aggregate scenario score cards are locked to spec formulas (`lcc_loss`, `reachability_loss`, `ripple_severity`, `impact_score`, `network_health`) with deterministic denominator/finite-value guards. |
| SCEN-03b | Scenario execution IDs are deterministic (`scn_<sha256-prefix>`) from snapshot, scenario type, and canonical payload JSON to guarantee repeatability. |
| SCEN-04a | METR-07 vulnerability is computed in canonical `run_metrics` using `0.60 * impact_pct + 0.40 * bridge_pct`, with impact from airport-removal scenario batch and one-to-one key merge on (`snapshot_id`, `airport_id`). |
| APP-01a | App layer now has a canonical `AppConfig` contract in `src/app/config.py` resolving `metrics.csv`, `communities.csv`, `route_metrics.csv`, `scenarios.csv`, `scenario_exposure.csv`, plus baseline `edges.csv`/`nodes.csv` from `config/atna.yaml` + `snapshot_id`. |
| APP-01b | Streamlit loaders in `src/app/data_loader.py` must fail fast on unreadable files/missing required columns and enforce `vulnerability_score` presence in `metrics.csv`. |
| APP-01c | Page rendering should use shared helpers in `src/app/ui/components.py` to prevent empty-filter crashes with consistent "No rows for current filters." messaging. |
| APP-02a | Streamlit app routing is explicit in `src/app/streamlit_app.py` via `st.Page` + `st.navigation` with deterministic APP-01..APP-07 order and no implicit page auto-discovery. |
| APP-02b | `src/app/pages/*` now defines one callable `render_*_page()` scaffold per route target so downstream page plans can implement logic incrementally without import churn. |

## Blockers

None recorded.

## Notes

- Domain ecosystem research was **skipped** by user choice; rely on locked spec for scope.
- Phase 3 complete: scenario artifacts and METR-07 vulnerability integration are now locked and test-covered.

## Next actions

1. Execute Phase 4 Plan 03 (`04-03-PLAN.md`) to implement Overview and Methodology pages on top of canonical loaders/helpers.
2. Keep router/page contracts from `04-02` stable while replacing placeholders with artifact-backed page content.

## Session continuity

| Field | Value |
|-------|--------|
| **Last session** | 2026-04-09 05:23Z |
| **Stopped at** | Completed `04-02-PLAN.md` |
| **Resume file** | None |
