---
phase: 01-repository-data-foundation
plan: "01"
subsystem: data-foundation
tags: [python, pandas, pytest, pyyaml, repo-layout, REPO-01, REPO-02, DATA-01]

requires:
  - phase: project-init
    provides: Locked spec path, ROADMAP, REQUIREMENTS
provides:
  - Spec-aligned directory skeleton (§4.2) with ETL/tests packages and tracked empty dirs
  - Pinned Python deps for pipeline + download scripts
  - README governance: layout, raw immutability, schema contract, download vs ETL
affects:
  - 01-02-config-yaml
  - 01-03-etl-tables
  - 01-04-nodes-validation

tech-stack:
  added: [numpy, pandas, PyYAML, pytest]
  patterns: [Immutable raw policy documented at repo root; single locked spec as REPO-02 contract]

key-files:
  created:
    - src/etl/__init__.py
    - tests/__init__.py
    - data/interim/.gitkeep
    - data/processed/.gitkeep
    - outputs/tables/.gitkeep
    - notebooks/exploration/.gitkeep
    - docs/specs/README.md
  modified:
    - requirements.txt
    - README.md

key-decisions:
  - "REPO-02 contract is stated in README and docs/specs/README.md as organization/ATNA_MVP_Technical_Spec_and_Workflow.md only."
  - "requirements.txt uses minimum compatible pins (numpy/pandas upper bound <3) alongside existing playwright/requests."

patterns-established:
  - "Download scripts populate data/raw/; ETL is a separate step that reads raw and writes interim/processed."

duration: "~15min"
completed: 2026-04-08
---

# Phase 1 Plan 01: Repository skeleton & governance Summary

**Spec §4.2 tree with pinned numpy/pandas/PyYAML/pytest, README-bound REPO-02 schema contract, and documented raw immutability (DATA-01).**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-04-08 (execution session)
- **Completed:** 2026-04-08
- **Tasks:** 3
- **Files modified:** 9 (7 created, 2 updated)

## Accomplishments

- Created `src/etl/`, `tests/`, `data/interim/`, `data/processed/`, `outputs/tables/`, `notebooks/exploration/` with package roots or `.gitkeep` as required.
- Added `docs/specs/README.md` linking the locked MVP spec and stating REPO-02 (no parallel undocumented schemas).
- Extended `requirements.txt` with numpy, pandas, PyYAML, pytest while keeping playwright and requests.
- Rewrote README with §4.2 layout table, raw policy, download vs ETL separation, and preserved BTS download instructions.

## Task Commits

1. **Task 1: Directory skeleton and specs pointer** — `83a460a` (feat)
2. **Task 2: Pin core Python dependencies** — `f82df78` (feat)
3. **Task 3: README governance and layout** — `38f7bd6` (feat)

**Plan metadata:** `docs(1-01): complete repository skeleton plan` (STATE + SUMMARY)

## Files Created/Modified

- `src/etl/__init__.py` — ETL package root
- `tests/__init__.py` — Test package root
- `data/interim/.gitkeep`, `data/processed/.gitkeep` — Track empty pipeline dirs
- `outputs/tables/.gitkeep`, `notebooks/exploration/.gitkeep` — Track outputs and notebooks shells
- `docs/specs/README.md` — Locked spec path and REPO-02 role
- `requirements.txt` — Core + download dependencies
- `README.md` — Layout, governance, raw policy, download vs ETL, existing download docs

## Decisions Made

- Documented schema contract exclusively via `organization/ATNA_MVP_Technical_Spec_and_Workflow.md` and `docs/specs/README.md`, matching REPO-02.
- Raw immutability explained at README top level so it is discoverable without reading scripts.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Repository boundaries and dependency baseline are in place for config (`01-02`) and ETL plans.
- No blockers recorded.

---
*Phase: 01-repository-data-foundation*
*Completed: 2026-04-08*
