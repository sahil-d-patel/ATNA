---
phase: 04-streamlit-application
plan: 05
subsystem: ui
tags: [streamlit, scenarios, apptest, smoke]

# Dependency graph
requires:
  - phase: 04-streamlit-application
    provides: APP-01..APP-07 pages, loaders, and scenario-facing data paths from 04-01..04-04
provides:
  - APP-06 scenario editor wired to canonical `scenarios.engine.run_scenario`
  - APP-09 resilience covered by Streamlit AppTest smoke suite
  - Human verification checkpoint closed (product walkthrough approved)
affects: [phase-05-qa-demo-polish]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - UI adapter layer (`scenario_service`) keeps formulas in engine only
    - AppTest with explicit run timeouts for artifact-heavy pages

key-files:
  created: []
  modified:
    - src/app/scenario_service.py
    - src/app/pages/scenario_editor.py
    - tests/test_streamlit_app_smoke.py
    - src/app/streamlit_app.py

key-decisions:
  - "Scenario editor submits via `st.form`; execution delegates to `run_ui_scenario` → `run_scenario` with baseline graph from `load_edges` + `build_analysis_graph`."
  - "Smoke tests use `AppTest.run(timeout=60)` so cold CSV loads do not hit the default ~3s script completion limit."
  - "Product layout stays `src/app/pages/*` with local `streamlit run`; no structural split into `services/` for MVP."

patterns-established:
  - "Form-submit-only scenario runs avoid partial rerender side effects."
  - "Page-level AppTest scripts import `render_*_page` directly for deterministic isolation."

# Metrics
duration: checkpoint-closed 2026-04-09
completed: 2026-04-09
---

# Phase 4 Plan 05: Scenario editor, smoke tests, and checkpoint Summary

**Scenario editor runs the canonical engine from the UI; automated AppTest coverage exercises all seven pages plus empty-filter paths; human verification approved for local demo runs.**

## Performance

- **Tasks:** 3 (2 automated + 1 human checkpoint)
- **Files modified:** 4 (including post-checkpoint stability fix for AppTest timeout and `streamlit run` import path)

## Accomplishments

- Implemented `scenario_service.py` adapter: baseline graph, payload normalization, `run_scenario` delegation, sorted exposure table.
- Implemented `scenario_editor.py`: form-based airport/route removal, before/after metric cards, scenario result row, affected-airport table and hop bar chart.
- Added `tests/test_streamlit_app_smoke.py`: seven-page render smoke, empty multiselect resilience, scenario form submit paths.
- Extended `streamlit_app.py` with `sys.path` bootstrap so `python -m streamlit run src/app/streamlit_app.py` resolves the `app` package without relying on pytest-only path injection.
- Human checkpoint: user confirmed full local walkthrough (all pages, both scenario types, narrow filters) — **approved**.

## Task commits

1. **Task 1: Scenario service + editor** — `336588e` (`feat(04-05): implement canonical scenario service and editor flow`)
2. **Task 2: AppTest smoke suite** — `f9935f8` (`test(04-05): add AppTest smoke coverage for all pages`)
3. **Post-checkpoint: test timeout + Streamlit path** — `2a7b74d` (`fix(04-05): stabilize AppTest timeout and streamlit import path`).

## Verification

- `python -m pytest tests/test_streamlit_app_smoke.py -q` — **3 passed** (after timeout adjustment).
- `python -m streamlit run src/app/streamlit_app.py` — local run confirmed by reviewer.

## Deviations

- Default AppTest script timeout was insufficient on cold artifact load; raised to 60s in the smoke helper.

## Follow-ups

- Phase 5: formal QA checklist (QA-01/QA-02), README demo narrative, and any export polish if scoped.
