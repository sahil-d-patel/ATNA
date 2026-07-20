"""Single entrypoint: raw BTS inputs → ``airports.csv``, ``edges.csv``, ``nodes.csv``."""

from __future__ import annotations

import argparse
from pathlib import Path

from etl.build_airports import build_airports_table, write_airports_csv
from etl.build_edges import build_edges_table, write_edges_csv
from etl.build_nodes import build_nodes
from etl.config import DEFAULT_CONFIG_PATH, load_config, validate_paths
from etl.load_raw import load_master, load_on_time_us_domestic


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
    # Parse each raw input exactly once per run and share the frames across builders.
    # The on-time extract dominates ETL wall time, and both the airports and edges
    # builders need the same U.S. domestic slice of it.
    master = load_master(cfg)
    on_time_us = load_on_time_us_domestic(cfg, master=master)

    write_airports_csv(cfg, build_airports_table(cfg, master=master, on_time_us=on_time_us))
    edges = build_edges_table(cfg, master=master, on_time_us=on_time_us)
    write_edges_csv(cfg, edges)
    # Reuse the in-memory edges frame rather than reading edges.csv back off disk.
    build_nodes(cfg, edges=edges)
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
