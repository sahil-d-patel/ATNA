#!/usr/bin/env bash
# Rebuild all processed artifacts for the configured snapshot:
# ETL (airports/edges/nodes) -> metrics/communities/routes -> demo scenarios.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="$REPO_ROOT/.venv/bin/python"
cd "$REPO_ROOT"

[[ -x "$PY" ]] || { echo "error: .venv not found — run ./setupScripts/setup.sh first" >&2; exit 1; }

PYTHONPATH=src "$PY" -m etl.run_pipeline "$@"
PYTHONPATH=src "$PY" -m metrics.run_metrics
PYTHONPATH=src "$PY" -m scenarios.run_scenarios
