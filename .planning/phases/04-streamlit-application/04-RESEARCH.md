# Phase 04: Streamlit application - Research

**Researched:** 2026-04-09  
**Domain:** Streamlit multipage analytics app over precomputed ATNA artifacts  
**Confidence:** HIGH

## Summary

Phase 04 should be implemented as a Streamlit multipage app with a single entrypoint router and seven dedicated page modules, each bound to the locked spec sections 10.1-10.7 and requirements APP-01 through APP-09. The app must treat `config/atna.yaml` as the only source of `snapshot_id` and artifact paths, then load only precomputed CSV artifacts from `data/processed/{snapshot_id}/`.

The standard implementation pattern is: (1) cached artifact loading (`st.cache_data`) keyed by snapshot and file path, (2) lightweight per-user interaction state in `st.session_state`, (3) form submission for scenario edits to avoid reruns on each keystroke, and (4) deterministic invocation of the existing `scenarios.engine.run_scenario()` to compute before/after cards and ripple outputs.

For verification, use Streamlit's native AppTest framework plus smoke testing on all pages. The key quality gates for this phase are no notebook-state coupling, robust handling of empty filters, and stable chart behavior under filter and selection interactions.

**Primary recommendation:** Use `st.navigation` + `st.Page` as the app shell, centralize artifact loading/caching in one data layer, and wire scenario editor actions to the existing scenario engine with form-based submission.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Streamlit | 1.55.0 docs baseline | Multipage UI framework | Officially preferred multipage routing with `st.Page` + `st.navigation`; built-in session state and testing framework |
| pandas | `>=2.2.0,<3` (repo) | Artifact loading/transforms | Native fit for CSV artifact tables used across all seven pages |
| plotly | `>=4.0.0` (required by `st.plotly_chart`) | Interactive charts/maps/tables integration | First-class Streamlit chart support with selection callbacks and robust tooltip behavior |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| streamlit.testing (`AppTest`) | Included with Streamlit | Page-level smoke and behavior tests | Use for APP-09 and all-page load checks |
| PyYAML | `>=6.0.1` (repo) | Parse `config/atna.yaml` | Use in shared config loader for snapshot/path resolution |
| networkx | `>=3.2,<4` (repo) | Scenario baseline graph operations | Use only inside scenario calls, not for ad hoc UI-only recomputation |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `st.Page` + `st.navigation` | `pages/` directory auto-discovery | `pages/` is simpler but less flexible; `st.navigation` is officially preferred and gives explicit routing control |
| Streamlit AppTest | Playwright/Selenium browser tests | Browser tests are useful for full UI rendering but higher overhead; AppTest is faster for smoke coverage and page exceptions |

**Installation:**
```bash
pip install streamlit plotly
```

## Architecture Patterns

### Recommended Project Structure
```text
src/app/
├── streamlit_app.py         # Entry point; defines st.navigation and shared frame
├── config.py                # Loads snapshot_id/paths from config/atna.yaml
├── data_loader.py           # Cached CSV readers + validation guards
├── scenario_service.py      # Thin adapter over scenarios.engine.run_scenario
├── ui/
│   ├── formatters.py        # Reusable labels/metric formatting
│   └── components.py        # Shared cards, selectors, empty-state blocks
└── pages/
    ├── overview.py          # APP-01
    ├── network_map.py       # APP-02
    ├── airport_explorer.py  # APP-03
    ├── communities.py       # APP-04
    ├── route_explorer.py    # APP-05
    ├── scenario_editor.py   # APP-06
    └── methodology.py       # APP-07
```

### Pattern 1: Entrypoint Router + Explicit Page Registration
**What:** Define all pages in one router file and run selected page via `pg.run()`.  
**When to use:** Always for this phase; ensures deterministic seven-page navigation and avoids implicit page discovery drift.  
**Example:**
```python
# Source: https://docs.streamlit.io/develop/concepts/multipage-apps/page-and-navigation
import streamlit as st

overview = st.Page("src/app/pages/overview.py", title="Overview")
network_map = st.Page("src/app/pages/network_map.py", title="Network Map")
# ... remaining pages ...

pg = st.navigation([overview, network_map])
st.set_page_config(page_title="ATNA", page_icon=":material/flight:")
pg.run()
```

### Pattern 2: Cached Artifact Access Layer
**What:** Wrap CSV loading in `@st.cache_data`, keyed by snapshot and path.  
**When to use:** All precomputed artifacts (`metrics.csv`, `communities.csv`, `route_metrics.csv`, `scenarios.csv`, `scenario_exposure.csv`).  
**Example:**
```python
# Source: https://docs.streamlit.io/develop/api-reference/caching-and-state/st.cache_data
import pandas as pd
import streamlit as st

@st.cache_data(scope="session")
def load_csv(path: str, snapshot_id: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    if "snapshot_id" in df.columns:
        df = df[df["snapshot_id"] == snapshot_id].copy()
    return df
```

### Pattern 3: Scenario Editor with Form Submission
**What:** Put scenario controls inside `st.form` and execute scenario once on submit.  
**When to use:** APP-06 for remove-airport/remove-route interaction and before/after cards.  
**Example:**
```python
# Source: https://docs.streamlit.io/develop/concepts/architecture/forms
import streamlit as st
from scenarios.engine import run_scenario

with st.form("scenario_editor"):
    scenario_type = st.selectbox("Scenario type", ["airport_removal", "route_removal"])
    airport_id = st.number_input("Airport ID", min_value=1, step=1)
    submitted = st.form_submit_button("Run scenario")

if submitted:
    # payload shape must match existing engine contract
    payload = {"airport_id": int(airport_id)}
    scenario_row, exposure_rows = run_scenario(
        baseline_graph=graph,
        snapshot_id=snapshot_id,
        scenario_type=scenario_type,
        payload=payload,
    )
```

### Anti-Patterns to Avoid
- **Notebook-coupled state:** Do not import notebook globals or temporary in-memory outputs; load canonical processed artifacts only.
- **Per-widget rerun for scenario execution:** Avoid recomputing scenario on every control change; use form submit.
- **Page-local duplicate loaders:** Avoid repeated ad hoc CSV parsing in each page; centralize typed loading to one module.
- **Silent missing-column behavior:** Fail fast when locked columns are missing (e.g., `vulnerability_score`).

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Multipage routing | Custom sidebar router state machine | `st.Page` + `st.navigation` | Officially preferred, handles routing and URL/page behavior |
| App smoke testing | Manual click-through checklist only | `streamlit.testing.v1.AppTest` + CI smoke | Deterministic test execution and uncaught exception detection per page |
| Cross-rerun state sync | Custom global dict/singletons | `st.session_state` | Built-in per-session state, survives reruns and across pages |
| Cache invalidation | Homegrown memoization | `st.cache_data` / `st.cache_resource` | Native hashing, TTL, scope controls, cache clear APIs |
| Scenario logic in UI | Reimplement graph edits in page code | `scenarios.engine.run_scenario()` | Existing canonical implementation ensures formula consistency |

**Key insight:** Streamlit already provides routing, state, and caching primitives; custom replacements add fragility and make APP-09 regressions more likely.

## Common Pitfalls

### Pitfall 1: Rerun Storms from Widget Changes
**What goes wrong:** Scenario execution and heavy chart regeneration trigger on every interaction.  
**Why it happens:** Widgets outside forms rerun app immediately on changes.  
**How to avoid:** Use `st.form` for scenario controls and execute only on `st.form_submit_button`.  
**Warning signs:** UI lag, repeated scenario IDs with near-identical payloads, high CPU for simple slider changes.

### Pitfall 2: Cache Staleness Across Snapshot Changes
**What goes wrong:** Charts show old snapshot data after snapshot switch.  
**Why it happens:** Cache key omits `snapshot_id` or path input.  
**How to avoid:** Include `snapshot_id` and resolved path arguments in all cached loader signatures.  
**Warning signs:** Table counts do not match selected snapshot; mixed-snapshot rows.

### Pitfall 3: Form Callback Value Bugs
**What goes wrong:** Callback reads stale values or wrong payload on submit.  
**Why it happens:** Passing form values via callback args instead of reading keyed widget state.  
**How to avoid:** Assign keys and read fresh values from `st.session_state` in callbacks.  
**Warning signs:** Submitted airport/route differs from visible widget values.

### Pitfall 4: Chart Breakage on Empty Filter Results
**What goes wrong:** Exceptions when filters produce empty dataframes.  
**Why it happens:** Chart code assumes at least one row or non-null columns.  
**How to avoid:** Add guard clauses and explicit empty-state UI before plotting.  
**Warning signs:** Intermittent crashes with narrow thresholds/month filters.

### Pitfall 5: Inconsistent Schema Assumptions
**What goes wrong:** Pages silently miscompute because expected columns differ from artifact contract.  
**Why it happens:** Hardcoded renamed fields or stale assumptions.  
**How to avoid:** Validate locked columns from spec section 6.x and fail loudly on mismatch.  
**Warning signs:** Missing `vulnerability_score`, malformed `edited_routes`, or wrong community fields.

## Code Examples

Verified patterns from official sources and current repo contracts:

### Multipage App Router
```python
# Source: https://docs.streamlit.io/develop/concepts/multipage-apps/page-and-navigation
import streamlit as st

pg = st.navigation([
    st.Page("src/app/pages/overview.py", title="Overview"),
    st.Page("src/app/pages/network_map.py", title="Network Map"),
])
pg.run()
```

### Session State Initialization
```python
# Source: https://docs.streamlit.io/develop/concepts/architecture/session-state
import streamlit as st

if "selected_airport_id" not in st.session_state:
    st.session_state.selected_airport_id = None
```

### Existing Scenario Engine Contract (project source)
```python
# Source: src/scenarios/engine.py
scenario_row, exposure_rows = run_scenario(
    baseline_graph=baseline_graph,
    snapshot_id=snapshot_id,
    scenario_type=scenario_type,
    payload=payload,
)
```

### Plotly Selection Behavior
```python
# Source: https://docs.streamlit.io/develop/api-reference/charts/st.plotly_chart
event = st.plotly_chart(fig, key="network_map", on_select="rerun")
selected_indices = event.selection.point_indices if event else []
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `pages/`-only multipage style | `st.Page` + `st.navigation` preferred | Current docs (v1.55 docs) | Better explicit routing and shared app frame control |
| Legacy `st.cache` usage | `st.cache_data` and `st.cache_resource` | Streamlit modern caching architecture | Safer data/resource separation and clearer cache semantics |
| Manual ad hoc UI testing | Native `AppTest` + CI smoke | Current app-testing docs | Fast automated page-level regression detection |

**Deprecated/outdated:**
- `use_container_width` in `st.plotly_chart`: marked deprecated; prefer `width="stretch"`.
- Heavy custom cache wrappers over Streamlit cache decorators: unnecessary and error-prone for this phase.

## Open Questions

1. **Deployment/runtime target for the app**
   - What we know: Phase goal is local MVP app behavior with smoke-tested pages.
   - What's unclear: Final runtime target (local only, Streamlit Community Cloud, internal VM, container).
   - Recommendation: Decide now because secrets handling, CI workflow, and package pinning strategy differ by target.

2. **App file structure convention in repo root**
   - What we know: No current `src/app/` Streamlit module exists.
   - What's unclear: Preferred location (`app/`, `src/app/`, or root `streamlit_app.py`) and command contract for team.
   - Recommendation: Lock one structure before implementation to avoid churn and broken imports during Phase 4.

3. **Scenario editor execution policy**
   - What we know: Existing engine supports runtime scenario computation from baseline graph.
   - What's unclear: Whether UI should only read precomputed scenario rows or allow fresh scenario execution + optional export.
   - Recommendation: Lock policy in plan; if live compute is allowed, constrain it to canonical formulas and optional save path.

## Sources

### Primary (HIGH confidence)
- Streamlit docs: `st.Page` + `st.navigation` (multipage architecture)  
  https://docs.streamlit.io/develop/concepts/multipage-apps/page-and-navigation
- Streamlit docs: `st.cache_data` API (v1.55.0 reference)  
  https://docs.streamlit.io/develop/api-reference/caching-and-state/st.cache_data
- Streamlit docs: `st.cache_resource` API (v1.55.0 reference)  
  https://docs.streamlit.io/develop/api-reference/caching-and-state/st.cache_resource
- Streamlit docs: Session State architecture  
  https://docs.streamlit.io/develop/concepts/architecture/session-state
- Streamlit docs: Forms architecture  
  https://docs.streamlit.io/develop/concepts/architecture/forms
- Streamlit docs: App testing concepts + CI automation  
  https://docs.streamlit.io/develop/concepts/app-testing  
  https://docs.streamlit.io/develop/concepts/app-testing/beyond-the-basics  
  https://docs.streamlit.io/develop/concepts/app-testing/automate-tests
- Streamlit docs: `st.plotly_chart` API  
  https://docs.streamlit.io/develop/api-reference/charts/st.plotly_chart
- Project canonical contract/spec and artifacts:
  - `organization/ATNA_MVP_Technical_Spec_and_Workflow.md`
  - `.planning/REQUIREMENTS.md`
  - `config/atna.yaml`
  - `src/scenarios/engine.py`
  - `data/processed/2025-12/*.csv`

### Secondary (MEDIUM confidence)
- Web search surfaced Streamlit docs routes and usage examples; all critical claims were cross-verified in official docs.

### Tertiary (LOW confidence)
- None used for prescriptive recommendations.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Derived from official Streamlit docs + existing repo dependencies/contracts.
- Architecture: HIGH - Matches official multipage/state/forms guidance and local artifact/schema constraints.
- Pitfalls: HIGH - Grounded in official rerun/state semantics plus phase-specific app contract risks.

**Research date:** 2026-04-09  
**Valid until:** 2026-05-09
