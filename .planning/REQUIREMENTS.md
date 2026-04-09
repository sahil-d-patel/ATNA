# ATNA MVP — Requirements (v1)

**Source:** `organization/ATNA_MVP_Technical_Spec_and_Workflow.md` (locked).  
**IDs:** `CATEGORY-NN` for traceability to `.planning/ROADMAP.md`.

---

## v1 Requirements

### Repository and governance

- [x] **REPO-01**: Repository layout matches spec §4.2 (or documented equivalent) with `data/`, `outputs/`, `src/` package boundaries, `tests/`, `requirements.txt`, `README.md`.
- [x] **REPO-02**: Locked MVP technical spec is version-controlled and referenced as the schema/metrics/UI contract (no parallel undocumented schemas).

### Data foundation (Phase 1 spec)

- [x] **DATA-01**: Raw BTS inputs stored unchanged under `data/raw/` (reporting carrier on-time, airport metadata, T-100 segment as required by spec §5).
- [x] **DATA-02**: ETL produces `airports.csv` with all required columns in spec §6.1.
- [x] **DATA-03**: ETL produces `edges.csv` per spec §6.2 including `snapshot_id` (`YYYY-MM`), `analysis_weight = log(1 + flight_count)`, and `route_key`.
- [x] **DATA-04**: ETL produces `nodes.csv` per spec §6.3 for each snapshot.
- [x] **DATA-05**: At least one monthly snapshot builds **end-to-end without manual fixes**; airport joins validate (spec §11 Phase 1 exit criteria).
- [x] **DATA-06**: Data dictionary / validation notes exist for the MVP slice (spec §11 Phase 1 deliverables).

### Graph metrics (Phase 2 spec)

- [ ] **METR-01**: Build **directed weighted** NetworkX graph per snapshot using analysis weights (spec §7.2).
- [ ] **METR-02**: Compute and persist node strength and degree fields per spec §7.3 into graph/node outputs as required by `nodes.csv` / pipeline.
- [ ] **METR-03**: Compute **PageRank** (directed weighted), **betweenness** (graph per spec §7.4), **eigenvector** when stable (secondary).
- [ ] **METR-04**: Compute **Hub Score** and **Bridge Score** exactly per spec §7.6–§7.7 (percentile scaling §7.5).
- [ ] **METR-05**: Run **Leiden**; produce `metrics.csv` and `communities.csv` per spec §6.4–§6.5 (incl. community traffic, density, top hubs/bridges).
- [ ] **METR-06**: Produce `route_metrics.csv` per spec §6.6 including **route criticality** and cross-community flag (spec §7.10).
- [ ] **METR-07**: **Vulnerability score** on nodes per spec §7.8 (depends on scenario impact for removal—may be wired after scenario engine or precomputed via batch; MVP requires it in `metrics.csv` contract).

### Scenario engine (Phase 3 spec)

- [ ] **SCEN-01**: User can define **airport removal** scenario: rebuild graph, compute summary metrics (spec §8.4, §9).
- [ ] **SCEN-02**: User can define **route removal** scenario with endpoint seeding and 2-hop propagation (spec §8.5).
- [ ] **SCEN-03**: Implement **LCC loss**, **reachability loss**, **ripple severity**, **Impact Score**, **Network Health** per spec §9 (locked formulas).
- [ ] **SCEN-04**: Persist `scenarios.csv` and `scenario_exposure.csv` per spec §6.7–§6.8 (exposure score, hop level, rank).
- [ ] **SCEN-05**: At least **three demo scenarios** run without failure; second hop weaker than first; health decreases when impact increases (spec §11 Phase 3 exit, §13.3).

### Application — pages (Phase 4 spec)

- [ ] **APP-01**: **Overview** page — totals, flight volume, top hubs, snapshot summary (spec §10.1).
- [ ] **APP-02**: **Network map** — airports, routes, thickness by analysis weight, month + threshold filters (spec §10.2).
- [ ] **APP-03**: **Airport explorer** — sortable table, hub/bridge/vulnerability, airport drilldown (spec §10.3).
- [ ] **APP-04**: **Communities** — Leiden coloring, community stats, top hubs/bridges per community (spec §10.4).
- [ ] **APP-05**: **Route explorer** — route table, criticality, cross-community indicator (spec §10.5).
- [ ] **APP-06**: **Scenario editor** — remove airport/route, before/after cards, impact, health, ripple map, affected-airport table (spec §10.6).
- [ ] **APP-07**: **Methodology** page — graph definitions, formulas, assumptions, limitations aligned to implementation (spec §10.7, §13.4).
- [ ] **APP-08**: App **loads precomputed artifacts** only (no notebook-only state in the product path; spec §4.1, §12.3).
- [ ] **APP-09**: Filters and tooltips behave without breaking charts (spec §11 Phase 4 tasks); **export** if time allows.

### QA and polish (Phase 5 spec)

- [ ] **QA-01**: Execute validation themes in spec §13 (data, metrics, scenario, UI) with noted outcomes or fixes.
- [ ] **QA-02**: **Stable demo build** — full narrative demo start-to-finish (spec §14); README documents how to reproduce pipeline + run app.

---

## v2 / Later (deferred)

- Additional snapshots / animation across months as a first-class story.
- Hosted deployment, auth, multi-user collaboration.
- Alternate weights (passenger-first UX) beyond storage as optional field.
- Exports beyond MVP “if time allows.”

---

## Out of Scope

| Item | Reason (spec reference) |
|------|-------------------------|
| Real-world operational delay prediction | §3.3 — not MVP |
| Aircraft rotation / crew / itinerary reconstruction | §3.3 |
| Multi-user editing | §3.3 |
| Deep causal propagation | §3.3 |
| Ripple beyond 2 hops | §8.7 locked |

---

## Traceability

| REQ-ID | Roadmap phase |
|--------|----------------|
| REPO-01, REPO-02, DATA-01–DATA-06 | Phase 1 — Repository & data foundation |
| METR-01–METR-06 | Phase 2 — Graph metrics & communities |
| SCEN-01–SCEN-05, METR-07 | Phase 3 — Scenario engine & vulnerability integration |
| APP-01–APP-09 | Phase 4 — Streamlit application |
| QA-01, QA-02 | Phase 5 — QA, demo polish, documentation |

*Update this table when phases are edited.*
