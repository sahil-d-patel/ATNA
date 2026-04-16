# Phase 2: Graph metrics & communities - Context

**Gathered:** 2026-04-08
**Status:** Ready for planning

<domain>
## Phase Boundary

Per-snapshot **directed weighted** analysis graphs with centralities, hub and bridge scores (including percentile scaling per spec), **Leiden** communities, and **route criticality** outputs (`metrics.csv`, `communities.csv`, `route_metrics.csv`). Reproducibility from processed edges alone; a **dev map or notebook** check that community assignments render legibly. Scope is **METR-01–METR-06** only — scenario engine, vulnerability (`METR-07`), and full Streamlit UI are later phases.

</domain>

<decisions>
## Implementation Decisions

### Community map validation
- **Geographic emphasis:** US-centric framing (lower 48 plus Alaska/Hawaii as needed) for the static map / notebook check.
- **Encoding:** Distinct color per community **and** marker size scaled by node strength or traffic.
- **Tiny/singleton communities:** **De-emphasize** — smaller or neutral markers below a size threshold so large communities read first.
- **Phase 2 bar:** **Visual pass** — major regions show coherent color patches; no obvious single-color dominance bug (not required: full spot-check of top hubs per community).

### Metric story (hubs vs bridges vs traffic)
- **Headline framing:** **Balanced trio** — hub score, bridge score, and PageRank presented with **equal weight** when scanning sanity checks and short validation text.
- **Bridge vs traffic distinction:** **Overlap is acceptable** — fail only if bridge ranking is **nearly identical** to pure traffic/strength ranking (e.g. correlation-style smoke), not on requiring many named counterexamples.
- **Where it is documented (Phase 2):** **Validation notes only** — not a dedicated README subsection for metrics interpretation (README expansion can wait for later phases if needed).
- **Column/order presentation:** **Follow spec §6 column order** wherever the spec defines it — no narrative reordering.

### Route criticality QA
- **Spot-check intuition:** Prefer **structural** surprises — examples where criticality is high despite **lower raw traffic** (bottleneck / few alternatives), not only “busiest routes win.”
- **Cross-community routes:** Emphasize **reasonable prevalence** — not zero and not 100% of routes; order-of-magnitude plausible **counts**.
- **Failure conditions:** **Either** triggers rework: (1) data integrity problems (nulls, bad joins, duplicate keys, etc.), **or** (2) criticality effectively **perfectly correlated** with a single raw input column (e.g. identical to passengers).
- **Manual sample depth:** Open — **Claude’s discretion** (time-boxed, pragmatic).

### Reproducibility bar
- **Validation notes must record:** **Package versions and Python version** (minimum traceability).
- **Exact reproducibility level, random seeds, CI golden hashes, and full lockfile/freeze:** **Claude’s discretion** — choose pragmatic defaults consistent with NetworkX/Leiden/Python stack and spec.

### Claude's Discretion
- Reproducibility strictness (bit-identical vs ranking-stable), seeding strategy, CI structural vs golden-hash checks, and depth of manual route spot-checks — user deferred to planner/implementer within the decisions above.

</decisions>

<specifics>
## Specific Ideas

- Map check should read as a **smoke test** for community coherence (patches, no dominance bug), not a full geographic audit.
- Validation narrative should make **hub, bridge, and PageRank** equally visible, while **tables/files stay spec-ordered**.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within Phase 2 scope.

</deferred>

---

*Phase: 02-graph-metrics-communities*
*Context gathered: 2026-04-08*
