# Phase 5 — Research notes (QA, demo polish, documentation)

## RESEARCH COMPLETE

### Spec anchors

- **§13 Validation Checklist** (`organization/ATNA_MVP_Technical_Spec_and_Workflow.md`): four themes — data (13.1), metrics (13.2), scenario (13.3), UI (13.4). Each theme is a short bullet list suitable for a pass/fail/notes matrix, not a new feature spec.
- **§14 Demo Workflow**: ten-step narrative (snapshot → map → hub/bridge → communities → routes → scenario removals → takeaway). Execution plan should treat this as a rehearsal script the README points to.

### Requirements mapping

| REQ-ID | Intent |
|--------|--------|
| QA-01 | Execute §13 themes with recorded outcomes or tracked fixes. |
| QA-02 | Stable demo path + README documents full reproduce path including app launch. |

### Existing evidence in repo (reuse, do not duplicate logic)

- **Data (13.1):** `data/reference/validation_notes_mvp.md`, `tests/test_etl_contracts.py`, `tests/test_etl_01_03.py`, download verify script.
- **Metrics (13.2):** `data/reference/validation_notes_phase2.md`, `outputs/maps/phase2_*`, metric tests under `tests/test_*metrics*.py`, `tests/test_communities.py`, etc.
- **Scenario (13.3):** `tests/test_scenario_ripple_scoring.py`, `tests/test_scenario_engine_artifacts.py`, `tests/test_vulnerability_metrics_integration.py`.
- **UI (13.4):** `tests/test_streamlit_app_smoke.py`, `.planning/phases/04-streamlit-application/04-VERIFICATION.md`.

### README gap (QA-02)

Current `README.md` documents ETL and download well but does **not** document:

- Metrics pipeline entrypoint: `PYTHONPATH=src python -m metrics.run_metrics` (after processed edges/nodes exist).
- Demo scenario batch: `PYTHONPATH=src python -m scenarios.run_scenarios`.
- App launch: `streamlit run src/app/streamlit_app.py` (entrypoint already adjusts `sys.path`).

### Recommended deliverables shape

1. **Single consolidated checklist file** under `data/reference/` (alongside other validation notes) mapping §13 bullets → outcome → evidence pointer (test name, path, or “manual / date / operator”). Keeps QA artifacts next to existing validation culture.
2. **README section** “Build metrics & scenarios & run the app” with Windows + Unix snippets matching `config/atna.yaml`’s `snapshot_id`, plus a short §14 demo subsection (numbered list mirroring spec).

### Deployment / layout (for execution)

- MVP remains **local** `streamlit run`; no hosting requirement in v1 (`REQUIREMENTS.md` v2 defers hosting). Plans should not introduce deployment scaffolding unless scope changes.

### Risks

- **Subjective rows (13.2):** “intuitive” hubs / spatial communities — plan must require explicit human sign-off text in the checklist, not only automation.
- **Scenario UI (13.3 / 13.4):** engine invariants are tested; UI still needs manual confirmation that before/after cards and ripple view match expectations for at least one demo scenario.
