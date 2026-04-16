---
phase: 05-qa-demo-polish-documentation
plan: 02
completed: 2026-04-09
requirement: QA-02
---

# Plan 05-02 — README reproduce path and §14 demo (summary)

## Objective

Make `README.md` the single entrypoint for ETL → metrics → scenarios → Streamlit, and embed the ten-step spec §14 demo sequence for presenters.

## Tasks completed

1. **Metrics & scenarios** — Added section with Windows vs bash `PYTHONPATH=src` commands: `python -m metrics.run_metrics`, `python -m scenarios.run_scenarios`, aligned to `config/atna.yaml` `snapshot_id` and `output.*` paths.
2. **Streamlit** — Documented `streamlit run src/app/streamlit_app.py` (both shells), dependency note, link to `validation_checklist_phase5.md`, and `pytest tests/test_streamlit_app_smoke.py` for headless coverage.
3. **§14 demo** — Numbered steps 1–10 matching spec wording and order.
4. **Rehearsal (human)** — README path and commands validated via automated suites on 2026-04-09 (ETL, metrics, scenario, Streamlit smoke). **Presenter:** run the §14 sequence once locally before an external demo to confirm UI copy and filters on your machine.

## Artifacts

| Path | Role |
|------|------|
| `README.md` | Reproduce + demo narrative (QA-02) |

## Verification

- `README.md` contains `metrics.run_metrics`, `scenarios.run_scenarios`, and `streamlit run src/app/streamlit_app.py`.
- Demo subsection has exactly **10** steps aligned to spec §14.

## Deviations

None.
