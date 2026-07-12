#!/usr/bin/env bash
# ATNA one-command setup: environment, dependencies, and (optionally) data.
#
#   ./setupScripts/setup.sh              interactive: installs everything, offers demo data
#   ./setupScripts/setup.sh --demo       non-interactive: bootstrap synthetic demo snapshot
#   ./setupScripts/setup.sh --data       full BTS download (Playwright) + real pipeline
#   ./setupScripts/setup.sh --skip-data  environment only, no data bootstrap
#   ./setupScripts/setup.sh -y           assume "yes" at prompts
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="$REPO_ROOT/.venv"
PY="$VENV/bin/python"
MIN_PY_MINOR=10

BOLD=$(tput bold 2>/dev/null || true)
GREEN=$(tput setaf 2 2>/dev/null || true)
YELLOW=$(tput setaf 3 2>/dev/null || true)
RED=$(tput setaf 1 2>/dev/null || true)
RESET=$(tput sgr0 2>/dev/null || true)

info()  { echo "${BOLD}${GREEN}==>${RESET}${BOLD} $*${RESET}"; }
warn()  { echo "${BOLD}${YELLOW}warning:${RESET} $*"; }
fail()  { echo "${BOLD}${RED}error:${RESET} $*" >&2; exit 1; }

DEMO=0; DATA=0; SKIP_DATA=0; ASSUME_YES=0
for arg in "$@"; do
  case "$arg" in
    --demo) DEMO=1 ;;
    --data) DATA=1 ;;
    --skip-data) SKIP_DATA=1 ;;
    -y|--yes) ASSUME_YES=1 ;;
    -h|--help) grep '^#' "$0" | sed 's/^# \{0,1\}//' | head -8; exit 0 ;;
    *) fail "unknown option: $arg (see --help)" ;;
  esac
done
[[ $DEMO -eq 1 && $DATA -eq 1 ]] && fail "--demo and --data are mutually exclusive"

cd "$REPO_ROOT"

# 1. Python
info "Checking Python"
PYTHON_BIN="$(command -v python3 || true)"
[[ -n "$PYTHON_BIN" ]] || fail "python3 not found — install Python 3.${MIN_PY_MINOR}+ from https://www.python.org/"
PY_VERSION="$("$PYTHON_BIN" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
PY_MINOR="${PY_VERSION#3.}"
[[ "${PY_VERSION%%.*}" == "3" && "$PY_MINOR" -ge "$MIN_PY_MINOR" ]] \
  || fail "Python ${PY_VERSION} found, but 3.${MIN_PY_MINOR}+ is required"
echo "    Python ${PY_VERSION} at ${PYTHON_BIN}"

# 2. Virtual environment
if [[ ! -x "$PY" ]]; then
  info "Creating virtual environment (.venv)"
  "$PYTHON_BIN" -m venv "$VENV"
else
  info "Reusing existing virtual environment (.venv)"
fi

# 3. Dependencies
info "Installing dependencies (requirements.txt)"
"$PY" -m pip install --quiet --upgrade pip
"$PY" -m pip install --quiet -r requirements.txt
echo "    $("$PY" -m pip --version)"

# 4. Data bootstrap
SNAPSHOT_ID="$("$PY" - <<'EOF'
import yaml
print(yaml.safe_load(open("config/atna.yaml"))["snapshot_id"])
EOF
)"
ARTIFACTS_DIR="$REPO_ROOT/data/processed/$SNAPSHOT_ID"

run_pipeline() {
  info "Running ETL pipeline (snapshot $SNAPSHOT_ID)"
  PYTHONPATH=src "$PY" -m etl.run_pipeline
  info "Computing graph metrics and communities"
  PYTHONPATH=src "$PY" -m metrics.run_metrics
  info "Running demo scenarios"
  PYTHONPATH=src "$PY" -m scenarios.run_scenarios
}

if [[ $SKIP_DATA -eq 1 ]]; then
  info "Skipping data bootstrap (--skip-data)"
elif [[ -f "$ARTIFACTS_DIR/metrics.csv" ]]; then
  info "Artifacts already present for snapshot $SNAPSHOT_ID — skipping data bootstrap"
elif [[ $DATA -eq 1 ]]; then
  info "Installing Playwright Chromium for the BTS downloader"
  "$PY" -m playwright install chromium
  info "Downloading BTS data (this can take a while; TranStats may throttle)"
  "$PY" scripts/download/download_bts_data.py
  "$PY" scripts/download/verify_downloads.py --year "${SNAPSHOT_ID%%-*}"
  run_pipeline
else
  if [[ $DEMO -eq 0 && $ASSUME_YES -eq 0 ]]; then
    echo
    echo "No processed artifacts found for snapshot ${SNAPSHOT_ID}."
    read -r -p "Generate a synthetic demo dataset so the app runs immediately? [Y/n] " answer
    case "${answer:-Y}" in [Yy]*) DEMO=1 ;; *) DEMO=0 ;; esac
  elif [[ $ASSUME_YES -eq 1 ]]; then
    DEMO=1
  fi
  if [[ $DEMO -eq 1 ]]; then
    info "Generating synthetic demo dataset (snapshot $SNAPSHOT_ID)"
    PYTHONPATH=src "$PY" scripts/demo/generate_demo_data.py
    run_pipeline
  else
    warn "Environment ready, but the app has no data. Re-run with --demo or --data later."
  fi
fi

# 5. Sanity check
info "Running self-contained test suite"
PYTHONPATH=src "$PY" -m pytest tests -q --no-header -x -k "not streamlit" >/dev/null \
  && echo "    tests passed" \
  || warn "some tests did not pass — run 'PYTHONPATH=src $PY -m pytest tests -q' for details"

echo
info "Setup complete"
echo "    Start the app:   ./setupScripts/start.sh"
echo "    Rebuild data:    ./setupScripts/pipeline.sh"
echo "    Run all tests:   PYTHONPATH=src .venv/bin/python -m pytest tests -q"
