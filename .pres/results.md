# Results

## Section Goal
Present the key findings from network structure, community decomposition, route criticality, and scenario disruptions.

## Related Visuals
- `visuals/network_map_min_analysis_weight_5.png`
- `visuals/community_map_2025-12.png`
- `visuals/top_5_critical_routes.png`
- `visuals/vulnerability_map.png`
- `visuals/DFW_removal_impact.png`
- `visuals/Yellowstone_airport_removal_impact.png`

## Result Set 1: Baseline Structure
### Network Backbone (`network_map_min_analysis_weight_5.png`)
- The route system is dense but unevenly concentrated around major hubs and corridors.
- Structural dependence appears clustered rather than uniformly distributed.
- Practical interpretation: resilience planning should prioritize concentrated corridors first.

## Result Set 2: Community Organization
### Community Partition (`community_map_2025-12.png`)
- Leiden detects multiple non-trivial communities for `2025-12`, supporting interpretable meso-scale structure.
- Communities reflect structural cohesion, enabling cross-community risk analysis.
- This result supports the route criticality framework that penalizes inter-community disruption potential.

## Result Set 3: Route-Level Fragility
### Top Route Criticality (`top_5_critical_routes.png`)
- Highest-ranked routes combine substantial traffic significance with inter-community connectivity.
- This confirms the model does not reduce route importance to volume alone.
- Operational takeaway: a small route subset can represent disproportionate network risk.

## Result Set 4: Airport-Level Vulnerability
### Vulnerability Layer (`vulnerability_map.png`)
- High vulnerability aligns with airports that are either high-impact removals, strong bridges, or both.
- The map separates "busy" from "structurally consequential" airports where necessary.
- This creates a clearer prioritization lens for intervention planning.

## Result Set 5: Scenario Comparison
### Major Hub Removal (`DFW_removal_impact.png`)
- Removing a major hub produces broad and deeper network effects.
- Expect higher aggregate impact and lower network health under this condition.

### Peripheral/Regional Case (`Yellowstone_airport_removal_impact.png`)
- Removal impact is typically more localized and lower in aggregate severity.
- Contrast with DFW case demonstrates why topology position dominates simple airport size labels.

## Integrated Interpretation
- Baseline maps identify where dependence may exist.
- Community and route outputs identify where structure can fracture.
- Scenario outputs quantify how severe that fracture is under explicit disruptions.
- Together, these results produce actionable rankings for resilience-oriented decisions.
