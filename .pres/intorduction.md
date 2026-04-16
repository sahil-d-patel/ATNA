# Introduction

## Section Goal
This section introduces ATNA as a structural analysis project of the U.S. domestic airport network for a fixed monthly snapshot (`2025-12`). The core idea is to understand **how airports and routes hold the network together**, not to predict exact flight delays.

## Related Visuals
- `visuals/network_map_min_analysis_weight_5.png`
- `visuals/community_map_2025-12.png`
- `visuals/vulnerability_map.png`

## What ATNA Is
- A graph-based view of domestic aviation where airports are nodes and routes are directed weighted edges.
- The edge weight used in analytics is `analysis_weight = log1p(flight_count)`, which compresses very large traffic differences so structure is easier to compare.
- The project focuses on a frozen snapshot month so metrics are internally consistent and comparable within that month.

## How To Read The Visuals In This Section
### 1) Network Map (`network_map_min_analysis_weight_5.png`)
- Shows the national route backbone after filtering out very low-weight links.
- Thick/high-visibility connections indicate routes with larger analysis influence.
- Use this map to orient the audience: where density concentrates, where sparse regions appear, and where coast-to-coast coupling depends on hub corridors.

### 2) Community Map (`community_map_2025-12.png`)
- Shows structural clusters discovered by Leiden community detection.
- Communities are algorithmic structure groups, not state/region boundaries.
- This visual introduces the idea that disruption effects can spread within and across communities differently.

### 3) Vulnerability Map (`vulnerability_map.png`)
- Visualizes airport-level vulnerability as a blended index of scenario impact and bridge behavior.
- Helps transition from "busy airport" thinking to "network criticality" thinking.
- Useful anchor statement: a high-traffic airport and a high-vulnerability airport can overlap, but they are not always the same.

## Core Storyline To Establish
1. The U.S. network is highly connected but not uniformly resilient.
2. Structural importance has multiple dimensions: traffic concentration, bridge position, and disruption consequences.
3. The project combines graph metrics plus scenario simulation to expose weak points.

## Terms To Define Early
- **Hub Score:** composite of strength, PageRank, and degree percentiles.
- **Bridge Score:** percentile of betweenness centrality (connector importance).
- **Community:** Leiden-derived group of airports with denser internal ties.
- **Impact Score / Network Health:** aggregate disruption outcome metrics from scenario analysis.

## Suggested Presenter Notes
- Start with the network map to establish scale and national topology.
- Move to community map to show latent structure.
- End with vulnerability map to frame why the rest of the presentation matters.
