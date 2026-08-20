"""Typed scenario payloads and normalized edit metadata."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ScenarioType(str, Enum):
    AIRPORT_REMOVAL = "airport_removal"
    AIRPORT_SET_REMOVAL = "airport_set_removal"
    ROUTE_REMOVAL = "route_removal"


@dataclass(frozen=True)
class AirportRemovalPayload:
    """Payload for airport-removal scenarios."""

    airport_id: int

    def __post_init__(self) -> None:
        if not isinstance(self.airport_id, int):
            raise TypeError("airport_id must be an integer")


@dataclass(frozen=True)
class AirportSetRemovalPayload:
    """Payload for removing several airports in one scenario.

    A correlated outage rarely takes out exactly one airport: a carrier collapse or a
    regional weather system degrades a set at once, and the combined effect is not the
    sum of the individual ones.
    """

    airport_ids: tuple[int, ...]

    def __post_init__(self) -> None:
        if not self.airport_ids:
            raise ValueError("airport_ids must contain at least one airport")
        if not all(isinstance(value, int) for value in self.airport_ids):
            raise TypeError("every airport_id must be an integer")
        if len(set(self.airport_ids)) != len(self.airport_ids):
            raise ValueError("airport_ids must not repeat an airport")


@dataclass(frozen=True)
class RouteRemovalPayload:
    """Payload for route-removal scenarios."""

    origin_id: int
    destination_id: int

    def __post_init__(self) -> None:
        if not isinstance(self.origin_id, int) or not isinstance(self.destination_id, int):
            raise TypeError("origin_id and destination_id must be integers")
        if self.origin_id == self.destination_id:
            raise ValueError("origin_id and destination_id must be different airports")


@dataclass(frozen=True)
class ScenarioEditResult:
    """Normalized edit result metadata returned by graph edit primitives."""

    scenario_type: ScenarioType
    snapshot_id: str | None
    removed_airport_id: int | None
    removed_origin_id: int | None
    removed_destination_id: int | None
    removed_airport_ids: tuple[int, ...] = ()
