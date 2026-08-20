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

from scenarios.scoring import node_strengths


@dataclass(frozen=True)
class ConnectivityCounts:
    """Traffic in the largest weakly connected component, and the weighted reach total.

    Both are traffic totals rather than counts (spec §9.1, §9.2).
    """

    lcc_size: float
    reachable_pairs: float


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

        # Strength is a property of the baseline: removing one airport does not change
        # the traffic at the airports that remain, so this is computed once.
        strengths = node_strengths(graph)
        self._strengths = np.array(
            [float(strengths.get(node, 0.0)) for node in self._nodes], dtype=float
        )

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
        strengths = np.delete(self._strengths, dropped)

        return _counts_from_edges(sources, targets, self._order - 1, strengths)


def _counts_from_edges(
    sources: np.ndarray, targets: np.ndarray, order: int, strengths: np.ndarray
) -> ConnectivityCounts:
    """Compute both connectivity measures for a directed graph given as edge arrays."""
    if order <= 0:
        return ConnectivityCounts(lcc_size=0.0, reachable_pairs=0.0)

    adjacency = csr_array(
        (np.ones(sources.shape[0], dtype=bool), (sources, targets)),
        shape=(order, order),
    )

    _, weak_labels = connected_components(adjacency, directed=True, connection="weak")
    lcc_size = float(np.bincount(weak_labels, weights=strengths).max())

    component_count, strong_labels = connected_components(
        adjacency, directed=True, connection="strong"
    )
    if component_count == 1:
        # One strongly connected component: every ordered pair is reachable, so the
        # weighted total is the square of the strength sum less the self pairs.
        total = float(strengths.sum() ** 2 - (strengths**2).sum())
        return ConnectivityCounts(lcc_size=lcc_size, reachable_pairs=total)

    weighted = _condensation_weighted_reach(
        strong_labels, strengths, sources, targets, component_count
    )
    return ConnectivityCounts(lcc_size=lcc_size, reachable_pairs=float(weighted))


def _condensation_weighted_reach(
    strong_labels: np.ndarray,
    strengths: np.ndarray,
    sources: np.ndarray,
    targets: np.ndarray,
    component_count: int,
) -> float:
    """Sum traffic-weighted reachable pairs over the SCC condensation.

    Mirrors :func:`scenarios.scoring.weighted_reach`: a reverse-topological bitset
    union over the condensation DAG, then ``S_C * S_reach(C)`` less the excluded
    self pairs, summed across components.
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

    component_strength = np.bincount(
        strong_labels, weights=strengths, minlength=component_count
    )
    component_square = np.bincount(
        strong_labels, weights=strengths**2, minlength=component_count
    )
    reachable_mask = [0] * component_count
    for component in reversed(list(nx.topological_sort(condensation))):
        mask = 1 << component
        for successor in condensation.successors(component):
            mask |= reachable_mask[successor]
        reachable_mask[component] = mask

    total = 0.0
    for component, mask in enumerate(reachable_mask):
        reached = 0.0
        remaining = mask
        while remaining:
            lowest_bit = remaining & -remaining
            reached += float(component_strength[lowest_bit.bit_length() - 1])
            remaining ^= lowest_bit
        total += float(component_strength[component]) * reached - float(component_square[component])
    return total
