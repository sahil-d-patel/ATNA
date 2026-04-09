# ATNA MVP — raw data sources

This project builds a **monthly U.S. domestic airport network** for analysis. Raw inputs are published by the Bureau of Transportation Statistics (BTS) via TranStats.

## Datasets in use

### 1. Reporting Carrier On-Time Performance

- **Page:** [DL_SelectFields — On-Time (FGJ)](https://www.transtats.bts.gov/DL_SelectFields.aspx?QO_fu146_anzr=b0-gvzr&gnoyr_VQ=FGJ)
- **Role:** Primary edge table — origin/destination pairs by month, cancellations, diversions, delay fields, and distance for domestic reporting-carrier flights.
- **Saved:** `data/raw/on_time/2025/on_time_2025_MM.csv` (one file per month).

### 2. Master Coordinate (airport reference)

- **Page:** [DL_SelectFields — Master Coordinate (FLL)](https://transtats.bts.gov/DL_SelectFields.aspx?QO_fu146_anzr=N8vn6v10&gnoyr_VQ=FLL)
- **Role:** Canonical airport attributes — **AirportID**, names, city/state/country, lat/long, UTC offset, and active/closed flags.
- **Saved:** `data/raw/airport_reference/master_coordinate_latest.csv`

### 3. T-100 Segment (All Carriers)

- **Page:** [DL_SelectFields — T-100 Segment (FMG)](https://www.transtats.bts.gov/DL_SelectFields.asp?QO_fu146_anzr=&gnoyr_VQ=FMG)
- **Role:** Route-level enrichment — scheduled vs performed departures, seats, passengers, distance, air time, ramp-to-ramp time.
- **Saved:** `data/raw/t100_segment/2025/t100_2025_MM.csv` (one file per month).

## Why AirportID is canonical

IATA codes can be reused or change over time. BTS **AirportID** (and **AirportSeqID** where needed) is the stable key intended for multi-year joins. Use IATA (`ORIGIN` / `DEST`) as a display attribute, not the primary join key.

## U.S. domestic scope

MVP processing will **retain only flights where both endpoints are U.S. airports**, using country fields from Master Coordinate to define the U.S. airport universe. Raw files may include non-U.S. endpoints; filtering is an ETL step, not applied at download time.

## Manifests and field notes

- `download_manifest_2025.md` — per-file download status for the 2025 pull.
- `download_manifest_2025.json` — machine-readable counterpart.
- `field_selection_notes.md` — mapping from TranStats checkbox names to spec column names.
