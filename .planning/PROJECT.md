# ATNA — Air Traffic Network Analysis (MVP)

## What This Is

An interactive **visual analytics and scenario editing** product for **U.S. domestic** airport traffic, framed as a **network science** tool with a polished demo narrative. Users explore hub structure, **structural bridge** airports, **Leiden** communities, **route criticality**, and run **what-if** removals (airport or route) with a **2-hop structural ripple** model and **before/after** network health metrics.

**Canonical specification:** `organization/ATNA_MVP_Technical_Spec_and_Workflow.md` (Version 1.0, locked MVP). This `PROJECT.md` summarizes and operationalizes that document; on any conflict, the organization spec wins.

## Why Now

The MVP is optimized for **finishability**, **interpretability**, **demo strength**, **technical credibility**, and **clean team parallelization** (data / graph / scenarios / app tracks).

## Users and Context

- Primary: analysts, researchers, and course/demo audiences who need **explainable** network views—not an airline ops simulator.
- Geographic scope: **U.S. domestic only**.
- Time granularity: **monthly snapshots** (`YYYY-MM`).

## Core Value (the one thing that must work)

End-to-end: **BTS-derived monthly graph** → **documented CSV artifacts** (nodes, edges, metrics, communities, route metrics) → **scenario engine** (removals + ripple + impact scores) → **Streamlit + Plotly** app with **all seven functional pages** plus **methodology**, telling a coherent story from overview through disruption.

## Explicit Non-Goals (MVP)

- Real-time delay forecasting, crew/itinerary simulation, multi-user editing, full causal historical propagation.
- Scope or formulas beyond the locked spec without a formal spec revision.

## Constraints and Stack (locked)

| Area | Choice |
|------|--------|
| Frontend | Streamlit, Plotly |
| ETL | pandas or polars |
| Graph | NetworkX primary; **igraph** for Leiden if needed |
| Graph model | Directed weighted airport graph; undirected structural projection for ripple / some views |
| Default edge weight (display) | Flight count |
| Analysis weight | `log(1 + flight_count)` |
| Communities | Leiden |
| Scenario editor | Airport removal, route removal |
| Ripple | Structural, max **2 hops**, λ = **0.35**, second hop discounted |
| Data sources | BTS on-time, airport metadata, T-100 segment (per spec §5) |

## Architecture (five layers)

1. **Raw data** — BTS files unchanged under `data/raw/`.
2. **Cleaning / normalization** — scripts → interim/processed tables.
3. **Graph tables** — `airports.csv`, `edges.csv`, `nodes.csv` (canonical schemas in spec §6).
4. **Metrics engine** — precompute centralities, communities, route scores, scenario outputs → `metrics.csv`, `communities.csv`, `route_metrics.csv`, scenario artifacts.
5. **App** — Streamlit loads **precomputed** artifacts only (no ad hoc notebook state in the product path).

Target repo layout: spec §4.2 (`data/`, `outputs/`, `notebooks/`, `src/{etl,graph,metrics,communities,scenarios,app,utils}/`, `tests/`, `requirements.txt`, `README.md`).

## Product Questions the MVP Must Answer

1. Biggest hubs? 2. Structural bridges? 3. Community partition? 4. Structurally important routes? 5–6. Effect of airport vs route removal? 7. How far does disruption spread (2-hop)? 8. Overall damage (impact / health)?

## Team Tracks (for execution)

- **A:** Data / ETL  
- **B:** Graph & metrics (incl. Leiden integration)  
- **C:** Scenario engine & artifacts  
- **D:** Streamlit / Plotly / integration  

Cross-cutting: schema owner, integration owner, demo owner (per spec §12).

## Requirements

### Validated

(None yet — ship to validate.)

### Active

- [ ] All v1 capabilities listed in `.planning/REQUIREMENTS.md` (derived from locked MVP spec).
- [ ] Artifacts and formulas match spec §6–§9; UI pages match spec §10.
- [ ] Demo sequence executable per spec §14.

### Out of Scope

- Operational delay prediction, aircraft rotation, crew connections, itinerary reconstruction, multi-user editing, deep causal propagation — **per spec §3.3** (why: MVP is structural / educational, not an ops twin).

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Locked MVP spec as single source of truth | User directive; reduces ambiguity and scope creep | Adopted |
| Precompute metrics offline; app reads artifacts | Performance, reproducibility, team parallelism | — Pending |
| Simple composite scores (Hub, Bridge, Vulnerability, Route criticality, Impact) | Finishable, explainable, demo-friendly | — Pending |
| Streamlit + Plotly | Locked in spec for MVP speed and visualization | — Pending |

## Risks and Watchouts

- **Betweenness cost** on full national graphs — may need sampling, filtering, or pre-aggregation; align with “expensive metrics offline” policy.
- **Leiden backend** — bridge igraph labels back into common tables (spec §15.2).
- **Schema drift** — no private schema variants; all outputs documented CSV/parquet (spec §12.3).

## Open Questions

- Which **initial month(s)** ship in v1 demo (still need concrete BTS slice choice)?
- **Deployment** target (local-only vs hosted); spec assumes reproducible pipeline + demo—hosting TBD.

---
*Last updated: 2026-04-08 after GSD `/gsd-new-project` initialization (spec-backed, research skipped by choice).*
