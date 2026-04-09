"""Typed scenario payloads and normalized edit metadata."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ScenarioType(str, Enum):
    AIRPORT_REMOVAL = "airport_removal"
    ROUTE_REMOVAL = "route_removal"


@dataclass(frozen=True)
class AirportRemovalPayload:
    """Payload for airport-removal scenarios."""

    airport_id: int

    def __post_init__(self) -> None:
        if not isinstance(self.airport_id, int):
            raise TypeError("airport_id must be an integer")


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
class ScenarioRequest:
    """Stable scenario request metadata for deterministic execution."""

    snapshot_id: str
    scenario_type: ScenarioType
    target_airport_id: int | None = None
    target_origin_id: int | None = None
    target_destination_id: int | None = None


@dataclass(frozen=True)
class ScenarioEditResult:
    """Normalized edit result metadata returned by graph edit primitives."""

    scenario_type: ScenarioType
    snapshot_id: str | None
    removed_airport_id: int | None
    removed_origin_id: int | None
    removed_destination_id: int | None
