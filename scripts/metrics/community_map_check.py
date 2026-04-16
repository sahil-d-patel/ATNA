from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from metrics.config import load_config
from metrics.graph_builder import build_analysis_graph, load_edges
from metrics.tables import assert_metr02_nodes_match_graph, load_nodes


def _load_airports_metrics(processed_dir: Path) -> pd.DataFrame:
    airports = pd.read_csv(processed_dir / "airports.csv")
    metrics = pd.read_csv(processed_dir / "metrics.csv")

    # Phase 1 emits airports.csv with airport_id_canonical as the join key.
    join_key = "airport_id_canonical" if "airport_id_canonical" in airports.columns else "airport_id"
    need_a = {join_key, "latitude", "longitude"}
    if not need_a.issubset(airports.columns):
        raise ValueError(f"airports.csv missing required columns: {sorted(need_a - set(airports.columns))}")

    need_m = {"airport_id", "leiden_community_id"}
    if not need_m.issubset(metrics.columns):
        raise ValueError(f"metrics.csv missing required columns: {sorted(need_m - set(metrics.columns))}")

    size_col = "strength_total" if "strength_total" in metrics.columns else "hub_score"
    if size_col not in metrics.columns:
        raise ValueError("metrics.csv must include strength_total or hub_score for marker sizing")

    df = (
        airports[[join_key, "latitude", "longitude"]]
        .merge(
            metrics[["airport_id", "leiden_community_id", size_col]],
            left_on=join_key,
            right_on="airport_id",
            how="inner",
        )
        .rename(columns={size_col: "size_metric"})
    )
    if join_key != "airport_id":
        df = df.drop(columns=[join_key])
    df["airport_id"] = pd.to_numeric(df["airport_id"], errors="raise").astype(int)
    df["leiden_community_id"] = pd.to_numeric(df["leiden_community_id"], errors="raise").astype(int)
    df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
    df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
    df = df.dropna(subset=["latitude", "longitude"]).reset_index(drop=True)
    return df


def _default_us_bbox_filter(df: pd.DataFrame) -> pd.DataFrame:
    # Lower 48 + AK/HI broad bbox (smoke test; not a cartographic projection).
    return df[
        (df["latitude"].between(18, 72))
        & (df["longitude"].between(-170, -60))
    ].copy()


def _canonical_display_labels(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Map Leiden IDs to stable display labels by descending community size.

    This does not change source IDs in metrics.csv; it only stabilizes rendering labels
    (`C01`, `C02`, ...) for easier cross-run audits and screenshot comparison.
    """
    agg = (
        df.groupby("leiden_community_id", as_index=False)["airport_id"]
        .count()
        .rename(columns={"airport_id": "community_size"})
    )
    min_airport = (
        df.groupby("leiden_community_id", as_index=False)["airport_id"]
        .min()
        .rename(columns={"airport_id": "min_airport_id"})
    )
    legend = agg.merge(min_airport, on="leiden_community_id", how="left")
    legend = legend.sort_values(
        by=["community_size", "min_airport_id", "leiden_community_id"],
        ascending=[False, True, True],
        kind="mergesort",
    ).reset_index(drop=True)
    legend["display_rank"] = np.arange(1, len(legend) + 1, dtype=int)
    legend["display_label"] = legend["display_rank"].map(lambda x: f"C{x:02d}")
    label_map = dict(zip(legend["leiden_community_id"], legend["display_label"]))
    out = df.copy()
    out["display_label"] = out["leiden_community_id"].map(label_map)
    return out, legend


def _write_legend_artifact(df: pd.DataFrame, legend: pd.DataFrame, out_csv: Path) -> Path:
    top_ids = (
        df.groupby("leiden_community_id")["airport_id"]
        .apply(lambda s: ",".join(str(v) for v in s.astype(int).head(8).tolist()))
        .rename("sample_airport_ids")
        .reset_index()
    )
    out = legend.merge(top_ids, on="leiden_community_id", how="left")
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(out_csv, index=False)
    return out_csv


def _write_validation_metrics(processed_dir: Path, snapshot: str, out_json: Path) -> Path:
    metrics = pd.read_csv(processed_dir / "metrics.csv")
    routes = pd.read_csv(processed_dir / "route_metrics.csv")

    flags = pd.to_numeric(routes["cross_community_flag"], errors="coerce")
    valid = flags.notna()
    cross_share = float((flags[valid] == 100).mean()) if valid.any() else float("nan")

    metr02_ok = True
    metr02_message = "passed"
    try:
        cfg = load_config()
        edges = load_edges(cfg)
        nodes = load_nodes(cfg)
        g = build_analysis_graph(edges)
        g.add_nodes_from(nodes["airport_id"].astype(int).tolist())
        assert_metr02_nodes_match_graph(g, nodes)
    except Exception as exc:  # noqa: BLE001
        metr02_ok = False
        metr02_message = str(exc)

    payload = {
        "snapshot_id": snapshot,
        "airport_count_metrics": int(metrics["airport_id"].nunique()),
        "route_count": int(len(routes)),
        "cross_community_route_share": cross_share,
        "cross_community_route_count": int((flags[valid] == 100).sum()) if valid.any() else 0,
        "metr02_reconciliation_passed": metr02_ok,
        "metr02_message": metr02_message,
    }
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return out_json


def render_community_map(
    processed_dir: Path,
    *,
    out_path: Path,
    legend_path: Path,
    validation_path: Path,
    snapshot: str,
    min_comm_size: int = 5,
) -> tuple[Path, Path, Path]:
    df = _load_airports_metrics(processed_dir)
    df = _default_us_bbox_filter(df)
    df, legend = _canonical_display_labels(df)

    # De-emphasize tiny communities.
    comm_sizes = df["display_label"].value_counts()
    df["is_tiny"] = df["display_label"].map(comm_sizes).fillna(0).astype(int) < int(min_comm_size)

    # Scale marker sizes reasonably.
    x = df["size_metric"].astype(float)
    if x.notna().any():
        q = x.quantile([0.05, 0.95]).to_dict()
        lo, hi = float(q.get(0.05, x.min())), float(q.get(0.95, x.max()))
        denom = (hi - lo) if hi > lo else 1.0
        s = ((x.clip(lo, hi) - lo) / denom) * 60.0 + 6.0
    else:
        s = 10.0

    df = df.assign(marker_size=s)

    fig, ax = plt.subplots(figsize=(12, 7))
    ax.set_title(f"Leiden communities (snapshot dir: {processed_dir.name})")
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")

    # Plot tiny communities first with lower alpha.
    label_to_rank = {lbl: i for i, lbl in enumerate(sorted(df["display_label"].dropna().unique()))}
    color_values = df["display_label"].map(label_to_rank).astype(float)

    for is_tiny, alpha in [(True, 0.25), (False, 0.75)]:
        sub = df[df["is_tiny"] == is_tiny]
        if sub.empty:
            continue
        ax.scatter(
            sub["longitude"],
            sub["latitude"],
            c=color_values.loc[sub.index],
            cmap="tab20",
            s=sub["marker_size"],
            alpha=alpha,
            linewidths=0,
        )

    # Inline legend for largest communities to make audits possible directly from image.
    top_legend = legend.head(8).copy()
    legend_lines = [
        f"{row.display_label} -> raw {int(row.leiden_community_id)} (n={int(row.community_size)})"
        for row in top_legend.itertuples(index=False)
    ]
    ax.text(
        1.01,
        0.98,
        "Top communities\n" + "\n".join(legend_lines),
        transform=ax.transAxes,
        va="top",
        fontsize=8,
        bbox={"facecolor": "white", "alpha": 0.8, "edgecolor": "gray"},
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(out_path, dpi=200)
    plt.close(fig)
    legend_written = _write_legend_artifact(df, legend, legend_path)
    validation_written = _write_validation_metrics(processed_dir, snapshot, validation_path)
    return out_path, legend_written, validation_written


def main() -> int:
    p = argparse.ArgumentParser(description="Phase 2 community map smoke check.")
    p.add_argument("--snapshot", default=None, help="snapshot_id (defaults to config/atna.yaml snapshot_id)")
    p.add_argument("--out", default=None, help="output PNG path (default outputs/maps/phase2_community_map_<snapshot>.png)")
    p.add_argument("--min-comm-size", type=int, default=5, help="communities smaller than this are de-emphasized")
    args = p.parse_args()

    cfg = load_config()
    snapshot = str(args.snapshot) if args.snapshot is not None else str(cfg.snapshot_id)
    processed_dir = cfg.repo_root / "data" / "processed" / snapshot
    if not processed_dir.is_dir():
        raise FileNotFoundError(f"processed snapshot directory not found: {processed_dir}")

    map_out = (
        Path(args.out)
        if args.out is not None
        else (cfg.repo_root / "outputs" / "maps" / f"phase2_community_map_{snapshot}.png")
    )
    legend_out = cfg.repo_root / "outputs" / "maps" / f"phase2_community_legend_{snapshot}.csv"
    validation_out = cfg.repo_root / "outputs" / "maps" / f"phase2_validation_metrics_{snapshot}.json"
    map_path, legend_path, validation_path = render_community_map(
        processed_dir,
        out_path=map_out,
        legend_path=legend_out,
        validation_path=validation_out,
        snapshot=snapshot,
        min_comm_size=args.min_comm_size,
    )
    print(map_path)
    print(legend_path)
    print(validation_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

