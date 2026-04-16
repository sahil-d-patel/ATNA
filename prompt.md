# Cursor Prompt: Download and Organize ATNA MVP Data

You are helping build the **ATNA MVP** for **U.S. domestic airport network analysis**.

## Core project constraints
- Scope: **U.S. domestic only**
- Time granularity: **monthly snapshots**
- Primary edge weight: **flight count**
- Use **AirportID** as the canonical airport identifier for joins
- Keep **raw downloads unchanged** and write cleaned outputs separately

The ATNA spec defines the MVP as a monthly directed airport graph and requires processed artifacts like `airports.csv`, `edges.csv`, and `nodes.csv`.

---

## Goal
Create a reproducible data-download workflow that fetches the three BTS datasets needed for the MVP, stores them in a clean folder structure, and writes a data-source manifest.

You should:
1. Create the exact folder structure below.
2. Download all required raw data for **calendar year 2025**.
3. Preserve raw files exactly as downloaded.
4. Document what was downloaded and where.
5. Prefer automation, but if BTS blocks fully scripted download because of its dynamic form, then build a script plus a short README describing the one manual step needed.

---

## Exact data sources to use

### 1) BTS Reporting Carrier On-Time Performance (primary edge source)
Selective download page:
https://www.transtats.bts.gov/DL_SelectFields.aspx?QO_fu146_anzr=b0-gvzr&gnoyr_VQ=FGJ

Use this for:
- origin and destination airport pairs
- monthly route construction
- delay overlays
- cancellations and diversions

Download window:
- Year: **2025**
- Months: **January through December**

Preferred fields:
- Year
- Month
- FlightDate
- Reporting_Airline
- DOT_ID_Reporting_Airline
- OriginAirportID
- Origin
- DestAirportID
- Dest
- CRSDepTime
- DepTime
- DepDelay
- CRSArrTime
- ArrTime
- ArrDelay
- Cancelled
- Diverted
- Distance

Save files as:
- `data/raw/on_time/2025/on_time_2025_01.csv`
- `data/raw/on_time/2025/on_time_2025_02.csv`
- ...
- `data/raw/on_time/2025/on_time_2025_12.csv`

### 2) BTS Master Coordinate (airport reference source)
Selective download page:
https://transtats.bts.gov/DL_SelectFields.aspx?QO_fu146_anzr=N8vn6v10&gnoyr_VQ=FLL

Use this for:
- AirportID
- airport names
- city/state/country
- latitude and longitude
- timezone / UTC offset
- active/closed indicators

Preferred fields:
- AirportSeqID
- AirportID
- Airport
- AirportName
- AirportCityName
- AirportStateName
- AirportStateCode
- AirportCountryName
- AirportCountryCodeISO
- Latitude
- Longitude
- UTCLocalTimeVariation
- AirportIsClosed
- AirportIsLatest

Save file as:
- `data/raw/airport_reference/master_coordinate_latest.csv`

### 3) BTS T-100 Segment (All Carriers) (route enrichment source)
Selective download page:
https://www.transtats.bts.gov/DL_SelectFields.asp?QO_fu146_anzr=&gnoyr_VQ=FMG

Use this for:
- departures performed
- seats
- passengers
- distance
- air time / ramp-to-ramp time

Download window:
- Year: **2025**
- Months: **January through December**

Preferred fields:
- Year
- Month
- OriginAirportID
- Origin
- DestAirportID
- Dest
- DepScheduled
- DepPerformed
- Seats
- Passengers
- Distance
- AirTime
- RampToRamp

Save files as:
- `data/raw/t100_segment/2025/t100_2025_01.csv`
- `data/raw/t100_segment/2025/t100_2025_02.csv`
- ...
- `data/raw/t100_segment/2025/t100_2025_12.csv`

---

## Important BTS note
Use **AirportID** as the canonical airport key everywhere. Do **not** use IATA airport code as the primary join key.

Reason:
- airport codes can change or be reused
- AirportID is the stable identifier intended for multi-year airport analysis

---

## Exact folder structure to create

```text
atna/
├── data/
│   ├── raw/
│   │   ├── on_time/
│   │   │   └── 2025/
│   │   ├── t100_segment/
│   │   │   └── 2025/
│   │   └── airport_reference/
│   ├── interim/
│   │   ├── cleaned_on_time/
│   │   ├── cleaned_t100/
│   │   ├── airport_lookup/
│   │   └── joined_routes/
│   ├── processed/
│   └── reference/
├── scripts/
│   ├── download/
│   └── utils/
├── logs/
├── notebooks/
├── src/
└── README.md
```

Also create:
- `data/reference/README_data_sources.md`
- `data/reference/download_manifest_2025.md`
- `data/reference/field_selection_notes.md`

---

## Download strategy
Because BTS TranStats uses dynamic field-selection forms, do this in order of preference:

### Preferred approach
Write a script that automates the downloads using a browser automation tool such as:
- Playwright
- Selenium

The script should:
1. Open each dataset page.
2. Select the correct year and month.
3. Select the preferred fields listed above.
4. Trigger the CSV download.
5. Rename and move the downloaded file into the correct folder.
6. Repeat for all months in 2025.
7. Log success or failure for each month.

### Fallback approach
If fully automated field selection is unreliable because of BTS form behavior:
1. Create a reusable downloader script that handles file movement, renaming, and verification.
2. Create a short markdown file with exact manual click steps for the user.
3. Keep the workflow reproducible.

Do **not** silently skip months.

---

## What to generate in the repo
Create these files:

### 1) `scripts/download/download_bts_data.py`
A Python script that:
- creates directories
- automates or assists download
- validates that all expected raw files exist
- writes a log file

### 2) `scripts/download/verify_downloads.py`
A Python script that checks:
- all 12 On-Time monthly files exist
- all 12 T-100 monthly files exist
- master coordinate file exists
- files are non-empty
- filenames match convention

### 3) `data/reference/download_manifest_2025.md`
List:
- dataset name
- source URL
- year/month covered
- saved filename
- download status
- notes if any month needed manual intervention

### 4) `data/reference/README_data_sources.md`
Explain:
- why these three datasets were chosen
- what each one is used for
- why AirportID is canonical
- why the scope is U.S. domestic only

### 5) `README.md`
Add a section called **Data Download** with:
- how to run the downloader
- how to verify downloads
- where the files are stored
- what to do if BTS blocks automation

---

## Filtering policy for later processing
Do not fully process the data yet unless needed for verification.
But document the intended rule clearly:
- keep only rows where both `OriginAirportID` and `DestAirportID` are U.S. airports
- derive the U.S. airport set from Master Coordinate using country fields

For later ETL, the intended processed outputs are:
- `airports.csv`
- `edges.csv`
- `nodes.csv`
- `metrics.csv`
- `communities.csv`
- `route_metrics.csv`
- `scenarios.csv`
- `scenario_exposure.csv`

Do not generate those yet unless it helps validate the raw download structure.

---

## Naming rules
Use these exact names:

### On-Time
- `on_time_2025_01.csv`
- `on_time_2025_02.csv`
- ...
- `on_time_2025_12.csv`

### T-100
- `t100_2025_01.csv`
- `t100_2025_02.csv`
- ...
- `t100_2025_12.csv`

### Airport reference
- `master_coordinate_latest.csv`

If BTS downloads files with generic names, rename them automatically.

---

## Quality bar
I want an implementation that is:
- reproducible
- cleanly organized
- explicit about assumptions
- robust to partial failures
- easy for a student team to run

The downloader should fail loudly when something is missing.
Do not pretend a missing month downloaded successfully.

---

## Final deliverable expectation
At the end, I want Cursor to have produced:
1. the folder structure
2. the download scripts
3. the manifest files
4. a clear README
5. as many raw downloads completed as possible
6. a precise note describing any remaining manual step

Use Python for scripts.
Prefer Playwright if browser automation is needed.
Keep the code readable and heavily validated.
