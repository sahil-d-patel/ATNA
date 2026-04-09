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
2. **ETL** — Separate Python entrypoints under `src/etl/` (and `python -m` / `scripts/` as documented in later phases) read raw inputs and write interim and processed tables. There is no requirement for a single chained “download + transform” command in Phase 1.

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
