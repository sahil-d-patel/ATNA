from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from metrics.config import load_config


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


def render_community_map(processed_dir: Path, *, out_path: Path, min_comm_size: int = 5) -> Path:
    df = _load_airports_metrics(processed_dir)
    df = _default_us_bbox_filter(df)

    # De-emphasize tiny communities.
    comm_sizes = df["leiden_community_id"].value_counts()
    df["is_tiny"] = df["leiden_community_id"].map(comm_sizes).fillna(0).astype(int) < int(min_comm_size)

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
    for is_tiny, alpha in [(True, 0.25), (False, 0.75)]:
        sub = df[df["is_tiny"] == is_tiny]
        if sub.empty:
            continue
        sc = ax.scatter(
            sub["longitude"],
            sub["latitude"],
            c=sub["leiden_community_id"],
            cmap="tab20",
            s=sub["marker_size"],
            alpha=alpha,
            linewidths=0,
        )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(out_path, dpi=200)
    plt.close(fig)
    return out_path


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

    out = (
        Path(args.out)
        if args.out is not None
        else (cfg.repo_root / "outputs" / "maps" / f"phase2_community_map_{snapshot}.png")
    )
    out_path = render_community_map(processed_dir, out_path=out, min_comm_size=args.min_comm_size)
    print(out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

