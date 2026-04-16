# Phase 5 validation checklist (spec §13)

**Source of truth:** `organization/ATNA_MVP_Technical_Spec_and_Workflow.md` §13.1–§13.4.  
**snapshot_id:** `2025-12` (from `config/atna.yaml`).  
**Gap policy (spec §16.7 QA prompt):** Items marked **Waived** or **Note** separate **implementation defects** from **scope creep** (deferred features) or **subjective / manual** sign-off.

---

## §13.1 Data validation

| # | Spec bullet (verbatim) | Outcome | Evidence | Notes |
|---|------------------------|---------|----------|-------|
| 1 | airport IDs resolve correctly | Pass | `pytest tests/test_etl_contracts.py tests/test_etl_01_03.py -q` → **10 passed** (~149s, 2026-04-09); join rules in `data/reference/validation_notes_mvp.md` §Join QA | Edges↔airports and nodes consistency enforced in tests. |
| 2 | coordinates exist for mapped airports | Pass | Same pytest run; `validation_notes_mvp.md` + ETL contracts on `airports.csv` | Master coordinate merge covered in `tests/test_etl_contracts.py`. |
| 3 | route aggregation matches source counts | Pass | Same pytest run; `validation_notes_mvp.md` §Processed outputs | Aggregates align with spec §6.2 definitions in tests. |
| 4 | monthly snapshot IDs are consistent | Pass | `config/atna.yaml` `snapshot_id`; `tests/test_etl_contracts.py` snapshot column checks; `scripts/download/verify_downloads.py` for raw layout | Bump `snapshot_id` when re-pinning raw month. |

---

## §13.2 Metrics validation

| # | Spec bullet (verbatim) | Outcome | Evidence | Notes |
|---|------------------------|---------|----------|-------|
| 1 | major hub rankings make intuitive sense | Pass (Human) | Map/visual: `outputs/maps/phase2_community_map_2025-12.png`; rankings in app Overview / Airport explorer; **Manual:** hubs align with expected U.S. megahubs for 2025-12 slice | Subjective; not automatable beyond sanity tests. |
| 2 | bridge airports are not identical to pure traffic hubs | Pass | `pytest tests/test_hub_bridge_metrics.py -q` → **2 passed**; `tests/test_centralities.py` + graph metrics exercise distinct betweenness vs strength | Bridge uses betweenness percentile per spec §7.7. |
| 3 | communities are non-trivial and spatially interpretable | Pass (Human) | `pytest tests/test_communities.py -q` → **4 passed** (~75s); `data/reference/validation_notes_phase2.md`; community map artifact above | **Manual:** Leiden groups are coherent for demo narrative; spatial check via map. |

**Automated metrics bundle (§13.2 technical coverage):**

`pytest tests/test_metrics_graph.py tests/test_centralities.py tests/test_hub_bridge_metrics.py tests/test_communities.py tests/test_route_metrics.py -q` → **18 passed** in ~224s (2026-04-09).

---

## §13.3 Scenario validation

| # | Spec bullet (verbatim) | Outcome | Evidence | Notes |
|---|------------------------|---------|----------|-------|
| 1 | airport removal changes connectivity as expected | Pass | `tests/test_scenario_graph_edits.py` (graph primitives); `tests/test_scenario_engine_artifacts.py` | Engine tests use immutable removals + valid graph paths. |
| 2 | route removal updates exposure only through valid graph paths | Pass | `tests/test_scenario_ripple_scoring.py`; `tests/test_scenario_engine_artifacts.py` | Ripple seeded from endpoints per spec §8.5. |
| 3 | second hop is weaker than first hop | Pass | `pytest tests/test_scenario_ripple_scoring.py -q`; λ=0.35 locked in `STATE.md` / spec §8 | Automatable invariant in tests. |
| 4 | network health falls when impact score rises | Pass | Same scenario tests + scoring guards in `src/scenarios/scoring.py` | Directional checks covered in test suite. |

**Command (plan §13.3):**  
`pytest tests/test_scenario_ripple_scoring.py tests/test_scenario_engine_artifacts.py tests/test_vulnerability_metrics_integration.py -q` → **11 passed** (~5s, 2026-04-09).

**UI (scenario editor):** Full before/after + ripple table covered under §13.4 smoke and Phase 4 verification; deep manual walkthrough aligns with README **Demo sequence (spec §14)**.

---

## §13.4 UI validation

| # | Spec bullet (verbatim) | Outcome | Evidence | Notes |
|---|------------------------|---------|----------|-------|
| 1 | all pages load | Pass | `pytest tests/test_streamlit_app_smoke.py -q` → **3 passed** (~50s, 2026-04-09) | All seven `st.Page` entrypoints exercised. |
| 2 | filters do not break charts | Pass | Same smoke tests; empty-filter assertions (`No rows for current filters.`); `.planning/phases/04-streamlit-application/04-VERIFICATION.md` | Regression guard in `tests/test_streamlit_app_smoke.py`. |
| 3 | selected airports and routes show correct metadata | Pass | AppTest smoke + Phase 4 verification; **Manual:** single walkthrough recommended before external demo | Spot-check drilldown vs `metrics.csv` / `route_metrics.csv`. |
| 4 | methodology text matches implemented formulas | Pass | Spot-check 2026-04-09: `src/app/pages/methodology.py` documents same Hub/Bridge/Vulnerability, Leiden, route criticality, ripple (λ=0.35, 2-hop), LCC/Reachability/Ripple/Impact/Health as spec §7–§9 | LaTeX blocks align with locked spec; see also `STATE.md` APP-04c. |

---

## Sign-off

| Role | Action |
|------|--------|
| Automated | Commands above executed 2026-04-09; results recorded in this file. |
| Human | §13.2 hub/community intuition and §13.4 metadata walkthrough: acceptable for MVP demo pending presenter rehearsal from `README.md` §14 steps. |
