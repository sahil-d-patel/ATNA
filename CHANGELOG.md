# Changelog

Notable changes to ATNA. Dates are the date the work landed.

## 2026-08-27

### Added

- **Second validation event.** The harness now takes an arbitrary event window and was
  pointed at the 11 January 2023 FAA NOTAM outage. Spearman ρ = +0.206 (p = 0.042),
  partial ρ = +0.302 — weaker than December 2022, and the reason is the finding:
  December was a *propagating* failure, January a *uniform* one where nothing spread
  through the network. Airport size explains nothing about January (−0.073) while
  network position still does. The model predicts disruptions that propagate.
- **Correlated outage in the editor.** `airport_set_removal` existed in the engine but
  had no interface; the scenario editor now removes several airports in one scenario.
- **Snapshot Comparison page.** Rank agreement between any two built snapshots, with a
  slope chart of the largest movers.

### Changed

- **Betweenness computed through igraph**, already a dependency for Leiden. 0.345s to
  0.134s on a real snapshot, with output identical to the last bit wherever shortest
  paths are unique. Tied paths can differ by ~1e-3 because Brandes splits credit among
  them; real `log1p` weights produce 490 distinct distances and a difference of exactly
  zero.

### Fixed

- Snapshot ids parsed as dates by Plotly, rendering a November timeline from
  `2022-11` / `2022-12`.
- Unused dataclass in the validation script; stale test count and missing
  `scripts/validation/` entry in the contributor docs; page count corrected to eight.

## 2026-08-23

### Changed — the ripple model, selected by measurement

Two defects, both of which made `ripple_severity` useless as the 30% term of
`impact_score`:

- **Shock is now proportional to the removed airport's strength** (spec §8.6). A fixed
  shock of 100 was conserved regardless of airport size and then divided among that
  airport's neighbours, so the larger the airport the thinner its own shock spread.
  On the real 348-airport November 2022 network, DFW has 360 neighbours and reached
  each with 0.28 — far below the threshold — so **every major hub scored exactly zero**.
- **Severity is the traffic-weighted mean exposure** (spec §9.3), replacing a count of
  airports above a fixed threshold of 10, which discarded both the magnitude of each
  exposure and the size of the airport it landed on.

Neither change was argued into place. Four combinations were measured against the
December 2022 disruption:

| Formulation | Distinct values | Hubs in top 10 | ρ | Partial ρ |
|---|---:|---:|---:|---:|
| Fixed shock, count ≥ 10 (previous) | 9 | 0 | +0.387 | +0.386 |
| Fixed shock, traffic-weighted | 332 | 0 | +0.387 | +0.386 |
| Strength shock, count ≥ 10 | 1 | 0 | +0.411 | +0.457 |
| **Strength shock, traffic-weighted** | **332** | **9** | **+0.411** | **+0.457** |

The adopted pair is the only one that both discriminates between airports and agrees
better with what actually happened. Ripple severity now takes 332 distinct values
across 348 airports and ranks ATL, DFW, DEN, ORD.

Validation improved from ρ = +0.387 to **+0.411**, and from +0.386 to **+0.457** once
airport size is controlled for.

### Changed — eigenvector centrality

Computed on the largest strongly connected component and left undefined outside it,
rather than abandoning the whole column whenever the snapshot as a whole was not
strongly connected. That cost every airport in the giant component a value it could
legitimately have carried.

### Fixed — documentation accuracy

The README claimed BTS extracts were "not redistributable" and that TranStats
"throttles aggressively". Neither held up: the downloader fetched the validation
dataset directly in about 90 seconds. Both claims corrected.

## 2026-08-20

### Changed — scoring

- **Connectivity loss is measured in traffic, not counts.** Both connectivity terms
  previously counted airports and reachable pairs equally, so losing ATL and losing ANC
  were the same event. Each took only *two distinct values across fifty airports*,
  which collapsed `impact_score` onto its ripple term and let peripheral airports
  outrank the largest hubs. Both now weight by endpoint strength (spec §9.1, §9.2).
  Each yields fifty distinct values on the same snapshot, and the vulnerability ranking
  now reads ORD, ATL, LGA, EWR, CLT.

  This moves every artifact carrying `vulnerability_score`, `impact_score`,
  `lcc_loss`, or `reachability_loss`.

### Added

- **Validation against the December 2022 disruption.** Predicted ripple exposure
  correlates with observed cancellation increase at ρ = +0.387 (p = 1.6 × 10⁻⁶) across
  144 airports, and survives controlling for airport size (partial ρ = +0.386). See
  [`docs/validation_december_2022.md`](docs/validation_december_2022.md).
- **Snapshot stability check.** Hub rankings agree at ρ = +0.972 between consecutive
  real months; the largest movers are Colorado ski airports gaining December service.
- **Multi-airport scenarios** (`airport_set_removal`), so a correlated outage can be
  modelled as one event rather than a sum of independent removals.
- **Month selection in the downloader** (`--months 11,12`), since a year of on-time
  data is several gigabytes.
- **Interface walkthrough PDF**, generated by driving the running app with Playwright.

### Fixed

- Artifact caches keyed on path but not modification time, and the invalidation
  argument was underscore-prefixed, which Streamlit excludes from cache keys. A
  pipeline rebuild left the app serving stale data until restart.
- `metrics.csv` did not reproduce byte for byte: NetworkX calls ARPACK without pinning
  a start vector.
- The application read the gitignored raw BTS tree; it now uses processed artifacts
  only and runs with `data/raw/` absent entirely.
- Airport identity rendered as DOT ids across every page except the scenario editor.
- Score columns were formatted to strings before display, so tables sorted them
  lexicographically.
- Package re-exports in `etl/__init__.py` shadowed their own submodules.

## Earlier

- Vulnerability sweep optimized from 9.23 s to 0.33 s (28×) through SCC condensation,
  zero-copy graph views, hoisted baseline invariants, and a SciPy-backed connectivity
  index. Artifact output byte-identical throughout.
- Synthetic demo dataset so a cold clone runs without a BTS download; before it,
  18 of 45 tests silently skipped.
- Continuous integration across Python 3.10–3.13, Ruff, and mypy.
