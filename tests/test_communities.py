from __future__ import annotations

import pandas as pd
import networkx as nx

from metrics.leiden_communities import compute_leiden_communities


def test_leiden_partition_covers_all_nodes():
    # Skip if optional deps are not installed in the current environment.
    try:
        import igraph  # noqa: F401
        import leidenalg  # noqa: F401
    except Exception:
        return

    g = nx.DiGraph()
    g.add_edge(1, 2, weight=1.0)
    g.add_edge(2, 3, weight=1.0)
    g.add_node(4)  # isolated

    airport_to_comm = compute_leiden_communities(g)
    assert set(airport_to_comm.keys()) == {1, 2, 3, 4}
    assert all(isinstance(v, int) and v >= 0 for v in airport_to_comm.values())

