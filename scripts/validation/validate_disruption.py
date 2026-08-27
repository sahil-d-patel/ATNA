"""Test ATNA's ripple predictions against a real network disruption.

Every score this project produces is a modelling output. Nothing so far establishes
that those outputs correspond to anything that happened. This script is the check.

**The natural experiment.** Between 21 and 29 December 2022 a winter storm and a
carrier scheduling collapse took a large share of U.S. domestic capacity offline. In
the BTS on-time data the signal is unambiguous: system-wide cancellations run near
0.6% before the event, peak at 27.6% on 23 December, and return to 0.7% on 30
December. The disruption is concentrated at a identifiable set of airports.

**The test.** Build the network from *November* 2022, so nothing about the event
informs the graph. Take the airports where the disruption actually originated, feed
them to the two-hop ripple model as a simultaneous removal, and ask whether predicted
exposure ranks the *remaining* airports in the same order as the degradation they
actually suffered.

**What would falsify it.** If exposure carries no information about who suffered, the
rank correlation is indistinguishable from zero. That outcome is reported the same as
any other; the point of the exercise is to find out.

**Known confounders**, stated because they bound what a positive result means:

* The storm hit geographically, and geography correlates with network position.
  A correlation here is not proof the *network* mechanism is what drove it.
* Southwest did not vanish; it degraded. The model removes airports outright.
* Airports serve many carriers, so a single-carrier collapse only partly removes any
  given airport.

Usage::

    PYTHONPATH=src python scripts/validation/validate_disruption.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from metrics.config import load_config  # noqa: E402
from metrics.graph_builder import build_analysis_graph, load_edges  # noqa: E402
from scenarios.engine import run_scenario  # noqa: E402

# The event window, and the stretch of the same month used as its own control.
EVENT_DAYS = range(22, 30)
CONTROL_DAYS = range(1, 21)

# How many origin airports are treated as the source of the disruption. Chosen by
# observed cancellation spike, not by assumption about which carrier was involved.
SEED_COUNT = 6

# Airports below this many control-period flights are dropped: a handful of departures
# makes a cancellation rate that swings wildly for reasons unrelated to the network.
MIN_CONTROL_FLIGHTS = 200


def load_observed(on_time_csv: Path) -> pd.DataFrame:
    """Per-airport cancellation rate in the event window versus the control window."""
    frame = pd.read_csv(
        on_time_csv,
        usecols=["FL_DATE", "ORIGIN_AIRPORT_ID", "CANCELLED"],
        low_memory=False,
    )
    frame["day"] = pd.to_datetime(frame["FL_DATE"], format="mixed").dt.day
    frame["CANCELLED"] = pd.to_numeric(frame["CANCELLED"], errors="coerce").fillna(0.0)

    control = frame[frame["day"].isin(CONTROL_DAYS)]
    event = frame[frame["day"].isin(EVENT_DAYS)]

    control_stats = control.groupby("ORIGIN_AIRPORT_ID")["CANCELLED"].agg(["mean", "size"])
    event_stats = event.groupby("ORIGIN_AIRPORT_ID")["CANCELLED"].agg(["mean", "size"])

    merged = control_stats.join(event_stats, lsuffix="_control", rsuffix="_event", how="inner")
    merged = merged[merged["size_control"] >= MIN_CONTROL_FLIGHTS]

    return pd.DataFrame(
        {
            "airport_id": merged.index.astype(int),
            "control_rate": merged["mean_control"].to_numpy() * 100.0,
            "event_rate": merged["mean_event"].to_numpy() * 100.0,
            "delta": (merged["mean_event"] - merged["mean_control"]).to_numpy() * 100.0,
            "control_flights": merged["size_control"].astype(int).to_numpy(),
        }
    ).reset_index(drop=True)


def choose_seeds(observed: pd.DataFrame, count: int) -> list[int]:
    """The airports where the disruption originated, taken from the data itself.

    Ranked by absolute cancellation increase weighted by size, so a large airport with
    a big jump outranks a small one with a noisier jump.
    """
    scored = observed.assign(severity=observed["delta"] * np.log1p(observed["control_flights"]))
    return scored.nlargest(count, "severity")["airport_id"].astype(int).tolist()


def predict_exposure(snapshot_config: Path, seeds: list[int]) -> pd.DataFrame:
    """Two-hop ripple exposure from removing the seed airports simultaneously."""
    cfg = load_config(snapshot_config)
    graph = build_analysis_graph(load_edges(cfg))

    present = [airport for airport in seeds if graph.has_node(airport)]
    if not present:
        raise SystemExit("none of the seed airports appear in the baseline graph")

    _, exposure_rows = run_scenario(
        graph,
        snapshot_id=cfg.snapshot_id,
        scenario_type="airport_set_removal",
        payload={"airport_ids": present},
        created_at="1970-01-01T00:00:00Z",
    )
    predicted = pd.DataFrame(exposure_rows)
    # Airports the model predicts no exposure for still take part in the test; scoring
    # only the ones it flagged would grade the model on its own selection.
    return predicted[["airport_id", "exposure_score", "hop_level"]]


def _partial_spearman(
    first: np.ndarray, second: np.ndarray, control: np.ndarray
) -> tuple[float, float]:
    """Spearman correlation between ``first`` and ``second`` holding ``control`` fixed.

    Computed on ranks: regress each variable on the control, then correlate the
    residuals. This is what separates "exposure predicts damage" from "big airports
    have more of everything".
    """
    ranked = [stats.rankdata(values) for values in (first, second, control)]
    control_rank = np.column_stack([np.ones_like(ranked[2]), ranked[2]])

    residuals = []
    for values in ranked[:2]:
        coefficients, *_ = np.linalg.lstsq(control_rank, values, rcond=None)
        residuals.append(values - control_rank @ coefficients)

    result = stats.pearsonr(residuals[0], residuals[1])
    return float(result.statistic), float(result.pvalue)


def evaluate(observed: pd.DataFrame, predicted: pd.DataFrame, seeds: list[int]) -> dict:
    """Rank-correlate predicted exposure against observed degradation."""
    merged = observed.merge(predicted, on="airport_id", how="left")
    merged["exposure_score"] = merged["exposure_score"].fillna(0.0)

    # The seed airports are the cause, not the effect. Leaving them in would score the
    # model on having predicted that the airports we removed were disrupted.
    tested = merged[~merged["airport_id"].isin(seeds)].copy()

    spearman = stats.spearmanr(tested["exposure_score"], tested["delta"])
    pearson = stats.pearsonr(tested["exposure_score"], tested["delta"])

    exposed = tested[tested["exposure_score"] > 0]
    unexposed = tested[tested["exposure_score"] == 0]
    mann_whitney = (
        stats.mannwhitneyu(exposed["delta"], unexposed["delta"], alternative="greater")
        if len(exposed) and len(unexposed)
        else None
    )

    # The obvious confounder: large airports both attract more predicted exposure and
    # cancel more flights in any disruption. If the correlation is only size, it should
    # vanish once size is partialled out of both variables.
    size = np.log1p(tested["control_flights"].to_numpy())
    partial_rho, partial_p = _partial_spearman(
        tested["exposure_score"].to_numpy(), tested["delta"].to_numpy(), size
    )

    return {
        "tested": tested,
        "n": len(tested),
        "spearman_rho": spearman.statistic,
        "spearman_p": spearman.pvalue,
        "pearson_r": pearson.statistic,
        "pearson_p": pearson.pvalue,
        "exposed_n": len(exposed),
        "exposed_median": exposed["delta"].median() if len(exposed) else float("nan"),
        "unexposed_n": len(unexposed),
        "unexposed_median": unexposed["delta"].median() if len(unexposed) else float("nan"),
        "mann_whitney_p": mann_whitney.pvalue if mann_whitney else float("nan"),
        "partial_rho": partial_rho,
        "partial_p": partial_p,
        "size_rho": stats.spearmanr(size, tested["delta"]).statistic,
    }


def report(result: dict, seeds: list[int], codes: pd.Series) -> None:
    """Print the finding, whatever it is."""
    name = lambda airport: codes.get(airport, str(airport))  # noqa: E731

    print("\nSeed airports (disruption origin, chosen from observed data):")
    print("  " + ", ".join(name(a) for a in seeds))

    print(f"\nAirports tested: {result['n']} (seeds excluded)")
    print("\nDoes predicted exposure rank observed degradation?")
    print(f"  Spearman rho  {result['spearman_rho']:+.3f}   p = {result['spearman_p']:.2e}")
    print(f"  Pearson  r    {result['pearson_r']:+.3f}   p = {result['pearson_p']:.2e}")

    print("\nControlling for airport size (log control-period flights):")
    print(f"  partial rho   {result['partial_rho']:+.3f}   p = {result['partial_p']:.2e}")
    print(f"  size alone    {result['size_rho']:+.3f}   (size versus observed damage)")

    if result["unexposed_n"] == 0:
        print(
            "\nEvery tested airport received some exposure, so an exposed-versus-"
            "unexposed\n  split carries no information here; the rank correlation is "
            "the test."
        )
    else:
        print("\nExposed versus unexposed airports (median cancellation increase):")
        print(f"  exposed    n={result['exposed_n']:>3}   {result['exposed_median']:+.2f} pp")
        print(f"  unexposed  n={result['unexposed_n']:>3}   {result['unexposed_median']:+.2f} pp")
        print(f"  Mann-Whitney (exposed greater)  p = {result['mann_whitney_p']:.2e}")

    tested = result["tested"]
    print("\nTop 10 airports by predicted exposure:")
    print(f"  {'code':<6}{'exposure':>10}{'observed Δ':>13}")
    for _, row in tested.nlargest(10, "exposure_score").iterrows():
        print(
            f"  {name(int(row['airport_id'])):<6}"
            f"{row['exposure_score']:>10.2f}{row['delta']:>+12.2f}pp"
        )

    rho, partial = result["spearman_rho"], result["partial_rho"]
    strength = (
        "no measurable relationship" if result["spearman_p"] > 0.05
        else "weak but significant" if abs(rho) < 0.25
        else "moderate" if abs(rho) < 0.5
        else "strong"
    )
    print(f"\nVerdict: {strength} (rho = {rho:+.3f}).")
    if result["partial_p"] > 0.05:
        print(
            "  It does not survive controlling for airport size, so on this event the\n"
            "  relationship is explained by how big an airport is, not where it sits."
        )
    else:
        print(
            f"  It survives controlling for airport size (partial rho = {partial:+.3f}),\n"
            "  so exposure carries information beyond airport size alone."
        )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--config", type=Path, required=True,
        help="YAML config for the PRE-event snapshot used to build the graph",
    )
    parser.add_argument(
        "--event-on-time", type=Path, required=True,
        help="Raw BTS on-time CSV covering the event month",
    )
    parser.add_argument("--seeds", type=int, default=SEED_COUNT)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    observed = load_observed(args.event_on_time)
    seeds = choose_seeds(observed, args.seeds)
    predicted = predict_exposure(args.config, seeds)
    result = evaluate(observed, predicted, seeds)

    cfg = load_config(args.config)
    airports = pd.read_csv(cfg.processed_dir / "airports.csv")
    codes = airports.set_index("airport_id_canonical")["airport_code_raw"]

    report(result, seeds, codes)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
