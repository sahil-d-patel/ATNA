# Data Preprocessing

## Section Goal
Describe how raw BTS inputs are transformed into canonical processed tables that feed all metrics, communities, and scenario outputs.

## Related Visuals
- `visuals/network_map_min_analysis_weight_5.png`
- `visuals/community_map_2025-12.png`

## Input Data Sources (MVP Slice)
- Reporting-carrier on-time performance extracts.
- T-100 domestic segment extracts.
- Airport coordinate/reference table.

## Raw Data Policy
- Raw files are treated as immutable source-of-truth artifacts.
- Snapshot month is pinned by `snapshot_id` (`YYYY-MM`) in project config.
- Reproducibility requires month-consistent files and manifest verification.

## Processing Outputs
- `airports.csv`: airport metadata and canonical identifiers.
- `edges.csv`: route-level directional links with `flight_count`, analysis fields, snapshot metadata.
- `nodes.csv`: node-level baseline graph fields.

These outputs are the substrate for all visuals in this project.

## Key Transform Rules
- Normalize and align airport identifiers across sources.
- Aggregate route records to monthly directional edges.
- Compute `analysis_weight = log1p(flight_count)` for stable weighting.
- Construct canonical route keys to prevent ambiguous route identity.
- Enforce required columns and snapshot consistency checks.

## Data Quality Controls
- Join integrity checks between edges, nodes, and airport reference data.
- Coordinate presence checks for mapped airports.
- Non-empty file checks and expected-count verification for monthly downloads.
- Snapshot consistency assertions (`2025-12` across processed artifacts).

## Why This Matters For Visual Trust
- If preprocessing is unstable, all maps and rankings become misleading.
- The network map depends on edge-weight correctness and coordinate completeness.
- Community output quality depends on clean topology and consistent node coverage.
- Scenario outputs depend on accurate baseline graph construction.

## Visual Read Guidance From A Preprocessing Perspective
### Network Map (`network_map_min_analysis_weight_5.png`)
- Validate that major corridors appear plausible for the snapshot month.
- Missing expected hubs/routes can indicate preprocessing or join issues.

### Community Map (`community_map_2025-12.png`)
- Check that communities are non-trivial and interpretable.
- Over-fragmentation or collapse into one group can indicate upstream data or weighting issues.

## Common Pitfalls To Mention
- Treating monthly snapshots as interchangeable.
- Confusing raw traffic counts with transformed analysis weights.
- Interpreting map artifacts without confirming preprocessing validation status.
