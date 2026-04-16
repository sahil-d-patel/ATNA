# MVP validation notes (DATA-06)

Structured QA notes for the **Phase 1** frozen snapshot and ETL outputs. Complements automated checks in `tests/test_etl_contracts.py` and `tests/test_etl_01_03.py`.

## Snapshot

| Field | Value |
|-------|--------|
| **snapshot_id** | `2025-12` (from `config/atna.yaml`) |
| **Spec** | `organization/ATNA_MVP_Technical_Spec_and_Workflow.md` §6.1–§6.3 |

## Source files (raw)

| Role | Path pattern |
|------|----------------|
| On-time performance | `data/raw/on_time/{year}/on_time_{year}_{month}.csv` |
| T-100 segment | `data/raw/t100_segment/{year}/t100_{year}_{month}.csv` |
| Master coordinates | `data/raw/airport_reference/master_coordinate_latest.csv` |

## Processed outputs (representative counts)

Counts below are for the checked-in config month **2025-12** after a successful ETL run. Re-run after changing `snapshot_id` or raw inputs.

| Table | Row count | Notes |
|-------|-----------|--------|
| `airports.csv` | 343 | DOT `AIRPORT_ID` in U.S. domestic MVP slice |
| `edges.csv` | 5827 | Directed routes (aggregated per origin–destination) |
| `nodes.csv` | 343 | One row per airport in the slice |

## Exclusions and filters

- **Cancelled flights** — Excluded from on-time aggregates (`CANCELLED != 0` dropped before route stats).
- **U.S. domestic slice** — Origin and destination must map to `AIRPORT_COUNTRY_CODE_ISO == US` in master (see `data/reference/field_selection_notes.md`).
- **T-100 merge** — Routes present in on-time but missing in T-100 get `passenger_count` / `seat_count` imputed to zero (left merge).

## Join QA

- **Edges ↔ airports** — Every `origin_id` and `destination_id` in `edges.csv` is expected to appear as `airport_id_canonical` in `airports.csv` for the same snapshot (enforced in tests).
- **Nodes** — Derived only from `edges.csv`; airport universe matches `airports.csv` for the MVP slice (enforced in tests).

## Known BTS / TranStats quirks

- **Automation** — TranStats may throttle or challenge automated downloads; use `--headed` or manual download paths documented in the root `README.md` if needed.
- **Master file** — `master_coordinate_latest.csv` is a rolling “latest” extract; version is recorded in `airports.csv` as `source_version`.
- **Monthly ZIPs** — Downloader stores extracted CSV bytes only; ZIPs are not retained by default.

## Related

- Download manifest: `data/reference/download_manifest_2025.md`
- Field checklist: `data/reference/field_selection_notes.md`
