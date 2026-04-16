---
phase: 01-repository-data-foundation
plan: 02
subsystem: etl
tags: yaml, pyyaml, pathlib, bts, reproducibility

requires:
  - phase: 01-repository-data-foundation
    provides: Repository skeleton, requirements.txt with PyYAML, README layout (01-01)
provides:
  - Single config/atna.yaml with snapshot_id and path templates aligned to download manifest
  - AtnaConfig loader with YYYY-MM validation and optional raw-file validate_paths()
  - README subsection for bumping snapshot and linking verify_downloads.py
affects:
  - 01-03 (ETL builders will import load_config)
  - 01-04 (pipeline entrypoint)

tech-stack:
  added: []
  patterns:
    - "REPO_ROOT from src/etl; paths in YAML relative to repo root"
    - "String templates {year}/{month}/{snapshot_id} expanded in loader"

key-files:
  created:
    - config/atna.yaml
    - src/etl/config.py
  modified:
    - README.md

key-decisions:
  - "MVP snapshot_id set to 2025-12 to match full 2025 manifest and latest complete month in download_manifest_2025.json"
  - "on_time_glob / t100_glob are single-month path templates (not directory wildcards) matching BTS file naming"

patterns-established:
  - "load_config(path=None) returns frozen AtnaConfig with resolved Paths"
  - "validate_paths(cfg) optional gate before ETL"

duration: 15min
completed: 2026-04-08
---

# Phase 1 Plan 02: Pipeline YAML and loader Summary

**Checked-in `config/atna.yaml` with 2025-12 MVP snapshot, `AtnaConfig` loader resolving on-time/T-100/master/processed paths from repo root, and README wiring to `verify_downloads.py`.**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-04-08 (session)
- **Completed:** 2026-04-08
- **Tasks:** 3
- **Files modified:** 3 (1 new config, 1 new module, README)

## Accomplishments

- `config/atna.yaml` pins `snapshot_id: "2025-12"` and templates aligned to `data/reference/download_manifest_2025.json` and `data/raw/` layout (`on_time`, `t100_segment`, `airport_reference`).
- `src/etl/config.py` exposes `load_config()`, `validate_paths()`, and `AtnaConfig` with resolved `Path`s; `snapshot_id` validated with `^\d{4}-\d{2}$`.
- README documents where config lives, how to bump the snapshot, and links `scripts/download/verify_downloads.py` with a copy-paste import smoke command.

## Task Commits

1. **Task 1: Define config/atna.yaml** — `fa3ad74` (feat)
2. **Task 2: Config loader module** — `5d68c6a` (feat)
3. **Task 3: Document configuration in README** — `8480d53` (feat)

**Plan metadata:** `docs(1-02): complete config and loader plan` (SUMMARY + STATE)

## Files Created/Modified

- `config/atna.yaml` — `snapshot_id`, `raw.*` templates, `output.processed_dir`
- `src/etl/config.py` — `REPO_ROOT`, `load_config`, `validate_paths`, `AtnaConfig`
- `README.md` — Pipeline configuration subsection

## Decisions Made

- Use **2025-12** as the canonical MVP month in YAML to align with a complete 2025 raw year in the manifest and the “most recent complete month at freeze” intent.
- Resolve YAML-relative paths against **`Path(__file__).resolve().parents[2]`** so behavior matches existing download scripts regardless of the working directory.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- ETL tasks (01-03) can import `load_config` and `validate_paths` before reading CSVs.
- Raw data present under `data/raw/` for verification; `data/processed/2025-12/` is created when ETL writes outputs.

---
*Phase: 01-repository-data-foundation*
*Completed: 2026-04-08*
