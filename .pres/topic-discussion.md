# Topic Discussion

## Section Goal
Go beyond reporting outputs and discuss implications, trade-offs, interpretation limits, and strategic use.

## Related Visuals
- `visuals/vulnerability_map.png`
- `visuals/top_5_critical_routes.png`
- `visuals/DFW_removal_impact.png`
- `visuals/Yellowstone_airport_removal_impact.png`
- `visuals/community_map_2025-12.png`

## Discussion Theme 1: Traffic Importance vs Structural Importance
- High traffic does not automatically imply highest systemic risk.
- Bridge-like airports/routes can create outsized cascade pathways.
- The vulnerability and scenario visuals help separate these concepts concretely.

## Discussion Theme 2: Why Community Structure Matters
- Cross-community links often act as "connective tissue" between dense sub-networks.
- Disrupting those links can produce broader isolation effects than similar-volume internal links.
- Community-aware route ranking therefore improves resilience targeting.

## Discussion Theme 3: Scenario Contrasts As Evidence
### DFW vs Yellowstone
- The DFW case illustrates broad exposure and stronger global network disturbance.
- The Yellowstone case illustrates a narrower disturbance footprint.
- The contrast is useful to explain why topology location and connector role drive impact.

## Discussion Theme 4: Practical Decision Use-Cases
- **Infrastructure investment:** prioritize redundancy around high vulnerability and critical routes.
- **Contingency planning:** build disruption playbooks around high-impact removals.
- **Monitoring strategy:** track month-over-month movement of top vulnerable airports/routes.

## Discussion Theme 5: Interpretation Constraints
- Snapshot-specific: findings should be read within the analyzed month context.
- Structural model: not a substitute for full operational causality modeling.
- Composite scores: strong for ranking and triage, weaker for standalone absolute forecasting claims.

## Talking Points For Q&A
- "Why log-transformed weights?" -> stabilizes heavy-tailed traffic effects for structural comparison.
- "Why 2-hop ripple?" -> deliberate MVP simplification with controlled interpretability.
- "Can this generalize to other months?" -> yes methodologically, but each month should be recomputed and interpreted with its own data.
