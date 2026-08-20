"""Compare two snapshots to check whether the scores are stable or noisy.

A score that swings arbitrarily between consecutive months is measuring the sampling
of one month, not the structure of a network. This compares two snapshots and reports
two things: how much the rankings agree, and which airports moved most.

Both matter. High agreement says the metric is picking up something persistent. The
movers say whether the exceptions have a reason — a seasonal route that only operates
in winter should move, and if the biggest movers are inexplicable that is a problem
the aggregate correlation would hide.

Usage::

    PYTHONPATH=src python scripts/validation/snapshot_stability.py \\
        --baseline 2022-11 --comparison 2022-12
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd
from scipy import stats

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

SCORE_COLUMNS = ("hub_score", "bridge_score", "vulnerability_score")
PROCESSED = REPO_ROOT / "data" / "processed"


def load_snapshot(snapshot_id: str) -> tuple[pd.DataFrame, pd.Series]:
    """Metrics for one snapshot, plus its airport-code lookup."""
    directory = PROCESSED / snapshot_id
    metrics_path = directory / "metrics.csv"
    if not metrics_path.is_file():
        raise SystemExit(
            f"no metrics for snapshot {snapshot_id}: expected {metrics_path}.\n"
            f"Build it with: PYTHONPATH=src python -c "
            f"\"from metrics.run_metrics import run; run('config/atna-{snapshot_id}.yaml')\""
        )
    metrics = pd.read_csv(metrics_path)
    airports = pd.read_csv(directory / "airports.csv")
    return metrics, airports.set_index("airport_id_canonical")["airport_code_raw"]


def compare(baseline_id: str, comparison_id: str, movers: int) -> None:
    baseline, codes = load_snapshot(baseline_id)
    comparison, _ = load_snapshot(comparison_id)

    merged = baseline.merge(
        comparison, on="airport_id", suffixes=("_base", "_comp"), how="inner"
    )
    print(f"\n{baseline_id} versus {comparison_id}")
    print(f"  airports present in both: {len(merged)}")
    print(f"  only in {baseline_id}: {len(baseline) - len(merged)}")
    print(f"  only in {comparison_id}: {len(comparison) - len(merged)}")

    print("\nRank agreement between snapshots:")
    for column in SCORE_COLUMNS:
        result = stats.spearmanr(merged[f"{column}_base"], merged[f"{column}_comp"])
        verdict = (
            "stable" if result.statistic >= 0.9
            else "mostly stable" if result.statistic >= 0.75
            else "unstable"
        )
        print(f"  {column:<22} rho = {result.statistic:+.3f}   {verdict}")

    print(f"\nLargest hub-score movements (top {movers}):")
    merged["movement"] = merged["hub_score_comp"] - merged["hub_score_base"]
    largest = merged.reindex(merged["movement"].abs().nlargest(movers).index)
    print(f"  {'code':<6}{baseline_id:>10}{comparison_id:>10}{'change':>10}")
    for _, row in largest.iterrows():
        code = codes.get(int(row["airport_id"]), str(int(row["airport_id"])))
        print(
            f"  {code:<6}{row['hub_score_base']:>10.1f}"
            f"{row['hub_score_comp']:>10.1f}{row['movement']:>+10.1f}"
        )
    print(
        "\n  Movers worth sanity-checking against the calendar: seasonal airports "
        "should\n  move, and a mover with no plausible explanation is worth "
        "investigating."
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--baseline", required=True, help="snapshot id, e.g. 2022-11")
    parser.add_argument("--comparison", required=True, help="snapshot id, e.g. 2022-12")
    parser.add_argument("--movers", type=int, default=8)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    compare(args.baseline, args.comparison, args.movers)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
