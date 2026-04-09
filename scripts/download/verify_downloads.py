"""
Verify raw BTS downloads exist, are non-empty, and match naming conventions.

Run from repo root:
  python scripts/download/verify_downloads.py
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
RAW = REPO_ROOT / "data" / "raw"

ON_TIME_RE = re.compile(r"^on_time_(\d{4})_(\d{2})\.csv$")
T100_RE = re.compile(r"^t100_(\d{4})_(\d{2})\.csv$")


def check_file(path: Path) -> tuple[bool, str]:
    if not path.is_file():
        return False, "missing"
    if path.stat().st_size == 0:
        return False, "empty"
    return True, "ok"


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--year", default="2025")
    args = p.parse_args()
    year = args.year

    errors: list[str] = []

    for m in range(1, 13):
        mm = f"{m:02d}"
        ot = RAW / "on_time" / year / f"on_time_{year}_{mm}.csv"
        ok, why = check_file(ot)
        if not ok:
            errors.append(f"on_time {year}-{mm}: {why} ({ot})")
        elif not ON_TIME_RE.match(ot.name):
            errors.append(f"on_time bad filename: {ot.name}")

        t1 = RAW / "t100_segment" / year / f"t100_{year}_{mm}.csv"
        ok, why = check_file(t1)
        if not ok:
            errors.append(f"t100 {year}-{mm}: {why} ({t1})")
        elif not T100_RE.match(t1.name):
            errors.append(f"t100 bad filename: {t1.name}")

    mc = RAW / "airport_reference" / "master_coordinate_latest.csv"
    ok, why = check_file(mc)
    if not ok:
        errors.append(f"master_coordinate: {why} ({mc})")
    elif mc.name != "master_coordinate_latest.csv":
        errors.append(f"master bad filename: {mc.name}")

    if errors:
        print("VERIFY FAILED", file=sys.stderr)
        for e in errors:
            print(e, file=sys.stderr)
        return 1

    print("VERIFY OK: 12 on_time + 12 t100 + master_coordinate for year", year)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
