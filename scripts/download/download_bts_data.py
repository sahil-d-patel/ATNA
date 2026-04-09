"""
Download BTS TranStats raw CSVs for ATNA MVP (calendar year 2025).

Uses Playwright to drive DL_SelectFields pages, saves ZIPs from BTS as-downloaded,
extracts the inner CSV, and writes renamed files under data/raw/.

Run from repo root:
  python scripts/download/download_bts_data.py
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import time
import zipfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

REPO_ROOT = Path(__file__).resolve().parents[2]
LOG_DIR = REPO_ROOT / "logs"
RAW = REPO_ROOT / "data" / "raw"
REF = REPO_ROOT / "data" / "reference"
MANIFEST_PATH = REF / "download_manifest_2025.json"

ON_TIME_URL = "https://www.transtats.bts.gov/DL_SelectFields.aspx?QO_fu146_anzr=b0-gvzr&gnoyr_VQ=FGJ"
MASTER_URL = "https://transtats.bts.gov/DL_SelectFields.aspx?QO_fu146_anzr=N8vn6v10&gnoyr_VQ=FLL"
T100_URL = "https://www.transtats.bts.gov/DL_SelectFields.asp?QO_fu146_anzr=&gnoyr_VQ=FMG"

# Checkbox `name` / `id` on DL_SelectFields (see BTS form)
ON_TIME_FIELDS = [
    "YEAR",
    "MONTH",
    "FL_DATE",
    "OP_UNIQUE_CARRIER",
    "OP_CARRIER_AIRLINE_ID",
    "ORIGIN_AIRPORT_ID",
    "ORIGIN",
    "DEST_AIRPORT_ID",
    "DEST",
    "CRS_DEP_TIME",
    "DEP_TIME",
    "DEP_DELAY",
    "CRS_ARR_TIME",
    "ARR_TIME",
    "ARR_DELAY",
    "CANCELLED",
    "DIVERTED",
    "DISTANCE",
]

MASTER_FIELDS = [
    "AIRPORT_SEQ_ID",
    "AIRPORT_ID",
    "AIRPORT",
    "DISPLAY_AIRPORT_NAME",
    "DISPLAY_AIRPORT_CITY_NAME_FULL",
    "AIRPORT_STATE_NAME",
    "AIRPORT_STATE_CODE",
    "AIRPORT_COUNTRY_NAME",
    "AIRPORT_COUNTRY_CODE_ISO",
    "LATITUDE",
    "LONGITUDE",
    "UTC_LOCAL_TIME_VARIATION",
    "AIRPORT_IS_CLOSED",
    "AIRPORT_IS_LATEST",
]

T100_FIELDS = [
    "YEAR",
    "MONTH",
    "ORIGIN_AIRPORT_ID",
    "ORIGIN",
    "DEST_AIRPORT_ID",
    "DEST",
    "DEPARTURES_SCHEDULED",
    "DEPARTURES_PERFORMED",
    "SEATS",
    "PASSENGERS",
    "DISTANCE",
    "AIR_TIME",
    "RAMP_TO_RAMP",
]


@dataclass
class DownloadRecord:
    dataset: str
    source_url: str
    year: str | None
    month: str | None
    target_path: str
    status: str
    notes: str = ""
    saved_bytes: int | None = None


@dataclass
class RunManifest:
    started_at: str
    finished_at: str | None = None
    records: list[DownloadRecord] = field(default_factory=list)

    def add(self, r: DownloadRecord) -> None:
        self.records.append(r)

    def to_json(self) -> dict:
        return {
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "records": [
                {
                    "dataset": r.dataset,
                    "source_url": r.source_url,
                    "year": r.year,
                    "month": r.month,
                    "target_path": r.target_path,
                    "status": r.status,
                    "notes": r.notes,
                    "saved_bytes": r.saved_bytes,
                }
                for r in self.records
            ],
        }


def setup_logging() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOG_DIR / f"download_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[logging.FileHandler(log_path, encoding="utf-8"), logging.StreamHandler(sys.stdout)],
    )
    logging.info("Log file: %s", log_path)


def ensure_dirs() -> None:
    for p in (
        RAW / "on_time" / "2025",
        RAW / "t100_segment" / "2025",
        RAW / "airport_reference",
        REF,
        LOG_DIR,
    ):
        p.mkdir(parents=True, exist_ok=True)


def check_field_boxes(page, names: list[str], dataset: str) -> None:
    page.locator("#chkAllVars").uncheck()
    missing: list[str] = []
    for name in names:
        loc = page.locator(f"#{name}")
        if loc.count() == 0:
            missing.append(name)
            continue
        loc.check()
    if missing:
        raise RuntimeError(f"{dataset}: missing checkboxes: {missing}")


def set_geo_year_month(page, year: str, month: str | None) -> None:
    page.locator("#cboGeography").select_option("All")
    page.locator("#cboYear").select_option(year)
    if month is not None:
        page.locator("#cboPeriod").select_option(month)


def download_zip_to_path(page, dest_zip: Path, timeout_ms: int = 300_000) -> None:
    # Form POST may navigate; do not wait for navigation or click() times out before the download event.
    with page.expect_download(timeout=timeout_ms) as dl_info:
        page.locator("#btnDownload").click(no_wait_after=True)
    dl_info.value.save_as(str(dest_zip))


def extract_single_csv_from_zip(zip_path: Path) -> bytes:
    with zipfile.ZipFile(zip_path) as z:
        names = [n for n in z.namelist() if n.lower().endswith(".csv")]
        if len(names) != 1:
            raise RuntimeError(f"Expected exactly one CSV in {zip_path}, got {names}")
        return z.read(names[0])


def run_on_time_month(page, year: str, month: int, pause_s: float, manifest: RunManifest) -> None:
    mm = f"{month:02d}"
    target = RAW / "on_time" / year / f"on_time_{year}_{mm}.csv"
    url = ON_TIME_URL
    rec = DownloadRecord(
        dataset="on_time_reporting",
        source_url=url,
        year=year,
        month=mm,
        target_path=str(target.relative_to(REPO_ROOT).as_posix()),
        status="pending",
    )
    staging = target.with_suffix(".zip.download")
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=120_000)
        check_field_boxes(page, ON_TIME_FIELDS, "on_time")
        set_geo_year_month(page, year, str(month))
        download_zip_to_path(page, staging)
        csv_bytes = extract_single_csv_from_zip(staging)
        target.write_bytes(csv_bytes)
        rec.status = "ok"
        rec.saved_bytes = len(csv_bytes)
        logging.info("on_time %s-%s -> %s (%s bytes)", year, mm, target.name, rec.saved_bytes)
    except Exception as e:
        rec.status = "failed"
        rec.notes = str(e)
        logging.exception("on_time %s-%s failed", year, mm)
        raise
    finally:
        staging.unlink(missing_ok=True)
        manifest.add(rec)
        time.sleep(pause_s)


def run_t100_month(page, year: str, month: int, pause_s: float, manifest: RunManifest) -> None:
    mm = f"{month:02d}"
    target = RAW / "t100_segment" / year / f"t100_{year}_{mm}.csv"
    url = T100_URL
    rec = DownloadRecord(
        dataset="t100_segment",
        source_url=url,
        year=year,
        month=mm,
        target_path=str(target.relative_to(REPO_ROOT).as_posix()),
        status="pending",
    )
    staging = target.with_suffix(".zip.download")
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=120_000)
        check_field_boxes(page, T100_FIELDS, "t100")
        set_geo_year_month(page, year, str(month))
        download_zip_to_path(page, staging)
        csv_bytes = extract_single_csv_from_zip(staging)
        target.write_bytes(csv_bytes)
        rec.status = "ok"
        rec.saved_bytes = len(csv_bytes)
        logging.info("t100 %s-%s -> %s (%s bytes)", year, mm, target.name, rec.saved_bytes)
    except Exception as e:
        rec.status = "failed"
        rec.notes = str(e)
        logging.exception("t100 %s-%s failed", year, mm)
        raise
    finally:
        staging.unlink(missing_ok=True)
        manifest.add(rec)
        time.sleep(pause_s)


def run_master(page, pause_s: float, manifest: RunManifest) -> None:
    target = RAW / "airport_reference" / "master_coordinate_latest.csv"
    url = MASTER_URL
    rec = DownloadRecord(
        dataset="master_coordinate",
        source_url=url,
        year=None,
        month=None,
        target_path=str(target.relative_to(REPO_ROOT).as_posix()),
        status="pending",
    )
    staging = target.with_suffix(".zip.download")
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=120_000)
        check_field_boxes(page, MASTER_FIELDS, "master_coordinate")
        # Master Coordinate has no time filters (year/period are N/A).
        download_zip_to_path(page, staging)
        csv_bytes = extract_single_csv_from_zip(staging)
        target.write_bytes(csv_bytes)
        rec.status = "ok"
        rec.saved_bytes = len(csv_bytes)
        logging.info("master_coordinate -> %s (%s bytes)", target.name, rec.saved_bytes)
    except Exception as e:
        rec.status = "failed"
        rec.notes = str(e)
        logging.exception("master_coordinate failed")
        raise
    finally:
        staging.unlink(missing_ok=True)
        manifest.add(rec)
        time.sleep(pause_s)


def validate_expected_files(year: str) -> list[str]:
    errors: list[str] = []
    for m in range(1, 13):
        mm = f"{m:02d}"
        ot = RAW / "on_time" / year / f"on_time_{year}_{mm}.csv"
        t1 = RAW / "t100_segment" / year / f"t100_{year}_{mm}.csv"
        for p in (ot, t1):
            if not p.is_file() or p.stat().st_size == 0:
                errors.append(f"missing or empty: {p.relative_to(REPO_ROOT)}")
    mc = RAW / "airport_reference" / "master_coordinate_latest.csv"
    if not mc.is_file() or mc.stat().st_size == 0:
        errors.append(f"missing or empty: {mc.relative_to(REPO_ROOT)}")
    return errors


def write_markdown_manifest(manifest: RunManifest) -> None:
    lines = [
        "# Download manifest — 2025",
        "",
        f"- Run started (UTC): `{manifest.started_at}`",
        f"- Run finished (UTC): `{manifest.finished_at or 'incomplete'}`",
        "",
        "| Dataset | Source URL | Year | Month | Saved path | Status | Bytes | Notes |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for r in manifest.records:
        url = r.source_url.replace("|", "%7C")
        lines.append(
            f"| {r.dataset} | {url} | {r.year or ''} | {r.month or ''} | `{r.target_path}` | {r.status} | "
            f"{r.saved_bytes if r.saved_bytes is not None else ''} | {r.notes.replace('|', '/')} |"
        )
    lines.append("")
    lines.append("Machine-readable: `data/reference/download_manifest_2025.json`")
    (REF / "download_manifest_2025.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    MANIFEST_PATH.write_text(json.dumps(manifest.to_json(), indent=2), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Download BTS raw datasets for ATNA MVP.")
    p.add_argument("--year", default="2025", help="Calendar year (default 2025)")
    p.add_argument(
        "--only",
        choices=("all", "on_time", "t100", "master"),
        default="all",
        help="Which dataset(s) to fetch",
    )
    p.add_argument("--headless", action="store_true", default=True, help="Run browser headless (default)")
    p.add_argument("--headed", action="store_true", help="Show browser window")
    p.add_argument("--pause", type=float, default=3.0, help="Seconds between downloads")
    p.add_argument(
        "--continue-on-error",
        action="store_true",
        help="Continue after a failed month (default: stop on first failure)",
    )
    return p.parse_args()


def main() -> int:
    args = parse_args()
    year = args.year
    headless = not args.headed
    setup_logging()
    ensure_dirs()

    started = datetime.now(timezone.utc).isoformat()
    manifest = RunManifest(started_at=started)

    months = list(range(1, 13))
    failed: list[str] = []

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=headless)
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()

        try:
            if args.only in ("all", "master"):
                try:
                    run_master(page, args.pause, manifest)
                except Exception:
                    failed.append("master_coordinate")
                    if not args.continue_on_error:
                        raise

            if args.only in ("all", "on_time"):
                for m in months:
                    try:
                        run_on_time_month(page, year, m, args.pause, manifest)
                    except Exception:
                        failed.append(f"on_time_{year}_{m:02d}")
                        if not args.continue_on_error:
                            raise

            if args.only in ("all", "t100"):
                for m in months:
                    try:
                        run_t100_month(page, year, m, args.pause, manifest)
                    except Exception:
                        failed.append(f"t100_{year}_{m:02d}")
                        if not args.continue_on_error:
                            raise

        except PlaywrightTimeoutError:
            logging.error("Timed out waiting for BTS download.")
            raise
        finally:
            manifest.finished_at = datetime.now(timezone.utc).isoformat()
            write_markdown_manifest(manifest)
            context.close()
            browser.close()

    errors: list[str] = []
    if args.only == "all":
        errors = validate_expected_files(year)
    exit_code = 0
    if errors:
        exit_code = 1
        for e in errors:
            logging.error("Validation: %s", e)
    if failed:
        exit_code = 1
        logging.error("Failed segments: %s", ", ".join(failed))
    if exit_code == 0:
        logging.info("All expected raw files present for year %s.", year)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
