"""ETL package: raw → interim/processed canonical tables.

Only names that do not collide with a submodule are re-exported here. Binding a
function named ``build_airports`` at package level would replace the
``etl.build_airports`` *module* attribute with the function, so
``import etl.build_airports as m; m.write_airports_csv`` would fail with a confusing
``AttributeError``. Stage entrypoints are imported from their modules directly:

    from etl.build_airports import build_airports
"""

from etl.build_airports import AIRPORTS_COLUMNS, build_airports_table, write_airports_csv
from etl.build_edges import EDGES_COLUMNS, build_edges_table, write_edges_csv
from etl.build_nodes import NODES_COLUMNS, build_nodes_table, write_nodes_csv
from etl.config import AtnaConfig, load_config, validate_paths
from etl.load_raw import (
    assert_raw_files_exist,
    load_master,
    load_on_time,
    load_on_time_us_domestic,
    load_t100,
    load_t100_us_domestic,
)

__all__ = [
    "AIRPORTS_COLUMNS",
    "EDGES_COLUMNS",
    "NODES_COLUMNS",
    "AtnaConfig",
    "assert_raw_files_exist",
    "build_airports_table",
    "build_edges_table",
    "build_nodes_table",
    "load_config",
    "load_master",
    "load_on_time",
    "load_on_time_us_domestic",
    "load_t100",
    "load_t100_us_domestic",
    "validate_paths",
    "write_airports_csv",
    "write_edges_csv",
    "write_nodes_csv",
]
