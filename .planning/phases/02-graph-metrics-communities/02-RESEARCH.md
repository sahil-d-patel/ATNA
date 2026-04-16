# Phase 2: Graph metrics & communities — Research

**Researched:** 2026-04-08  
**Domain:** Python graph analytics (directed weighted), community detection (Leiden), CSV artifacts  
**Confidence:** HIGH (stack), MEDIUM (performance at national scale)

## Summary

Phase 2 builds a **directed weighted** graph from `edges.csv` using **`analysis_weight`** as edge weight (spec §7.2), computes **PageRank**, **betweenness**, and **eigenvector centrality** via **NetworkX**, applies **percentile scaling** P(·) on the full airport set per §7.5, derives **Hub** and **Bridge** scores per §7.6–§7.7, runs **Leiden** on an **igraph** view of the same graph, and writes **`metrics.csv`**, **`communities.csv`**, and **`route_metrics.csv`** with spec column order. **Vulnerability** (§7.8) is **out of scope for Phase 2 logic** but the **`vulnerability_score`** column must exist in `metrics.csv` (populate with **NaN** or equivalent and document until Phase 3 / METR-07).

**Primary recommendation:** NetworkX for all centralities and graph traversal; **python-igraph** + **leidenalg** (or igraph’s Leiden API) for communities; pandas for I/O and merges; single CLI entrypoint (e.g. `python -m src.metrics.run_metrics`) reading paths from `config/atna.yaml`.

## Standard Stack

### Core

| Library | Version | Purpose | Why standard |
|---------|---------|---------|--------------|
| **networkx** | ≥3.2 | `DiGraph`, PageRank, betweenness, eigenvector | Spec names NetworkX primary; stable APIs for weighted directed metrics |
| **python-igraph** | ≥0.11 | Graph view + **Leiden** | Spec §15.2: Leiden support cleaner through igraph |
| **leidenalg** | ≥0.10 | Leiden partition (igraph-backed) | Standard Python binding used with igraph |
| **numpy** | (existing) | Arrays, numerics | Already in project |
| **pandas** | (existing) | CSV read/write, merges | Already in project |

### Supporting

| Library | Purpose | When to use |
|---------|---------|-------------|
| **pytest** | Contract + metric sanity tests | All phases |
| **PyYAML** | Extend `atna.yaml` with `outputs` paths for metrics artifacts | Config parity with ETL |

### Alternatives considered

| Instead of | Could use | Tradeoff |
|------------|-----------|----------|
| leidenalg | CDlib, graspologic | Heavier deps; spec already points to igraph |
| NetworkX betweenness | Approximation only | OK as optional optimization if runtime too slow; MVP likely full graph is acceptable |

**Installation (add to `requirements.txt`):**

```text
networkx>=3.2,<4
python-igraph>=0.11,<1
leidenalg>=0.10,<1
```

## Architecture Patterns

### Recommended layout

```text
src/
├── etl/                 # existing
└── metrics/
    ├── __init__.py
    ├── config.py        # resolve paths from atna.yaml (mirror etl/config pattern)
    ├── graph_builder.py # edges.csv → DiGraph (METR-01)
    ├── centralities.py  # pagerank, betweenness, eigenvector (METR-03)
    ├── percentile.py    # P(metric) rank 0–100 (§7.5)
    ├── hub_bridge.py    # hub_score, bridge_score (METR-04)
    ├── leiden_communities.py  # partition + community stats (METR-05)
    ├── route_criticality.py   # route_metrics (METR-06)
    └── run_metrics.py   # orchestration CLI
```

### Pattern: Spec-faithful weights

**What:** Use only `analysis_weight` on edges for analysis graph; keep `flight_count` available for QA/tooltips only.  
**When:** All centrality and Leiden inputs.  
**Pitfall:** Accidentally using `flight_count` as weight breaks parity with §7.2.

### Pattern: igraph from NetworkX

**What:** Build NetworkX graph first (single source of truth), convert to igraph for Leiden only (same nodes/edges/weights).  
**When:** Community detection step.  
**Avoid:** Maintaining two independent graph builders that can drift.

## Don't hand-roll

| Problem | Don’t build | Use instead | Why |
|---------|-------------|-------------|-----|
| Directed weighted PageRank | Custom power iteration | `networkx.pagerank` | Weight handling, convergence |
| Betweenness | Naive all-pairs | `networkx.betweenness_centrality` | Correctness + performance |
| Leiden | Louvain substitute | igraph + leidenalg | Spec locks **Leiden** |
| Percentile P(·) | ad-hoc min-max | `scipy.stats.rankdata` or pandas `.rank(pct=True)*100` | Matches §7.5 percentile rank 0–100 |

**Note:** If avoiding scipy, pandas `rank(pct=True)` × 100 is sufficient.

## Common pitfalls

### Pitfall 1: Eigenvector on disconnected / irreducible graphs

**What goes wrong:** Eigenvector centrality may error or be undefined on some components.  
**Why:** Spec §7.4 treats eigenvector as secondary — “if stable and available.”  
**How to avoid:** Try/except or NetworkX `numpy` backend checks; write **NaN** when unavailable.  
**Warning signs:** `NetworkXError` or all-zero eigenvector.

### Pitfall 2: Betweenness runtime

**What goes wrong:** Full betweenness on large graphs is O(V·E) per pair work — can be slow.  
**Why:** National airport network is medium-sized; still watch full US graph.  
**How to avoid:** Start with exact; if too slow, document k-sample approximation **only** if validation still passes sanity (bridge ≠ pure traffic).

### Pitfall 3: Community ID alignment

**What goes wrong:** `leiden_community_id` in `metrics.csv` does not match `communities.csv`.  
**Why:** Relabeling or off-by-one when merging partitions.  
**How to avoid:** Single dict `airport_id → community_id`; one writer for both artifacts.

### Pitfall 4: Route criticality before communities

**What goes wrong:** `cross_community_flag` wrong if Leiden not run first.  
**Why:** §7.10 uses Leiden communities.  
**How to avoid:** Plan order: Leiden + node community labels before `route_metrics.csv`.

### Pitfall 5: `top_hub_airport_ids` / `top_bridge_airport_ids` encoding

**What goes wrong:** Format does not match what Phase 4 Streamlit expects.  
**Why:** Spec lists columns but not delimiter; must match existing project conventions or spec examples if any.  
**How to avoid:** Use a documented delimiter (e.g. pipe or semicolon) in validation notes; align with `data/reference` examples if present.

## Code examples

### Weighted DiGraph from edges

```python
import networkx as nx
import pandas as pd

def build_graph(edges: pd.DataFrame) -> nx.DiGraph:
    g = nx.DiGraph()
    for row in edges.itertuples(index=False):
        g.add_edge(row.origin_id, row.destination_id, weight=float(row.analysis_weight))
    return g
```

### Percentile P(x) to 0–100

```python
def percentile_rank_0_100(series: pd.Series) -> pd.Series:
    return series.rank(pct=True) * 100.0
```

*(Use same ranking rules for all airports in the snapshot, with documented tie handling.)*

## State of the art

| Area | Practice | Notes |
|------|----------|-------|
| Leiden in Python | igraph + leidenalg | Matches technical spec §15.2 |
| Large betweenness | Approximate k | Defer unless needed |

## Open questions

1. **Exact `top_*_airport_ids` serialization** — Confirm delimiter vs Streamlit parsing in Phase 4 when that page is built; until then, document in validation notes.
2. **Disconnected graph** — Whether to run Leiden per weakly connected component or treat as one graph; prefer library default with documented behavior.

## Sources

### Primary (HIGH)

- `organization/ATNA_MVP_Technical_Spec_and_Workflow.md` — §6.4–§6.6, §7.2–§7.10, §15.2
- NetworkX documentation — centrality algorithms for directed weighted graphs
- igraph / leidenalg documentation — Leiden clustering

### Secondary (MEDIUM)

- Project `02-CONTEXT.md` — map QA bar, hub/bridge narrative, route criticality QA

## Metadata

**Confidence breakdown:** Stack HIGH (spec-locked); performance MEDIUM; serialization LOW until APP-04 consumes files.

**Research date:** 2026-04-08  
**Valid until:** ~30 days or after major NetworkX/igraph major releases.
