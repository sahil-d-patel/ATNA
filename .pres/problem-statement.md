# Problem Statement

## Section Goal
Define the real analytical problem: identifying which airports and routes create outsized systemic risk when stressed or removed.

## Related Visuals
- `visuals/network_map_min_analysis_weight_5.png`
- `visuals/top_5_critical_routes.png`
- `visuals/vulnerability_map.png`

## Problem Context
- Large transportation networks can look robust in aggregate but fail through a small number of structural choke points.
- Traditional "top traffic only" ranking misses bridge-like connectors that carry disproportionate structural importance.
- Decision-making requires a way to separate:
  - high-volume assets,
  - high-connectivity assets,
  - and high-consequence failure points.

## Key Questions This Project Answers
1. Which airports are traffic hubs versus structural bridges?
2. Which routes are critical due to both weight and cross-community connectivity?
3. Which removals generate the largest drop in network integrity and health?

## How The Visuals Express The Problem
### 1) Network Map (`network_map_min_analysis_weight_5.png`)
- Reveals uneven concentration of links and potential dependence on certain corridors.
- Motivates why disruption is not uniformly distributed across geography.

### 2) Critical Routes (`top_5_critical_routes.png`)
- Distills route-level risk into a top list for immediate interpretation.
- Reinforces that route fragility can be high even when many alternate routes exist elsewhere.

### 3) Vulnerability Map (`vulnerability_map.png`)
- Converts abstract metric outputs into a spatial/systemic risk layer.
- Highlights likely "high consequence" airports beyond simple throughput rankings.

## Why This Matters
- Infrastructure planning: where to prioritize redundancy investment.
- Operational preparedness: where disruption likely propagates fastest.
- Policy and resilience: how to support regions dependent on a few structural connectors.

## Scope Boundaries (Important)
- This is a structural network analytics MVP, not a full airline-operations simulator.
- The model does not reconstruct aircraft rotations, crew constraints, or causal delay chains.
- Results are snapshot-specific and should be interpreted month-by-month.
