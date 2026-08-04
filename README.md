<div align="center">

<img src="organization/logo.png" alt="ATNA" width="140"/>

# ATNA — Air Traffic Network Analysis

![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)
![Pandas](https://img.shields.io/badge/pandas-%23150458.svg?style=for-the-badge&logo=pandas&logoColor=white)
![NumPy](https://img.shields.io/badge/numpy-%23013243.svg?style=for-the-badge&logo=numpy&logoColor=white)
![SciPy](https://img.shields.io/badge/SciPy-%230C55A5.svg?style=for-the-badge&logo=scipy&logoColor=%23ffffff)
![Streamlit](https://img.shields.io/badge/Streamlit-%23FE4B4B.svg?style=for-the-badge&logo=streamlit&logoColor=white)
![Plotly](https://img.shields.io/badge/Plotly-%233F4F75.svg?style=for-the-badge&logo=plotly&logoColor=white)
![pytest](https://img.shields.io/badge/pytest-%23ffffff.svg?style=for-the-badge&logo=pytest&logoColor=2f9fe3)

**Which airports actually hold the U.S. flight network together — and what breaks when one goes down?**

</div>

**ATNA** turns a month of U.S. Bureau of Transportation Statistics flight records into a directed, weighted airport graph, then scores every airport and route on how structurally load-bearing it is. Remove an airport or a route in the scenario editor and the app recomputes connectivity loss, two-hop ripple exposure, and a network health score — in under a second, against the live graph rather than a precomputed lookup.

It answers questions a raw traffic table cannot: *Denver and Charlotte move similar passenger volume — so why does removing Charlotte hurt the network more?* Traffic rank and structural importance are different things, and the gap between them is the whole point of the project.

---

## Contents

- [What it does](#what-it-does) · [Quick start](#quick-start) · [Architecture](#architecture)
- [Performance](#performance) · [Metrics](#metrics-and-formulas) · [Testing](#testing)
- [Project structure](#project-structure) · [Commands](#development-commands)

---

## What it does

| | |
|---|---|
| **Hub scoring** | Blends traffic strength, PageRank, and degree into a single 0–100 percentile score, so a small airport with outsized connectivity is not buried under raw volume. |
| **Bridge detection** | Ranks airports by betweenness on the inverse-weight graph — the connectors whose loss forces long detours, which traffic rank alone never surfaces. |
| **Leiden communities** | Partitions the network into regional clusters and flags the cross-community routes that stitch them together. |
| **Scenario editor** | Remove any airport or route and get connectivity loss, ripple exposure, and network health against the live graph. Every edit is revertible and the history is inspectable. |
| **Vulnerability index** | Precomputes the impact of removing *each* airport individually, so the whole network can be ranked by fragility rather than probed one guess at a time. |
| **Route criticality** | Scores every directed route on weight percentile plus a cross-community bonus, ranking the links that carry structural rather than merely heavy load. |

Seven Streamlit pages: Overview, Network Map, Airport Explorer, Communities, Route Explorer, Scenario Editor, and Methodology.

---

## Quick start

**Requires:** Python 3.10+ and git. Nothing else — no database, no API keys, no accounts.

```bash
git clone https://github.com/sahil-d-patel/ATNA.git
cd ATNA
./setupScripts/setup.sh --demo
./setupScripts/start.sh
```

The app opens at [http://localhost:8501](http://localhost:8501).

<details>
<summary><b>Windows</b></summary>

```batch
git clone https://github.com/sahil-d-patel/ATNA.git
cd ATNA
setupScripts\setup.bat --demo
setupScripts\start.bat
```

</details>

`setup.sh` creates the virtualenv, installs dependencies, generates a demo dataset, runs the full pipeline, and executes the test suite. A cold clone reaches a working app in about a minute.

### About the demo dataset

The BTS extracts are large, rate-limited, and not redistributable, so a fresh clone has no data. Rather than leaving the app dead on arrival, `--demo` synthesizes a BTS-shaped dataset that the **unmodified** pipeline consumes exactly like production input.

- **Real:** identifiers, IATA codes, cities, and coordinates for the 50 busiest U.S. airports.
- **Synthetic:** every flight, passenger, seat, and delay figure — drawn from a gravity model (hub mass over great-circle distance) behind a hub-and-spoke gate, so small airports connect through hubs instead of to each other. Service is decided per unordered pair, because airlines schedule round trips.

The result is a network with genuine structure rather than noise: ~1,280 directed routes carrying ~393,000 flight legs. Leiden recovers four regional communities that line up with real U.S. aviation geography — West (DEN, LAX, LAS, PHX, SEA, SFO), Midwest (ORD, ATL, DTW, MDW, CVG), South (DFW, IAH, MCO, MIA, TPA, FLL), and Northeast (CLT, JFK, BOS, DCA, BWI, IAD) — with ORD and ATL topping the hub rankings. Output is deterministic for a given `--seed`.

### Running on real BTS data

```bash
./setupScripts/setup.sh --data     # Playwright download from TranStats, then full pipeline
```

Downloads on-time performance, T-100 segment, and master coordinate files for the year in [`config/atna.yaml`](config/atna.yaml), then runs ETL → metrics → scenarios. TranStats throttles aggressively; [`scripts/download/MANUAL_BTS_DOWNLOAD.md`](scripts/download/MANUAL_BTS_DOWNLOAD.md) documents the manual fallback.

---

## Architecture

```mermaid
graph TD
    subgraph Ingest
        BTS[BTS TranStats<br/>on-time · T-100 · master coordinate]
        DEMO[Demo generator<br/>gravity model]
        BTS --> RAW[(data/raw/<br/>immutable)]
        DEMO --> RAW
    end

    subgraph ETL["ETL — pandas"]
        RAW --> AIRPORTS[airports.csv<br/>U.S. domestic slice]
        RAW --> EDGES[edges.csv<br/>directed routes<br/>w = log1p flights]
        EDGES --> NODES[nodes.csv<br/>strength · degree]
    end

    subgraph Metrics["Metrics — NetworkX + leidenalg"]
        EDGES --> G{{Directed weighted graph}}
        G --> CENT[PageRank · Betweenness<br/>Eigenvector]
        G --> LEIDEN[Leiden partition]
        CENT --> SCORES[hub_score · bridge_score]
        LEIDEN --> COMM[communities.csv]
        SCORES --> ROUTES[route_metrics.csv]
        LEIDEN --> ROUTES
    end

    subgraph Scenarios["Scenario engine"]
        G --> EDIT[Airport / route removal<br/>zero-copy graph views]
        EDIT --> RIPPLE[Two-hop ripple<br/>lambda = 0.35]
        EDIT --> CONN[LCC loss · reachability loss<br/>SCC condensation]
        RIPPLE --> IMPACT[impact_score<br/>network_health]
        CONN --> IMPACT
        IMPACT --> VULN[vulnerability_score<br/>per airport]
    end

    VULN --> METRICS[(metrics.csv)]
    SCORES --> METRICS
    IMPACT --> SCEN[(scenarios.csv<br/>scenario_exposure.csv)]

    METRICS --> APP[Streamlit · 7 pages<br/>Plotly maps and charts]
    COMM --> APP
    ROUTES --> APP
    SCEN --> APP

    style G fill:#4c78a8,color:#fff
    style APP fill:#FE4B4B,color:#fff
    style RAW fill:#555,color:#fff
    style METRICS fill:#2d7f5e,color:#fff
    style SCEN fill:#2d7f5e,color:#fff
```

Each stage writes CSV artifacts under `data/processed/{snapshot_id}/` and the next stage reads them. Stages are independently runnable and independently testable, and the app only ever reads artifacts — it never recomputes the pipeline.

---

## Performance

The expensive operation is the **vulnerability batch**: it removes every airport in turn and rescores the whole network each time. That is `N` scenarios over an `N`-node, `E`-edge graph, so naive implementations degrade sharply exactly when the dataset gets interesting.

Measured on a 350-airport / 15,000-route graph — full U.S. domestic BTS scale:

| Stage | Before | After | Speedup |
|---|---:|---:|---:|
| `reachable_pairs_count` (single call) | 16.8 ms | 2.3 ms | **7.2×** |
| Vulnerability batch (350 scenarios) | 9.23 s | 2.61 s | **3.5×** |

### Counting reachable pairs without traversing per node

Reachability loss needs the number of ordered reachable pairs. The direct reading of that definition is a breadth-first sweep from every node — `O(V · (V + E))` per scenario, repeated `N` times.

But every node inside a strongly connected component reaches exactly the same set of nodes. So one Tarjan pass condenses the graph, and a reverse-topological bitset union over the condensation DAG yields the count directly:

```
reachable_pairs = Σ_C |C| · (nodes reachable from C − 1)
```

One `O(V + E)` pass replaces `V` full traversals. Verified identical to the per-node count across 300 randomized graphs including empty, single-node, isolated, and fully disconnected cases.

### Removing airports without copying the graph

Each scenario built a full `DiGraph.copy()` to delete one node — duplicating the entire adjacency structure to hide a single vertex, `O(V + E)` per scenario and 72% of remaining runtime after the first fix.

The scored graph is read-only: it is never mutated and never returned. So the engine now uses `nx.restricted_view`, which hides the node in `O(1)` and reads identically. The public `remove_airport` / `remove_route` helpers still return real copies by default (`copy=True`) so external callers keep their mutable-graph contract.

### Invariants hoisted out of the batch loop

Every scenario in the batch removes one airport from the *same* unchanged baseline, so the normalized neighbor shares and the baseline reachable-pair count are loop invariants. Both are computed once and threaded through, rather than re-derived per airport.

> All three changes are structural, not numerical. Artifact values and CSV column order are byte-identical before and after — the locked specification treats both as a contract.

---

## Metrics and formulas

Defined in [`organization/ATNA_MVP_Technical_Spec_and_Workflow.md`](organization/ATNA_MVP_Technical_Spec_and_Workflow.md), which is a **locked contract**: the formulas and CSV column orders below are frozen, and the implementation is tested against them.

`P(·)` is percentile rank scaled to 0–100, which puts otherwise incomparable metrics on one axis.

| Metric | Formula |
|---|---|
| Analysis edge weight | `w(i,j) = log(1 + flight_count(i,j))` |
| Hub score | `0.50·P(strength_total) + 0.30·P(PageRank) + 0.20·P(degree_total)` |
| Bridge score | `P(betweenness)` on the inverse-weight graph |
| Vulnerability | `0.60·P(impact of removing i) + 0.40·P(bridge_score)` |
| Route criticality | `0.70·P(w(i,j)) + 0.30·cross_community_flag` |
| Impact score | `0.40·lcc_loss + 0.30·reachability_loss + 0.30·ripple_severity` |
| Network health | `100 − impact_score` |
| Ripple exposure | Two hops, dependency shares, `λ = 0.35` on the second hop |

Betweenness runs on distance `1/w`: higher traffic means a *shorter* structural distance, since NetworkX treats edge weight additively as cost.

---

## Testing

```bash
PYTHONPATH=src .venv/bin/python -m pytest tests -q
```

**53 tests, all passing, no skips** — roughly 3 seconds end to end.

The suite covers ETL column and join contracts, centrality and hub/bridge math, Leiden partition coverage, route criticality, graph-edit isolation, ripple and scoring formulas, scenario artifact schemas, vulnerability integration, and a headless `AppTest` smoke test that renders all seven Streamlit pages.

Two properties the optimizations depend on are pinned explicitly: that supplying precomputed baseline inputs yields byte-identical scenario rows, and that running a scenario never mutates the shared baseline graph — the app caches one graph across reruns, so a mutating edit would corrupt every later scenario in the session.

Because the demo generator produces a complete dataset, data-dependent tests execute against real artifacts on any machine rather than skipping. Before it existed, 18 of 45 tests silently skipped on a fresh clone — a suite that reported success while a third of the pipeline went untested.

---

## Project structure

```
ATNA/
├── config/atna.yaml            # Snapshot month + resolved raw/processed paths
├── src/
│   ├── etl/                    # BTS extracts → airports.csv, edges.csv, nodes.csv
│   │   ├── load_raw.py         #   typed readers, U.S. domestic filter
│   │   ├── build_airports.py   #   master coordinate join
│   │   ├── build_edges.py      #   route aggregation, log1p analysis weight
│   │   └── build_nodes.py      #   strength and degree rollups
│   ├── metrics/                # Graph construction and scoring
│   │   ├── graph_builder.py    #   validated DiGraph build
│   │   ├── centralities.py     #   PageRank, betweenness, eigenvector
│   │   ├── hub_bridge.py       #   locked composite scores
│   │   ├── leiden_communities.py #  partition + community rollups
│   │   ├── route_criticality.py  #  per-route structural scoring
│   │   └── run_metrics.py      #   stage entrypoint
│   ├── scenarios/              # What-if engine
│   │   ├── graph_edits.py      #   copy or zero-copy view removals
│   │   ├── ripple.py           #   two-hop propagation, λ = 0.35
│   │   ├── scoring.py          #   LCC / reachability / impact / health
│   │   ├── vulnerability.py    #   per-airport batch scoring
│   │   └── engine.py           #   orchestration + deterministic scenario ids
│   └── app/                    # Streamlit application
│       ├── streamlit_app.py    #   router shell
│       ├── data_loader.py      #   cached, schema-guarded artifact loaders
│       ├── scenario_service.py #   session state, history, revert
│       ├── pages/              #   seven pages
│       └── ui/                 #   shared components and formatters
├── scripts/
│   ├── demo/generate_demo_data.py  # Synthetic BTS-shaped dataset
│   ├── download/                   # Playwright TranStats downloader + verifier
│   └── metrics/                    # Static map QA checks
├── setupScripts/               # One-command setup / start / pipeline (sh + bat)
├── tests/                      # 53 tests
├── data/                       # raw (gitignored) · interim · processed · reference
├── organization/               # Locked technical specification
├── .github/workflows/ci.yml    # Lint + full pipeline + tests on 3.10–3.13
└── pyproject.toml              # Ruff and pytest configuration
```

---

## Development commands

```bash
./setupScripts/setup.sh --demo      # Full bootstrap with synthetic data
./setupScripts/setup.sh --data      # Full bootstrap with real BTS download
./setupScripts/setup.sh --skip-data # Environment only
./setupScripts/pipeline.sh          # Rebuild all artifacts: ETL → metrics → scenarios
./setupScripts/start.sh             # Launch the Streamlit app
```

Individual stages, with `src` on the path:

```bash
PYTHONPATH=src .venv/bin/python scripts/demo/generate_demo_data.py --force
PYTHONPATH=src .venv/bin/python -m etl.run_pipeline
PYTHONPATH=src .venv/bin/python -m metrics.run_metrics
PYTHONPATH=src .venv/bin/python -m scenarios.run_scenarios
PYTHONPATH=src .venv/bin/python -m pytest tests -q
```

**Changing the snapshot month:** edit `snapshot_id` in [`config/atna.yaml`](config/atna.yaml) to a `YYYY-MM` value, make sure raw CSVs exist for that month, then re-run the pipeline. Path templates expand `{year}`, `{month}`, and `{snapshot_id}` automatically.

**Raw data policy:** `data/raw/` is immutable in place. Refreshing data means writing to a new path, not overwriting existing bytes, so prior inputs stay inspectable and results stay reproducible.

---

## Tech stack

**Pipeline** — Python 3.13 · pandas · NumPy · PyYAML
**Graph** — NetworkX · python-igraph · leidenalg · SciPy
**App** — Streamlit · Plotly
**Testing** — pytest · Streamlit `AppTest`
**Data acquisition** — Playwright

---

## Documentation

| Document | Purpose |
|---|---|
| [Technical specification](organization/ATNA_MVP_Technical_Spec_and_Workflow.md) | Locked data model, formulas, and workflow |
| [Data sources](data/reference/README_data_sources.md) | BTS tables and why each is used |
| [Field selection notes](data/reference/field_selection_notes.md) | Exact TranStats fields per download |
| [Download spec](docs/data_download_spec.md) | Raw file naming and layout |
| [Manual download](scripts/download/MANUAL_BTS_DOWNLOAD.md) | Fallback when TranStats blocks automation |
| [Validation notes](data/reference/validation_notes_mvp.md) | Snapshot metadata, exclusions, BTS quirks |

---

<div align="center">

Built as a team project at Texas A&M University.

</div>
