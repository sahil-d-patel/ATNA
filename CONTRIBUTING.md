# Contributing

## Getting set up

```bash
./setupScripts/setup.sh --demo
```

That creates the virtualenv, installs dependencies, generates a synthetic snapshot so
the application has data, runs the full pipeline, and executes the tests. A cold clone
reaches a working app in about a minute. No database, API keys, or accounts.

## Before you open a pull request

```bash
PYTHONPATH=src .venv/bin/python -m pytest tests -q   # 92 tests, no skips
.venv/bin/ruff check src tests scripts
.venv/bin/python -m mypy
```

CI runs the same three on Python 3.10 through 3.13, and additionally regenerates the
demo snapshot and runs ETL, metrics, and scenarios end to end. A change that breaks the
pipeline fails CI even when every unit test passes.

## The one rule that matters

**The metric formulas and CSV column orders are a contract.** They are defined in
[`organization/ATNA_MVP_Technical_Spec_and_Workflow.md`](organization/ATNA_MVP_Technical_Spec_and_Workflow.md)
and the implementation is tested against them. Artifacts are supposed to be
reproducible: the same input month yields the same bytes, on any machine, on any run.

So when you change anything under `src/etl/`, `src/metrics/`, or `src/scenarios/`:

1. Regenerate the artifacts and diff them.

   ```bash
   cp -r data/processed/2025-12 /tmp/before
   ./setupScripts/pipeline.sh
   diff -r /tmp/before data/processed/2025-12
   ```

2. If nothing should have changed, that diff must be empty. `scenarios.csv` will differ
   in `created_at` only, which is a wall-clock stamp.

3. If values *should* change, say so explicitly in the commit message, explain why, and
   raise it with the team. A silent change to `vulnerability_score` is much worse than a
   loud one.

Optimizations are held to a stronger standard: they must be structurally different and
numerically identical. `tests/test_scenario_precomputed_equivalence.py` and
`tests/test_connectivity_index.py` exist to pin exactly that, and new fast paths belong
alongside them.

## Conventions

- **Commits** follow [Conventional Commits](https://www.conventionalcommits.org/):
  `feat(scope):`, `fix(scope):`, `perf(scope):`, `docs:`, `test:`, `chore:`.
  The body should say *why*, since the diff already says what.
- **Comments** explain reasoning, not mechanics. If a line is surprising, say what makes
  it necessary; if it is obvious, leave it alone.
- **Tests** assert behavior worth protecting. A test that passes whether or not the code
  works is worse than no test, because it reads like coverage.
- **Line length** is 100. Ruff enforces import order, pyupgrade, bugbear, and
  comprehension rules; see `pyproject.toml`.

## Layout

| Path | What lives there |
|---|---|
| `src/etl/` | Raw BTS extracts to `airports.csv`, `edges.csv`, `nodes.csv` |
| `src/metrics/` | Graph construction, centralities, communities, composite scores |
| `src/scenarios/` | Removal engine, ripple propagation, scoring, vulnerability sweep |
| `src/app/` | Streamlit application; reads artifacts, never recomputes the pipeline |
| `scripts/demo/` | Synthetic dataset generator |
| `scripts/download/` | BTS acquisition and verification |
| `scripts/docs/` | Interface capture and PDF generation |

Each pipeline stage writes CSVs and the next stage reads them, so stages run and test
independently. The application only ever reads artifacts; if a page needs a number that
does not exist yet, it belongs in a pipeline stage rather than in the page.

## Regenerating the interface document

```bash
./setupScripts/start.sh                                  # one shell
PYTHONPATH=src .venv/bin/python scripts/docs/capture_ui.py   # another
```

This drives the running application with Playwright, including an actual airport
removal, and writes `docs/ui/ATNA-interface.pdf`. It is automated so the document
tracks the code; a page that fails to render fails the capture rather than quietly
leaving a stale screenshot behind.

## Data

`data/raw/` is immutable in place and gitignored. Refreshing means writing to a new
path, never overwriting existing bytes, so prior inputs stay inspectable and results
stay reproducible. The BTS extracts are not redistributable, which is why the demo
generator exists.
