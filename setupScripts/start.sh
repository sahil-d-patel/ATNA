#!/usr/bin/env bash
# Launch the ATNA Streamlit app. Run ./setupScripts/setup.sh first.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="$REPO_ROOT/.venv/bin/python"
cd "$REPO_ROOT"

[[ -x "$PY" ]] || { echo "error: .venv not found — run ./setupScripts/setup.sh first" >&2; exit 1; }

SNAPSHOT_ID="$("$PY" -c 'import yaml; print(yaml.safe_load(open("config/atna.yaml"))["snapshot_id"])')"
if [[ ! -f "data/processed/$SNAPSHOT_ID/metrics.csv" ]]; then
  echo "error: no artifacts for snapshot $SNAPSHOT_ID — run ./setupScripts/setup.sh --demo (or --data) first" >&2
  exit 1
fi

exec env PYTHONPATH=src "$REPO_ROOT/.venv/bin/streamlit" run src/app/streamlit_app.py
