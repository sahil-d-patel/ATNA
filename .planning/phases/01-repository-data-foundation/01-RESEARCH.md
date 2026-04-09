# Phase 1: Repository & data foundation — Research

**Researched:** 2026-04-08  
**Domain:** Python ETL (pandas), BTS TranStats CSVs, reproducible academic pipelines  
**Confidence:** MEDIUM (stack verified against `PROJECT.md` and repo; BTS behavior documented in-repo)

## Summary

Phase 1 delivers a **reproducible** path from pinned BTS raw inputs to canonical `airports.csv`, `edges.csv`, and `nodes.csv` for one `YYYY-MM` snapshot, plus repo layout and spec governance. The locked spec (`organization/ATNA_MVP_Technical_Spec_and_Workflow.md`) defines §4.2 layout, §5 sources, and §6.1–6.3 column contracts — plans must treat it as the schema authority.

The repo already contains a **Playwright-based downloader** (`scripts/download/download_bts_data.py`), verification (`verify_downloads.py`), manifests under `data/reference/`, and field notes. Research confirms the standard approach: **pandas** for transforms, **YAML** for a single pipeline config (per `01-CONTEXT.md`), separate **download** vs **ETL** steps, and **pytest** or a **validation script** for column contracts and join QA. Polars is optional; spec/PROJECT lock **pandas or polars** — default **pandas** for consistency with existing scripts and ecosystem familiarity.

**Primary recommendation:** Implement ETL as `src/etl/` modules driven by checked-in YAML; write snapshot outputs under `data/processed/` (or `outputs/tables/` per spec) with one command documented in README; gate quality with automated checks plus DATA-06 notes for exclusions.

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python | 3.10+ | Runtime | README and tooling already assume this |
| pandas | >=2.0 (pin in requirements.txt) | Columnar ETL, joins, aggregations | Spec/PROJECT; matches MVP expectations |
| PyYAML | compatible | Single pipeline config file | Locked in `01-CONTEXT.md` |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | current | Tests for validators / golden-path | At least one automated sanity path |
| numpy | via pandas | Numerics | Implicit for pandas |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| pandas | polars | Faster on huge CSVs; PROJECT allows either — pick one for Phase 1 and stick to it |

**Installation (illustrative):**

```bash
pip install -r requirements.txt
```

## Architecture Patterns

### Recommended project structure (align to spec §4.2)

```text
data/raw/              # immutable raw BTS (existing download layout)
data/interim/          # optional intermediate Parquet/CSV
data/processed/        # canonical airports/edges/nodes for snapshot(s)
data/reference/      # manifests, field notes (existing)
outputs/             # spec tables / figures placeholder
src/etl/             # load_raw, build_airports, build_edges, build_nodes, pipeline entrypoint
tests/               # contract tests / validation tests
```

### Pattern 1: Config-driven pipeline

**What:** One YAML holds `snapshot_id`, paths to raw files or directories, and output paths.  
**When to use:** All Phase 1 ETL runs; avoids env-only configuration per context doc.  
**Example:** Loader reads YAML, resolves paths relative to repo root, passes to builders.

### Pattern 2: Manifest + verification

**What:** Keep `download_manifest_*.json` (or successor) as provenance; `verify_downloads.py` confirms expected files.  
**When to use:** After download, before ETL; supports REPO/DATA reproducibility narrative.

### Anti-patterns to avoid

- **Silent coercions:** Dropping rows without logging — context requires transparent exclusions in DATA-06.
- **Chained download+ETL as one opaque step:** Context separates download vs ETL; document both.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| CSV parsing / joins | Ad-hoc string splits | pandas read_csv, merge | Edge cases (quotes, dtypes) |
| Config sprawl | Multiple undocumented env vars | Single YAML + documented keys | Reproducibility |

## Common Pitfalls

### Pitfall 1: Airport ID vs IATA confusion

**What goes wrong:** Joining on `ORIGIN`/`DEST` strings when spec expects AirportID-keyed graph.  
**Why:** BTS uses multiple identifiers; spec centers on canonical airport IDs.  
**How to avoid:** Follow `field_selection_notes.md` and spec §6 — join on `*_AIRPORT_ID` fields from raw tables.  
**Warning signs:** Large unmatched traffic or duplicate hub counts.

### Pitfall 2: Snapshot scope

**What goes wrong:** Mixing months or years in one `snapshot_id`.  
**How to avoid:** Filter raw rows to `year`/`month` matching YAML `snapshot_id` before aggregating edges.

### Pitfall 3: analysis_weight formula

**What goes wrong:** Wrong log base or forgetting `+1`.  
**How to avoid:** `analysis_weight = log(1 + flight_count)` per §6.2 (natural log per spec intent — confirm in implementation and document if using log1p).

## Code Examples

### Natural log weight (typical)

```python
import numpy as np
# analysis_weight = log(1 + flight_count)
df["analysis_weight"] = np.log1p(df["flight_count"].astype(float))
```

## State of the Art

| Old Approach | Current Approach | Notes |
|--------------|------------------|-------|
| Manual CSV drops only | Manifest + automated verify + ETL | Matches existing repo direction |

## Open Questions

1. **Exact `timezone` source for airports.csv**  
   - What we know: §6.1 lists `timezone`; master has `UTC_LOCAL_TIME_VARIATION`.  
   - Recommendation: Map from master field with documented assumption; note in DATA-06 if simplified.

2. **Interim Parquet vs CSV**  
   - Recommendation: Optional; MVP deliverables are canonical CSVs — interim format is implementation discretion.

## Sources

### Primary (HIGH confidence)

- `organization/ATNA_MVP_Technical_Spec_and_Workflow.md` — §4.2, §5, §6.1–6.3
- `.planning/PROJECT.md` — stack and architecture
- `.planning/phases/01-repository-data-foundation/01-CONTEXT.md` — locked decisions

### Secondary (MEDIUM confidence)

- In-repo: `scripts/download/download_bts_data.py`, `data/reference/field_selection_notes.md`

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH — aligned with PROJECT/spec  
- Architecture: MEDIUM — dirs partially absent until implementation  
- Pitfalls: MEDIUM — domain-specific; validate against real raw rows  

**Research date:** 2026-04-08  
**Valid until:** Revisit if BTS column layouts change materially (per CONTEXT).

---

## RESEARCH COMPLETE

**Phase:** 01 — Repository & data foundation  
**Confidence:** MEDIUM

### Key Findings

- Pandas + YAML + pytest/validation script fits Phase 1 and existing repo.  
- Spec §6.1–6.3 are the column contracts; ETL must target them explicitly.  
- Download path exists; Phase 1 must wire **config → ETL → processed CSVs → validation notes**.  
- Join on AirportID-style fields, not ad-hoc strings; document exclusions.

### File Created

`.planning/phases/01-repository-data-foundation/01-RESEARCH.md`

### Ready for Planning

Research complete. Planner can create PLAN.md files.
