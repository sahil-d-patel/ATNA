"""Generate a synthetic BTS-shaped raw dataset so ATNA runs without a real download.

The BTS TranStats extracts under ``data/raw/`` are large, rate-limited, and not
redistributable, which makes a fresh clone unrunnable until someone completes the
full download. This script writes raw CSVs with the **same schema** the real BTS
files use, so the unmodified ETL → metrics → scenarios pipeline consumes them
exactly as it consumes production data.

What is real and what is not:

* **Real** — airport identifiers, IATA codes, city/state, and latitude/longitude
  for the 50 busiest U.S. airports. The map and airport tables therefore show
  true geography, and Leiden communities fall out along genuine regional lines.
* **Synthetic** — every flight, passenger, seat, and delay figure. Traffic is
  sampled from a gravity model (hub mass over great-circle distance), so the
  network has believable hubs, spokes, and cross-country bridges, but no row
  corresponds to a real flight.

Output is deterministic for a given ``--seed``, so demo screenshots, artifact
checksums, and test fixtures stay reproducible across machines.

Usage::

    PYTHONPATH=src python scripts/demo/generate_demo_data.py
    PYTHONPATH=src python scripts/demo/generate_demo_data.py --seed 7 --force
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from etl.config import AtnaConfig, load_config

EARTH_RADIUS_MI = 3958.8

# Gravity-model tuning, calibrated so the month lands near 400k flight legs across
# ~1000 directed routes — the same order of magnitude a real BTS month shows for
# airports of this size.
GRAVITY_SCALE = 2.4e6
DISTANCE_EXPONENT = 1.20
MIN_ROUTE_FLIGHTS = 30

# U.S. domestic service is hub-and-spoke, not point-to-point: two small airports rarely
# get a nonstop unless they are regional neighbors. Without this gate a pure gravity
# model produces an implausibly complete graph, and Leiden collapses the whole country
# into a couple of communities instead of resolving regional structure.
HUB_MASS_THRESHOLD = 0.50
REGIONAL_NONSTOP_MILES = 450.0
SEATS_PER_FLIGHT = 150
LOAD_FACTOR_RANGE = (0.68, 0.92)
CANCELLATION_RATE = 0.017
DIVERSION_RATE = 0.002

# Per-airport delay bias (minutes) is drawn from this range, so congested hubs stay
# congested across the whole month instead of averaging out to a single global mean.
DELAY_BIAS_RANGE = (-4.0, 11.0)
DELAY_SPREAD_MIN = 28.0


@dataclass(frozen=True)
class Airport:
    """One row of the master coordinate reference.

    ``mass`` is the gravity-model weight: roughly proportional to real annual
    enplanements, normalized so ATL sits at 1.0.
    """

    airport_id: int
    code: str
    name: str
    city: str
    state: str
    latitude: float
    longitude: float
    utc_offset: int
    mass: float


# DOT airport IDs, codes, and coordinates are real; `mass` approximates relative
# enplanement volume and drives synthetic traffic only.
AIRPORTS: tuple[Airport, ...] = (
    Airport(10397, "ATL", "Hartsfield-Jackson Atlanta International", "Atlanta, GA", "GA", 33.6367, -84.4281, -5, 1.00),
    Airport(11298, "DFW", "Dallas/Fort Worth International", "Dallas/Fort Worth, TX", "TX", 32.8968, -97.0380, -6, 0.87),
    Airport(11292, "DEN", "Denver International", "Denver, CO", "CO", 39.8617, -104.6732, -7, 0.85),
    Airport(12892, "LAX", "Los Angeles International", "Los Angeles, CA", "CA", 33.9425, -118.4081, -8, 0.83),
    Airport(13930, "ORD", "Chicago O'Hare International", "Chicago, IL", "IL", 41.9786, -87.9048, -6, 0.82),
    Airport(12889, "LAS", "Harry Reid International", "Las Vegas, NV", "NV", 36.0801, -115.1522, -8, 0.62),
    Airport(11057, "CLT", "Charlotte Douglas International", "Charlotte, NC", "NC", 35.2140, -80.9431, -5, 0.60),
    Airport(13487, "MSP", "Minneapolis-St Paul International", "Minneapolis, MN", "MN", 44.8820, -93.2218, -6, 0.44),
    Airport(14771, "SFO", "San Francisco International", "San Francisco, CA", "CA", 37.6188, -122.3750, -8, 0.58),
    Airport(14747, "SEA", "Seattle/Tacoma International", "Seattle, WA", "WA", 47.4490, -122.3093, -8, 0.57),
    Airport(13204, "MCO", "Orlando International", "Orlando, FL", "FL", 28.4294, -81.3089, -5, 0.61),
    Airport(12266, "IAH", "George Bush Intercontinental", "Houston, TX", "TX", 29.9844, -95.3414, -6, 0.56),
    Airport(12478, "JFK", "John F Kennedy International", "New York, NY", "NY", 40.6398, -73.7789, -5, 0.55),
    Airport(11618, "EWR", "Newark Liberty International", "Newark, NJ", "NJ", 40.6925, -74.1687, -5, 0.48),
    Airport(11433, "DTW", "Detroit Metro Wayne County", "Detroit, MI", "MI", 42.2124, -83.3534, -5, 0.42),
    Airport(14107, "PHX", "Phoenix Sky Harbor International", "Phoenix, AZ", "AZ", 33.4343, -112.0116, -7, 0.59),
    Airport(13303, "MIA", "Miami International", "Miami, FL", "FL", 25.7932, -80.2906, -5, 0.51),
    Airport(10721, "BOS", "Logan International", "Boston, MA", "MA", 42.3643, -71.0052, -5, 0.50),
    Airport(11697, "FLL", "Fort Lauderdale-Hollywood International", "Fort Lauderdale, FL", "FL", 26.0726, -80.1527, -5, 0.42),
    Airport(14100, "PHL", "Philadelphia International", "Philadelphia, PA", "PA", 39.8721, -75.2411, -5, 0.38),
    Airport(12953, "LGA", "LaGuardia", "New York, NY", "NY", 40.7772, -73.8726, -5, 0.36),
    Airport(10821, "BWI", "Baltimore/Washington International", "Baltimore, MD", "MD", 39.1754, -76.6683, -5, 0.36),
    Airport(14869, "SLC", "Salt Lake City International", "Salt Lake City, UT", "UT", 40.7884, -111.9778, -7, 0.40),
    Airport(14679, "SAN", "San Diego International", "San Diego, CA", "CA", 32.7336, -117.1897, -8, 0.37),
    Airport(12264, "IAD", "Washington Dulles International", "Washington, DC", "VA", 38.9445, -77.4558, -5, 0.32),
    Airport(11278, "DCA", "Ronald Reagan Washington National", "Washington, DC", "VA", 38.8521, -77.0377, -5, 0.32),
    Airport(13232, "MDW", "Chicago Midway International", "Chicago, IL", "IL", 41.7868, -87.7522, -6, 0.29),
    Airport(15304, "TPA", "Tampa International", "Tampa, FL", "FL", 27.9755, -82.5332, -5, 0.33),
    Airport(14057, "PDX", "Portland International", "Portland, OR", "OR", 45.5887, -122.5975, -8, 0.28),
    Airport(12173, "HNL", "Daniel K Inouye International", "Honolulu, HI", "HI", 21.3187, -157.9224, -10, 0.31),
    Airport(15016, "STL", "St Louis Lambert International", "St Louis, MO", "MO", 38.7487, -90.3700, -6, 0.24),
    Airport(10693, "BNA", "Nashville International", "Nashville, TN", "TN", 36.1245, -86.6782, -6, 0.32),
    Airport(10423, "AUS", "Austin-Bergstrom International", "Austin, TX", "TX", 30.1975, -97.6664, -6, 0.30),
    Airport(13796, "OAK", "Oakland International", "Oakland, CA", "CA", 37.7213, -122.2207, -8, 0.19),
    Airport(13495, "MSY", "Louis Armstrong New Orleans International", "New Orleans, LA", "LA", 29.9934, -90.2581, -6, 0.20),
    Airport(14492, "RDU", "Raleigh-Durham International", "Raleigh/Durham, NC", "NC", 35.8776, -78.7875, -5, 0.24),
    Airport(14893, "SMF", "Sacramento International", "Sacramento, CA", "CA", 38.6954, -121.5908, -8, 0.20),
    Airport(14831, "SJC", "Norman Y Mineta San Jose International", "San Jose, CA", "CA", 37.3626, -121.9291, -8, 0.20),
    Airport(14908, "SNA", "John Wayne Airport", "Santa Ana, CA", "CA", 33.6757, -117.8682, -8, 0.19),
    Airport(13198, "MCI", "Kansas City International", "Kansas City, MO", "MO", 39.2976, -94.7139, -6, 0.21),
    Airport(11042, "CLE", "Cleveland Hopkins International", "Cleveland, OH", "OH", 41.4117, -81.8498, -5, 0.17),
    Airport(14122, "PIT", "Pittsburgh International", "Pittsburgh, PA", "PA", 40.4915, -80.2329, -5, 0.17),
    Airport(12339, "IND", "Indianapolis International", "Indianapolis, IN", "IN", 39.7173, -86.2944, -5, 0.17),
    Airport(11193, "CVG", "Cincinnati/Northern Kentucky International", "Cincinnati, OH", "KY", 39.0489, -84.6678, -5, 0.16),
    Airport(11109, "CMH", "John Glenn Columbus International", "Columbus, OH", "OH", 39.9980, -82.8919, -5, 0.16),
    Airport(13342, "MKE", "General Mitchell International", "Milwaukee, WI", "WI", 42.9472, -87.8966, -6, 0.14),
    Airport(14683, "SAT", "San Antonio International", "San Antonio, TX", "TX", 29.5337, -98.4698, -6, 0.17),
    Airport(12451, "JAX", "Jacksonville International", "Jacksonville, FL", "FL", 30.4941, -81.6879, -5, 0.14),
    Airport(10299, "ANC", "Ted Stevens Anchorage International", "Anchorage, AK", "AK", 61.1743, -149.9962, -9, 0.12),
    Airport(10140, "ABQ", "Albuquerque International Sunport", "Albuquerque, NM", "NM", 35.0402, -106.6091, -7, 0.13),
)


def great_circle_miles(lat1: np.ndarray, lon1: np.ndarray, lat2: np.ndarray, lon2: np.ndarray) -> np.ndarray:
    """Vectorized haversine distance in statute miles."""
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dphi = p2 - p1
    dlambda = np.radians(lon2 - lon1)
    a = np.sin(dphi / 2.0) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dlambda / 2.0) ** 2
    return 2.0 * EARTH_RADIUS_MI * np.arcsin(np.sqrt(np.clip(a, 0.0, 1.0)))


def build_master_frame() -> pd.DataFrame:
    """Master coordinate reference in BTS column layout."""
    return pd.DataFrame(
        {
            "AIRPORT_SEQ_ID": [a.airport_id * 100 + 1 for a in AIRPORTS],
            "AIRPORT_ID": [a.airport_id for a in AIRPORTS],
            "CITY_MARKET_ID": [30000 + idx for idx, _ in enumerate(AIRPORTS)],
            "AIRPORT": [a.code for a in AIRPORTS],
            "DISPLAY_AIRPORT_NAME": [a.name for a in AIRPORTS],
            "DISPLAY_AIRPORT_CITY_NAME_FULL": [a.city for a in AIRPORTS],
            "AIRPORT_STATE_CODE": [a.state for a in AIRPORTS],
            "AIRPORT_COUNTRY_CODE_ISO": ["US"] * len(AIRPORTS),
            "AIRPORT_COUNTRY_NAME": ["United States"] * len(AIRPORTS),
            "LATITUDE": [a.latitude for a in AIRPORTS],
            "LONGITUDE": [a.longitude for a in AIRPORTS],
            "UTC_LOCAL_TIME_VARIATION": [f"{a.utc_offset * 100:05d}" for a in AIRPORTS],
            "AIRPORT_IS_CLOSED": [0] * len(AIRPORTS),
            # Real master coordinate files carry one row per airport per validity
            # window; the app keeps only the current row. One row per airport here,
            # so every row is the latest.
            "AIRPORT_IS_LATEST": [1] * len(AIRPORTS),
        }
    )


def build_route_frame(rng: np.random.Generator) -> pd.DataFrame:
    """Directed routes with a gravity-model monthly flight count.

    Flights scale as ``mass_o * mass_d / distance ** DISTANCE_EXPONENT``, then get a
    lognormal shock so the degree distribution is heavy-tailed like the real network.
    A route survives only if it clears ``MIN_ROUTE_FLIGHTS`` *and* passes the
    hub-and-spoke gate: at least one endpoint is a major hub, or the pair is close
    enough for regional nonstop service. That gate is what produces the sparse
    spoke-to-spoke structure the bridge metrics and Leiden communities depend on.
    """
    ids = np.array([a.airport_id for a in AIRPORTS])
    mass = np.array([a.mass for a in AIRPORTS])
    lat = np.array([a.latitude for a in AIRPORTS])
    lon = np.array([a.longitude for a in AIRPORTS])

    # Airlines schedule round trips, so service is decided per unordered pair. Drawing
    # the two directions independently would leave one-way routes all over the network,
    # which is both unrealistic and structurally destructive: the graph stops being
    # strongly connected and eigenvector centrality degenerates to an empty column.
    first_idx, second_idx = np.triu_indices(len(AIRPORTS), k=1)

    distance = great_circle_miles(lat[first_idx], lon[first_idx], lat[second_idx], lon[second_idx])
    distance = np.maximum(distance, 75.0)

    expected = GRAVITY_SCALE * mass[first_idx] * mass[second_idx] / (distance**DISTANCE_EXPONENT)
    shock = rng.lognormal(mean=0.0, sigma=0.55, size=expected.shape)
    pair_expected = np.maximum(expected * shock, 0.0)

    serves_hub = (mass[first_idx] >= HUB_MASS_THRESHOLD) | (mass[second_idx] >= HUB_MASS_THRESHOLD)
    regional_pair = distance <= REGIONAL_NONSTOP_MILES
    served = (pair_expected >= MIN_ROUTE_FLIGHTS) & (serves_hub | regional_pair)

    first_idx, second_idx = first_idx[served], second_idx[served]
    distance, pair_expected = distance[served], pair_expected[served]

    # Both directions of a served pair are drawn around the same expectation, so
    # outbound and inbound counts differ slightly the way real monthly totals do.
    outbound = rng.poisson(pair_expected)
    inbound = rng.poisson(pair_expected)

    return pd.DataFrame(
        {
            "origin_id": np.concatenate([ids[first_idx], ids[second_idx]]),
            "destination_id": np.concatenate([ids[second_idx], ids[first_idx]]),
            "distance_mi": np.concatenate([distance, distance]),
            "flight_count": np.concatenate([outbound, inbound]),
        }
    ).reset_index(drop=True)


def build_on_time_frame(routes: pd.DataFrame, year: int, month: int, rng: np.random.Generator) -> pd.DataFrame:
    """Expand routes into one row per flight leg, in on-time performance layout."""
    counts = routes["flight_count"].to_numpy()
    total = int(counts.sum())

    origin = np.repeat(routes["origin_id"].to_numpy(), counts)
    dest = np.repeat(routes["destination_id"].to_numpy(), counts)
    distance = np.repeat(routes["distance_mi"].to_numpy(), counts)

    # Congestion bias is a stable per-airport property, so busy hubs stay late all month.
    bias_by_id = {
        a.airport_id: float(rng.uniform(*DELAY_BIAS_RANGE)) + 6.0 * a.mass for a in AIRPORTS
    }
    dest_bias = np.array([bias_by_id[int(a)] for a in dest])

    # Right-skewed: most flights near on time, a long tail of severe delays.
    arr_delay = rng.gumbel(loc=dest_bias - 6.0, scale=DELAY_SPREAD_MIN / 3.0, size=total)
    arr_delay += 0.0015 * distance
    arr_delay = np.round(arr_delay).astype(float)

    cancelled = (rng.random(total) < CANCELLATION_RATE).astype(int)
    diverted = (rng.random(total) < DIVERSION_RATE).astype(int)
    arr_delay[cancelled == 1] = np.nan

    seq_offset = np.full(total, 1, dtype=int)
    return pd.DataFrame(
        {
            "YEAR": year,
            "MONTH": month,
            "OP_CARRIER_AIRLINE_ID": rng.choice([19393, 19790, 19805, 20304, 20355, 20366], size=total),
            "ORIGIN_AIRPORT_ID": origin,
            "ORIGIN_AIRPORT_SEQ_ID": origin * 100 + seq_offset,
            "ORIGIN_CITY_MARKET_ID": origin,
            "DEST_AIRPORT_ID": dest,
            "DEST_AIRPORT_SEQ_ID": dest * 100 + seq_offset,
            "DEST_CITY_MARKET_ID": dest,
            "DISTANCE": np.round(distance, 0),
            "ARR_DELAY": arr_delay,
            "CANCELLED": cancelled,
            "DIVERTED": diverted,
        }
    )


def build_t100_frame(routes: pd.DataFrame, year: int, month: int, rng: np.random.Generator) -> pd.DataFrame:
    """Segment-level passenger and seat totals per directed route."""
    flights = routes["flight_count"].to_numpy()
    seats = flights * SEATS_PER_FLIGHT
    load_factor = rng.uniform(*LOAD_FACTOR_RANGE, size=len(routes))
    return pd.DataFrame(
        {
            "YEAR": year,
            "MONTH": month,
            "ORIGIN_AIRPORT_ID": routes["origin_id"].to_numpy(),
            "DEST_AIRPORT_ID": routes["destination_id"].to_numpy(),
            "DEPARTURES_PERFORMED": flights,
            "PASSENGERS": np.round(seats * load_factor).astype(int),
            "SEATS": seats,
            "DISTANCE": np.round(routes["distance_mi"].to_numpy(), 0),
        }
    )


def _write_csv(frame: pd.DataFrame, path: Path, *, force: bool) -> None:
    """Write ``frame`` to ``path``, honoring the DATA-01 immutable-raw policy."""
    if path.exists() and not force:
        raise FileExistsError(
            f"{path} already exists. data/raw/ is immutable in place (DATA-01); "
            "pass --force to overwrite this synthetic file deliberately."
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)


def generate(cfg: AtnaConfig, *, seed: int, force: bool) -> dict[str, Path]:
    """Write all three raw CSVs for the configured snapshot month."""
    year, month = (int(part) for part in cfg.snapshot_id.split("-", 1))
    rng = np.random.default_rng(seed)

    routes = build_route_frame(rng)
    if routes.empty:
        raise RuntimeError("gravity model produced no routes above the flight threshold")

    outputs = {
        "master": (build_master_frame(), cfg.raw_master_airport),
        "on_time": (build_on_time_frame(routes, year, month, rng), cfg.raw_on_time),
        "t100": (build_t100_frame(routes, year, month, rng), cfg.raw_t100),
    }
    for frame, path in outputs.values():
        _write_csv(frame, path, force=force)

    written = {name: path for name, (_, path) in outputs.items()}
    legs = int(routes["flight_count"].sum())
    print(
        f"Generated synthetic snapshot {cfg.snapshot_id}: "
        f"{len(AIRPORTS)} airports, {len(routes)} directed routes, {legs:,} flight legs"
    )
    for name, path in written.items():
        print(f"  {name:<8} {path.relative_to(cfg.repo_root)}")
    return written


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a synthetic BTS-shaped raw dataset for the configured snapshot."
    )
    parser.add_argument("--config", type=Path, default=None, metavar="PATH", help="YAML config override")
    parser.add_argument("--seed", type=int, default=20251201, help="RNG seed (default: 20251201)")
    parser.add_argument("--force", action="store_true", help="overwrite existing raw CSVs")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    generate(load_config(args.config), seed=args.seed, force=args.force)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
