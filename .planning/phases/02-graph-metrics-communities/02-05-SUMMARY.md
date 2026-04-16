---
phase: 02-graph-metrics-communities
plan: 05
subsystem: metrics
tags: route_metrics, criticality, cross_community

requires:
  - plan: 02-04
    provides: metrics.csv with leiden_community_id
provides:
  - route_metrics.csv (§6.6) with cross_community_flag + route_criticality_score (§7.10)

completed: 2026-04-09
---

# Phase 2 Plan 5: Route metrics (METR-06) Summary

Implemented `route_metrics.csv` per spec §6.6 with **cross-community flag** and **route criticality score** per §7.10, wired into the Phase 2 metrics runner.

## Commits

1. **Cross-community flag** — `1156d58` — `feat(02-05): add cross-community route flag`
2. **Route criticality score** — `619c891` — `feat(02-05): compute route criticality score`
3. **Pipeline wiring + tests** — `69593bc` — `feat(02-05): write route_metrics.csv and add tests`

## Key files

- `src/metrics/route_criticality.py` — builds per-route table; `RouteCriticality = 0.70*P(w) + 0.30*CrossCommunity`
- `src/metrics/run_metrics.py` — writes `route_metrics.csv` after metrics + communities using the same snapshot edges + Leiden IDs
- `tests/test_route_metrics.py` — contract + synthetic logic + optional real-snapshot sanity checks

## Verification

- `pytest tests/test_route_metrics.py -q` — passed
- Full suite `pytest tests -q` — passed

## Artifact check (configured snapshot)

- `data/processed/2025-12/route_metrics.csv` written
- Cross-community share observed ~46% (non-degenerate)

