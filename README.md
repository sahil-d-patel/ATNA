# ATNA MVP

U.S. domestic airport network analysis — monthly snapshots, **AirportID**-keyed graphs, BTS-sourced raw data.

## Repository layout (spec §4.2)

Top-level boundaries follow the locked MVP technical spec:

| Area | Role |
|------|------|
| `data/` | `raw/` immutable inputs, `interim/` scratch transforms, `processed/` canonical tables, `reference/` manifests and notes |
| `outputs/` | Precomputed artifacts (`figures/`, `tables/`, `scenarios/` as built in later phases) |
| `notebooks/exploration/` | Ad hoc analysis (not the production pipeline) |
| `src/` | Library code (`etl/`, and later `graph/`, `metrics/`, etc. per spec) |
| `docs/specs/` | Pointers to the **locked** specification (see below) |
| `tests/` | Automated checks for contracts and joins |
| `requirements.txt` | Pinned Python dependencies |
| `README.md` | This file |

Scripts that fetch BTS data live under `scripts/download/`; they populate `data/raw/` but are **not** a substitute for ETL: download first, then run transforms that read raw and write interim/processed outputs.

## Schema contract (REPO-02)

Canonical column names, table shapes, metrics definitions, and UI behavior are defined only in the version-controlled **`organization/ATNA_MVP_Technical_Spec_and_Workflow.md`**. A short pointer and rationale live in [`docs/specs/README.md`](docs/specs/README.md). Do not maintain a second, undocumented schema.

## Raw data policy (DATA-01)

- **`data/raw/` is immutable in place.** Do not silently overwrite an existing raw file with a new fetch.
- If you need to refresh data, use a **new path**: e.g. a dated subfolder or a filename suffix so prior bytes remain inspectable for reproducibility and audit.
- The download script writes extracted CSVs to expected paths; treat any re-download as a deliberate replacement only if you have changed paths or explicitly archived the old file.

## Download vs ETL

1. **Download** — Populate `data/raw/` (automated script and/or manual steps per `data/reference/` docs). Provenance is tracked via manifests under `data/reference/`.
2. **ETL** — Python modules under `src/etl/` read raw inputs and write processed tables for the configured snapshot.

### Run the full ETL (airports → edges → nodes)

**Prerequisite:** Raw CSVs exist for the `snapshot_id` in [`config/atna.yaml`](config/atna.yaml) (same layout as the downloader). Use [`scripts/download/verify_downloads.py`](scripts/download/verify_downloads.py) to confirm files before ETL.

From the repository root, with `src` on `PYTHONPATH`:

**Windows (PowerShell):**

```powershell
$env:PYTHONPATH = "src"
python -m etl.run_pipeline
```

**macOS / Linux:**

```bash
PYTHONPATH=src python -m etl.run_pipeline
```

Optional custom config:

```bash
PYTHONPATH=src python -m etl.run_pipeline --config path/to/atna.yaml
```

Outputs: `data/processed/{snapshot_id}/airports.csv`, `edges.csv`, and `nodes.csv` (spec §6.1–§6.3).

**Validation / QA notes** — See [`data/reference/validation_notes_mvp.md`](data/reference/validation_notes_mvp.md) for snapshot metadata, exclusion rules, and known BTS quirks. Automated column and join checks live under `tests/test_etl_contracts.py`.

## Metrics and scenario artifacts

After ETL, `data/processed/{snapshot_id}/` contains `airports.csv`, `edges.csv`, and `nodes.csv`. Build graph metrics and scenario outputs with `snapshot_id` from [`config/atna.yaml`](config/atna.yaml) (paths under `output.*` in that file).

**Windows (PowerShell):**

```powershell
$env:PYTHONPATH = "src"
python -m metrics.run_metrics
python -m scenarios.run_scenarios
```

**macOS / Linux:**

```bash
PYTHONPATH=src python -m metrics.run_metrics
PYTHONPATH=src python -m scenarios.run_scenarios
```

Writes (per config): `metrics.csv`, `communities.csv`, `route_metrics.csv`, `scenarios.csv`, and `scenario_exposure.csv` under `data/processed/{snapshot_id}/`.

## Run the Streamlit app

From the repository root, with dependencies installed (`pip install -r requirements.txt`) and artifacts present for the configured `snapshot_id`:

**Windows (PowerShell):**

```powershell
$env:PYTHONPATH = "src"
streamlit run src/app/streamlit_app.py
```

**macOS / Linux:**

```bash
PYTHONPATH=src streamlit run src/app/streamlit_app.py
```

Headless regression coverage for all seven pages: `pytest tests/test_streamlit_app_smoke.py -q` (uses Streamlit `AppTest`; allow ~60s per run on cold start). Phase 5 checklist and outcomes: [`data/reference/validation_checklist_phase5.md`](data/reference/validation_checklist_phase5.md).

### Demo sequence (spec §14)

Presenter rehearsal order (locked spec **§14 — Recommended final demo sequence**):

1. Open a monthly snapshot (Overview / app default for `snapshot_id`).
2. Show major hubs on the network map.
3. Switch to Airport Explorer and rank by Hub Score.
4. Rank by Bridge Score and explain the difference.
5. Open Communities and show Leiden partitioning.
6. Open Route Explorer and highlight cross-community routes.
7. Remove a major airport in the Scenario Editor.
8. Show ripple spread, impact score, and network health drop.
9. Remove a route and compare the outcome.
10. Close with the structural takeaway.

## Pipeline configuration

Single checked-in YAML drives the MVP snapshot month and resolved paths for raw BTS files and processed outputs:

| Item | Location |
|------|----------|
| Config file | [`config/atna.yaml`](config/atna.yaml) |
| Loader | [`src/etl/config.py`](src/etl/config.py) — `load_config()`, optional `validate_paths()` |

**Bumping the MVP snapshot** — Edit `snapshot_id` in `config/atna.yaml` to the target `YYYY-MM` (must match the month you froze in `data/raw/`). Path templates in that file expand `{year}`, `{month}`, and `{snapshot_id}`; they follow the same layout as [`data/reference/download_manifest_2025.json`](data/reference/download_manifest_2025.json) and the downloader. After changing the month, re-fetch or copy raw CSVs for that month if needed, then confirm files exist before ETL.

**Verify downloads match config** — From the repo root:

```bash
python scripts/download/verify_downloads.py --year 2025
```

Adjust `--year` if your manifest and `snapshot_id` use a different calendar year. The script checks counts and non-empty files; align its year with the raw paths implied by `snapshot_id`.

**Load config in Python** (from repository root, with `src` on the path):

```bash
python -c "import sys; from pathlib import Path; sys.path.insert(0, str(Path('src').resolve())); from etl.config import load_config, validate_paths; c = load_config(); validate_paths(c); print(c.snapshot_id, c.processed_dir)"
```

---

## Data Download

### Prerequisites

- Python 3.10+
- Dependencies: `pip install -r requirements.txt`
- Playwright browser: `python -m playwright install chromium`

### Run the downloader

From the repository root:

```bash
python scripts/download/download_bts_data.py
```

Options:

- `--year 2025` — calendar year (default `2025`)
- `--only {all,on_time,t100,master}` — fetch a subset
- `--headed` — show the Chromium window (default is headless)
- `--pause 3` — seconds between downloads (default `3`)
- `--continue-on-error` — keep going after a failed month (default stops on first failure)

TranStats returns a **ZIP** per request; the script saves the inner CSV to `data/raw/...` using the names in `prompt.md`. Original ZIPs are not kept (only the extracted CSV bytes are written).

### Verify files

```bash
python scripts/download/verify_downloads.py --year 2025
```

Expect **12** on-time files, **12** T-100 segment files, and **one** master coordinate file, all non-empty.

### Layout

- Raw: `data/raw/on_time/2025/`, `data/raw/t100_segment/2025/`, `data/raw/airport_reference/`
- Manifest: `data/reference/download_manifest_2025.md` and `download_manifest_2025.json`
- Logs: `logs/download_*.log`

### If BTS blocks automation

TranStats may throttle or challenge automated sessions. If downloads fail consistently:

1. Run with `--headed` to observe the form.
2. Use the same field checklist in `data/reference/field_selection_notes.md` for a **manual** download from the three TranStats pages listed in `data/reference/README_data_sources.md`.
3. Save ZIPs or CSVs into the paths above (or drop CSVs next to the expected filenames) and re-run `verify_downloads.py`.

For a reproducible manual path, open each DL_SelectFields URL, choose **Geography: All**, **Year** and **Month** (where applicable), select the listed fields, click **Download**, unzip if needed, and rename to `on_time_2025_MM.csv`, `t100_2025_MM.csv`, or `master_coordinate_latest.csv`.

## Documentation

- Locked MVP spec: [`organization/ATNA_MVP_Technical_Spec_and_Workflow.md`](organization/ATNA_MVP_Technical_Spec_and_Workflow.md)
- Spec pointer: [`docs/specs/README.md`](docs/specs/README.md)
- Data rationale: `data/reference/README_data_sources.md`
- Field mapping: `data/reference/field_selection_notes.md`
- Download spec: `prompt.md`
