# Phase 1: Repository & data foundation - Context

**Gathered:** 2026-04-08
**Status:** Ready for planning

<domain>
## Phase Boundary

Reproducible path from raw BTS inputs to canonical `airports.csv`, `edges.csv`, and `nodes.csv` for at least one monthly snapshot, with validation aligned to the locked MVP spec (§6 column contracts) and documented data dictionary / validation notes for the MVP slice. Scope is REPO-01, REPO-02, and DATA-01 through DATA-06 as in `REQUIREMENTS.md` — not metrics, scenarios, or UI.

</domain>

<decisions>
## Implementation Decisions

### BTS source pinning & raw storage

- **Provenance:** Use a manifest-based approach with verification suitable for academic reproducibility (exact mechanism left to implementation — see Claude's Discretion).
- **Raw immutability:** Do **not** overwrite files under `data/raw/`. If a file is re-fetched, use a new dated subfolder or filename suffix so history remains inspectable.
- **Source scope:** Follow **spec §5 literally** for which raw BTS products (on-time, airport metadata, T-100 segment per DATA-01); no extra products in Phase 1 without a roadmap change.
- **Schema / layout drift:** Do not invest in elaborate automatic healing of BTS layout changes. **Document clearly** that if BTS column layouts or distributions change, **the ETL and manifest/documentation must be updated** explicitly for the new source shape.

### MVP snapshot month

- **Initial month:** Use the **most recent complete BTS month** available at the time the project freezes raw inputs for Phase 1 (not a fixed historical month by policy).
- **Demo stability:** Treat that chosen `YYYY-MM` as the **canonical MVP snapshot** for demos and write-ups **until explicitly bumped** — do not silently rotate the "official" MVP month as time passes.

### Pipeline entrypoints & reruns

- **Primary interface:** **Python** — `python -m ...` and/or `scripts/` entrypoints with **documented arguments** (not Makefile-first for Phase 1).
- **Configuration:** A **single checked-in YAML** (or equivalent) for snapshot month, paths, and BTS file locations — not CLI-only or env-only for Phase 1.
- **Download vs ETL:** **Separate steps:** download/populate `data/raw/` first (manual and/or download script), then run ETL that reads raw and writes canonical tables. No requirement for one chained "download+transform" command in Phase 1.
- **Reproducibility narrative:** README should explain reproducibility in a **clear, academic-grade** way without claiming unrealistic bit-for-exact-byte precision unless the manifest proves it — exact wording left to implementation (Claude's Discretion).

### Validation & join QA

- **Automation:** Include **at least one automated sanity path** (tests or scripts) that exercises column contracts and key joins; full CI coverage is not mandated by this discussion — depth left to implementation (Claude's Discretion).
- **Join problems:** Prefer **transparent handling** — excluded rows / known gaps **documented** rather than silent failures. Exclusions must be visible in validation notes or equivalent.
- **Quality bar:** **Small imperfections are acceptable** (e.g. edge cases, minor naming quirks) as long as **nothing materially detrimental** slips through (e.g. large silent join failures, wrong mass of traffic attributed). Align with roadmap language: no broken joins **inside the declared MVP slice** for anything that would invalidate analysis intent.
- **Validation artifacts location:** Must be **discoverable from README**; exact folder split (`data/reference/` vs `docs/`) left to implementation (Claude's Discretion).

### Claude's Discretion

- Manifest format details (hashing vs lighter checks) while keeping reproducibility credible.
- How much raw BTS to keep on disk beyond the canonical MVP month.
- Directory layout for `snapshot_id` in paths vs flat tables with a column — **must** align with spec §4.2 and REPO-01.
- Depth of automated checks beyond the minimum sanity path.
- Final placement and naming of DATA-06 validation notes and data dictionary files.

</decisions>

<specifics>
## Specific Ideas

- **ETL maintenance:** When BTS changes, explicitly update ETL + tracking docs — no "silent" tolerance for layout drift.
- **MVP month:** "Most recent complete month at freeze" plus "fixed for demos until bumped" — document the actual `YYYY-MM` in the manifest/YAML once chosen.

</specifics>

<deferred>
## Deferred Ideas

None captured — discussion stayed within Phase 1 scope.

</deferred>

---

*Phase: 01-repository-data-foundation*
*Context gathered: 2026-04-08*
