# ATNA MVP — Roadmap

**Depth:** Standard (5 execution phases + spec Phase 0 already satisfied by locked doc).  
**Coverage:** Every v1 requirement in `.planning/REQUIREMENTS.md` maps to exactly one phase below.

---

## Phase 1 — Repository & data foundation

**Goal:** Reproducible path from raw BTS to canonical `airports.csv`, `edges.csv`, `nodes.csv` for at least one monthly snapshot.

| Requirement IDs |
|-----------------|
| REPO-01, REPO-02, DATA-01, DATA-02, DATA-03, DATA-04, DATA-05, DATA-06 |

**Success criteria (observable)**

1. Cloning the repo plus documented steps reproduces processed tables from raw inputs for one `YYYY-MM` snapshot.
2. `airports.csv`, `edges.csv`, `nodes.csv` validate against spec §6 column contracts in automated checks or documented QA.
3. No broken airport joins in the MVP slice; validation notes capture any exclusions.

**Dependencies:** None (first build slice).

**Plans:** 4 plans

Plans:

- [x] `01-01-PLAN.md` — Repository skeleton, dependencies, README governance (REPO-01, REPO-02, DATA-01 policy)
- [x] `01-02-PLAN.md` — Single `config/atna.yaml` + loader (pipeline configuration)
- [x] `01-03-PLAN.md` — ETL: `airports.csv` and `edges.csv` (DATA-02, DATA-03)
- [x] `01-04-PLAN.md` — `nodes.csv`, pipeline entrypoint, tests, validation notes (DATA-04, DATA-05, DATA-06)

---

## Phase 2 — Graph metrics & communities

**Goal:** Per-snapshot directed weighted analysis graphs, centralities, hub/bridge scores, Leiden communities, route criticality outputs.

| Requirement IDs |
|-----------------|
| METR-01, METR-02, METR-03, METR-04, METR-05, METR-06 |

**Success criteria**

1. `metrics.csv`, `communities.csv`, `route_metrics.csv` exist per spec §6 with sensible sanity checks (major hubs plausible; bridges not identical to pure traffic ranking).
2. Community assignments render cleanly on a dev map view (static check or notebook acceptable before full app).
3. PageRank, betweenness, and Leiden outputs are reproducible from processed edges alone.

**Dependencies:** Phase 1 outputs.

**Plans:** 6 plans

Plans:

- [x] `02-01-PLAN.md` — Dependencies, config paths, NetworkX DiGraph from edges (METR-01)
- [x] `02-02-PLAN.md` — Percentile P(·), PageRank, betweenness, eigenvector (METR-03)
- [x] `02-03-PLAN.md` — Hub/Bridge scores, nodes↔graph consistency, metrics.csv placeholders (METR-02, METR-04)
- [x] `02-04-PLAN.md` — Leiden, communities.csv, leiden_community_id on metrics (METR-05)
- [x] `02-05-PLAN.md` — route_metrics.csv, criticality, cross-community flag (METR-06)
- [x] `02-06-PLAN.md` — Community map smoke script, validation notes, human map review

---

## Phase 3 — Scenario engine & vulnerability integration

**Goal:** Airport and route removal scenarios, 2-hop ripple (λ = 0.35), locked aggregate scores, persisted scenario artifacts; complete `metrics.csv` vulnerability field.

| Requirement IDs |
|-----------------|
| SCEN-01, SCEN-02, SCEN-03, SCEN-04, SCEN-05, METR-07 |

**Success criteria**

1. Three distinct demo scenarios (mix of airport and route removals) run end-to-end without error.
2. `scenarios.csv` and `scenario_exposure.csv` match spec §6.7–§6.8; ripple weaker at hop 2 than hop 1.
3. Impact score and network health move in opposite directions as expected under controlled edits.
4. `metrics.csv` includes **vulnerability_score** per spec §7.8 once removal impact is computable (batch or integrated).

**Dependencies:** Phase 2 (graph + bridge scores); uses Leiden labels for cross-community route context where needed.

**Plans:** 4 plans

Plans:

- [x] `03-01-PLAN.md` — Scenario foundations: config contracts, typed payloads, immutable graph edits (SCEN-01/SCEN-02 base)
- [x] `03-02-PLAN.md` — Two-hop ripple and locked scoring formulas with deterministic tests (SCEN-02/SCEN-03)
- [x] `03-03-PLAN.md` — Scenario engine orchestration, scenario artifacts, and 3 demo scenario runner (SCEN-01/SCEN-04/SCEN-05)
- [x] `03-04-PLAN.md` — Vulnerability batch + `metrics.csv` integration for METR-07

---

## Phase 4 — Streamlit application

**Goal:** Full seven-page interactive product plus methodology, consuming precomputed artifacts.

| Requirement IDs |
|-----------------|
| APP-01, APP-02, APP-03, APP-04, APP-05, APP-06, APP-07, APP-08, APP-09 |

**Success criteria**

1. Each page in spec §10.1–§10.7 loads with real artifact data for the chosen snapshot.
2. Scenario editor drives the scenario engine and displays before/after, ripple map, and affected-airport table.
3. No page relies on notebook-only state; filters and tooltips do not break charts on smoke tests.

**Dependencies:** Phases 1–3 artifacts available under stable paths (`outputs/` or agreed layout).

---

## Phase 5 — QA, demo polish, documentation

**Goal:** Validation checklist executed, demo script rehearsed, README reproduces pipeline and app launch.

| Requirement IDs |
|-----------------|
| QA-01, QA-02 |

**Success criteria**

1. Spec §13 themes (data, metrics, scenario, UI) checked with recorded outcomes.
2. README documents environment, ETL entrypoints, metrics build, scenario run, and `streamlit run` (or equivalent).
3. Demo sequence §14 can be executed without manual data fixes.

**Dependencies:** Phase 4 complete.

---

## Coverage checklist

| Phase | Requirement count |
|-------|-------------------|
| 1 | 8 |
| 2 | 6 |
| 3 | 6 |
| 4 | 9 |
| 5 | 2 |
| **Total** | **31** |

All REQ-IDs in `REQUIREMENTS.md` appear exactly once above.

---

*Generated: 2026-04-08 — aligned to `organization/ATNA_MVP_Technical_Spec_and_Workflow.md` §11.*
