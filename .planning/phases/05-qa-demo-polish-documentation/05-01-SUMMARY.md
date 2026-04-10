---
phase: 05-qa-demo-polish-documentation
plan: 01
completed: 2026-04-09
requirement: QA-01
---

# Plan 05-01 — Spec §13 validation checklist (summary)

## Objective

Deliver a single durable checklist under `data/reference/` mapping spec §13.1–§13.4 to outcomes, evidence, and notes (including §16.7-style separation of defects vs scope / manual items).

## Tasks completed

1. **Scaffold** — `data/reference/validation_checklist_phase5.md` with header (`snapshot_id`), four subsections, and one row per spec bullet.
2. **§13.1 Data** — Linked to `validation_notes_mvp.md`, `tests/test_etl_contracts.py`, `tests/test_etl_01_03.py`, `verify_downloads.py`; ran `pytest tests/test_etl_contracts.py tests/test_etl_01_03.py -q` → 10 passed.
3. **§13.2 Metrics** — Ran metrics/community/route pytest bundle (18 passed, ~224s); hub/bridge distinction via `test_hub_bridge_metrics.py`; human rows for intuitive hubs and spatial communities with pointers to phase-2 map and notes.
4. **§13.3 Scenario** — Ran `pytest tests/test_scenario_ripple_scoring.py tests/test_scenario_engine_artifacts.py tests/test_vulnerability_metrics_integration.py -q` → 11 passed; cited `test_scenario_graph_edits.py` (3 passed) for removal/path validity.
5. **§13.4 UI** — Ran `pytest tests/test_streamlit_app_smoke.py -q` → 3 passed; methodology spot-check vs `src/app/pages/methodology.py` and Phase 4 verification doc.

## Artifacts

| Path | Role |
|------|------|
| `data/reference/validation_checklist_phase5.md` | Canonical §13 matrix (QA-01) |

## Verification commands (recorded in checklist)

- ETL: `pytest tests/test_etl_contracts.py tests/test_etl_01_03.py -q`
- Metrics: `pytest tests/test_metrics_graph.py tests/test_centralities.py tests/test_hub_bridge_metrics.py tests/test_communities.py tests/test_route_metrics.py -q`
- Scenarios: `pytest tests/test_scenario_ripple_scoring.py tests/test_scenario_engine_artifacts.py tests/test_vulnerability_metrics_integration.py -q`
- UI smoke: `pytest tests/test_streamlit_app_smoke.py -q`

## Deviations

None. No product code changes required for failing §13 items.
