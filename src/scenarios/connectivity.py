"""Batch connectivity counts for airport-removal sweeps.

Scoring a scenario needs exactly two integers from the post-removal graph: the size of
the largest weakly connected component, and the number of ordered reachable pairs. The
reference implementations in :mod:`scenarios.scoring` derive both from NetworkX, which
is the right choice for a single scenario.

A vulnerability sweep is a different problem. It removes every airport in turn, so the
per-scenario NetworkX passes are repeated ``V`` times over a graph that is otherwise
unchanged. :class:`ConnectivityIndex` builds the edge arrays once and answers each
removal from SciPy's compiled connected-components routines, which avoids rebuilding
Python-level graph objects inside the loop.

Both counts are integers, so downstream float arithmetic is bit-identical to the
reference path. ``tests/test_connectivity_index.py`` pins that equivalence.
"""

from __future__ import annotations

from dataclasses import dataclass

import networkx as nx
import numpy as np
from scipy.sparse import csr_array
from scipy.sparse.csgraph import connected_components


@dataclass(frozen=True)
class ConnectivityCounts:
    """Largest weakly connected component size and reachable ordered pair count."""

    lcc_size: int
    reachable_pairs: int


class ConnectivityIndex:
    """Precomputed edge arrays supporting fast single-airport removal queries.

    Construction is ``O(V + E)``. Each query is one boolean mask over the edge arrays
    plus two SciPy component passes, with a bitset union over the SCC condensation only
    when the remaining graph is not already strongly connected.
    """

    def __init__(self, graph: nx.DiGraph) -> None:
        if not isinstance(graph, nx.DiGraph):
            raise TypeError("graph must be a networkx.DiGraph")

        self._nodes: list[int] = [int(node) for node in graph.nodes()]
        self._position: dict[int, int] = {node: i for i, node in enumerate(self._nodes)}
        self._order = len(self._nodes)

        if graph.number_of_edges():
            sources, targets = zip(
                *((self._position[int(u)], self._position[int(v)]) for u, v in graph.edges()),
                strict=True,
            )
        else:
            sources, targets = (), ()
        self._sources = np.fromiter(sources, dtype=np.int32, count=len(sources))
        self._targets = np.fromiter(targets, dtype=np.int32, count=len(targets))

    @property
    def nodes(self) -> list[int]:
        """Airport ids in the index's internal order."""
        return list(self._nodes)

    def without_airport(self, airport_id: int) -> ConnectivityCounts:
        """Connectivity counts for the graph with ``airport_id`` removed."""
        node = int(airport_id)
        if node not in self._position:
            raise ValueError(f"airport {node} is not present in the index")

        dropped = self._position[node]
        keep = (self._sources != dropped) & (self._targets != dropped)
        # Removing one node shifts every higher index down by one, keeping the
        # remaining labels contiguous in 0..order-2 as csr_array requires.
        sources = self._sources[keep]
        targets = self._targets[keep]
        sources = sources - (sources > dropped)
        targets = targets - (targets > dropped)

        return _counts_from_edges(sources, targets, self._order - 1)


def _counts_from_edges(
    sources: np.ndarray, targets: np.ndarray, order: int
) -> ConnectivityCounts:
    """Compute both connectivity counts for a directed graph given as edge arrays."""
    if order <= 0:
        return ConnectivityCounts(lcc_size=0, reachable_pairs=0)

    adjacency = csr_array(
        (np.ones(sources.shape[0], dtype=bool), (sources, targets)),
        shape=(order, order),
    )

    _, weak_labels = connected_components(adjacency, directed=True, connection="weak")
    lcc_size = int(np.bincount(weak_labels).max())

    component_count, strong_labels = connected_components(
        adjacency, directed=True, connection="strong"
    )
    if component_count == 1:
        # One strongly connected component: every ordered pair is reachable.
        return ConnectivityCounts(lcc_size=lcc_size, reachable_pairs=order * (order - 1))

    component_sizes = np.bincount(strong_labels, minlength=component_count)
    reachable_pairs = _condensation_reachable_pairs(
        strong_labels, component_sizes, sources, targets, component_count
    )
    return ConnectivityCounts(lcc_size=lcc_size, reachable_pairs=int(reachable_pairs))


def _condensation_reachable_pairs(
    strong_labels: np.ndarray,
    component_sizes: np.ndarray,
    sources: np.ndarray,
    targets: np.ndarray,
    component_count: int,
) -> int:
    """Sum reachable ordered pairs over the SCC condensation.

    Mirrors :func:`scenarios.scoring.reachable_pairs_count`: a reverse-topological
    bitset union over the condensation DAG, then ``|C| * (reachable nodes - 1)``
    summed across components.
    """
    source_components = strong_labels[sources]
    target_components = strong_labels[targets]
    crossing = source_components != target_components

    condensation = nx.DiGraph()
    condensation.add_nodes_from(range(component_count))
    condensation.add_edges_from(
        zip(
            source_components[crossing].tolist(),
            target_components[crossing].tolist(),
            strict=True,
        )
    )

    sizes = [int(size) for size in component_sizes]
    reachable_mask = [0] * component_count
    for component in reversed(list(nx.topological_sort(condensation))):
        mask = 1 << component
        for successor in condensation.successors(component):
            mask |= reachable_mask[successor]
        reachable_mask[component] = mask

    total = 0
    for component, mask in enumerate(reachable_mask):
        reached = 0
        remaining = mask
        while remaining:
            lowest_bit = remaining & -remaining
            reached += sizes[lowest_bit.bit_length() - 1]
            remaining ^= lowest_bit
        total += sizes[component] * (reached - 1)
    return total
