---
phase: 02-graph-metrics-communities
plan: 06
subsystem: metrics
tags: community-map, validation-notes

requires:
  - plan: 02-05
    provides: metrics.csv with Leiden IDs + route_metrics.csv
provides:
  - scripts/metrics/community_map_check.py
  - outputs/maps/phase2_community_map_<snapshot>.png (generated)
  - data/reference/validation_notes_phase2.md

completed: 2026-04-09
human_checkpoint: approved
---

# Phase 2 Plan 6: Community map smoke check Summary

Built a runnable community map smoke script and Phase 2 validation notes.

## What was produced

- `scripts/metrics/community_map_check.py` — generates a PNG scatter map of airports colored by `leiden_community_id` with marker size scaled by strength/hub proxy; tiny communities are de-emphasized.
- `outputs/maps/phase2_community_map_2025-12.png` — generated artifact for snapshot `2025-12`.
- `data/reference/validation_notes_phase2.md` — versions + sanity narrative + reproducibility notes.

## Human checkpoint

- Status: **approved** (user confirmed).
- Artifacts remain under `outputs/maps/` by user preference.

