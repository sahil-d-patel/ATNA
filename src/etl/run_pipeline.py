"""Single entrypoint: raw BTS inputs → ``airports.csv``, ``edges.csv``, ``nodes.csv``."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from etl.build_airports import build_airports_table, write_airports_csv
from etl.build_edges import build_edges_table, write_edges_csv
from etl.build_nodes import build_nodes
from etl.config import DEFAULT_CONFIG_PATH, load_config, validate_paths
from etl.load_raw import load_master


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Run ATNA MVP ETL: airports → edges → nodes for snapshot in config."
    )
    p.add_argument(
        "--config",
        type=Path,
        default=None,
        metavar="PATH",
        help=f"YAML config (default: {DEFAULT_CONFIG_PATH})",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    cfg = load_config(args.config)
    validate_paths(cfg)
    # Load the master coordinate table once and share it across builders so the
    # raw CSV is parsed a single time per pipeline run.
    master = load_master(cfg)
    write_airports_csv(cfg, build_airports_table(cfg, master=master))
    write_edges_csv(cfg, build_edges_table(cfg, master=master))
    build_nodes(cfg)
    print(
        f"ETL complete for snapshot {cfg.snapshot_id!r}:",
        cfg.processed_dir / "airports.csv",
        cfg.processed_dir / "edges.csv",
        cfg.processed_dir / "nodes.csv",
        sep="\n  ",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
