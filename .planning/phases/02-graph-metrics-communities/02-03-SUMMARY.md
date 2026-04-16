---
phase: 02-graph-metrics-communities
plan: 03
title: "METR-04 hub/bridge + METR-02 QA + metrics.csv baseline"
completed: 2026-04-09
commits:
  - c0b5b24
  - bd88feb
  - 1f59133
artifacts:
  - data/processed/2025-12/metrics.csv
---

# Phase 02 Plan 03: METR-04 / METR-02 / metrics.csv baseline — Summary

Implemented **METR-04** (Hub/Bridge scores) and **METR-02** validation, and added a Phase 2 runner to produce the first **`metrics.csv`** cut with **placeholders** for later plans.

## What shipped

- **Hub Score / Bridge Score (spec §7.6–§7.7)**
  - `hub_score = 0.50*P(strength_total) + 0.30*P(pagerank) + 0.20*P(degree_total)`
  - `bridge_score = P(betweenness)`
- **METR-02 QA**
  - Recomputes `strength_{in,out,total}` and `degree_{in,out,total}` from the analysis `DiGraph` and asserts they match `nodes.csv` (degrees exact; strengths within tolerance).
- **metrics.csv writer**
  - Writes §6.4 columns in exact order:
    `snapshot_id, airport_id, pagerank, betweenness, eigenvector, hub_score, bridge_score, vulnerability_score, leiden_community_id`
  - Placeholder policy:
    - `vulnerability_score = NaN` (METR-07 later)
    - `leiden_community_id = -1` sentinel (Leiden later)

## Key files

- `src/metrics/hub_bridge.py`
- `src/metrics/tables.py`
- `src/metrics/run_metrics.py`
- `tests/test_hub_bridge_metrics.py`

## Artifacts produced

- **`data/processed/2025-12/metrics.csv`** (via `metrics.run_metrics.run()` with `PYTHONPATH=src`)

## Verification

- `pytest -q` (all tests pass)
- `metrics.csv` written for configured snapshot when processed `nodes.csv` + `edges.csv` exist

## Deviations from plan

None — implemented as written.

## Authentication gates

None.

