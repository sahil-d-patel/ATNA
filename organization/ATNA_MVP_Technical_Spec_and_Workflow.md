# ATNA MVP Technical Specification and Workflow
## Air Traffic Network Analysis
## Locked MVP Scope, Build Plan, Data Model, Metrics, and XML Prompt Pack

Version: 1.0  
Status: Locked MVP Spec  
Project: Air Traffic Network Analysis  
Scope: U.S. domestic airport network visual analytics and scenario editing tool  

---

# 1. Executive Summary

ATNA will be built as an interactive visual analytics and scenario editing tool for U.S. domestic flight traffic.

The MVP is not a full airline operations simulator.
The MVP is not a real-time delay forecasting engine.
The MVP is not a purely static EDA notebook project.

The MVP is a network science product with a clean interactive interface.
It will help users:

- explore airport traffic structure
- identify hubs and structural bridge airports
- inspect Leiden communities and modularity-driven structure
- remove airports or routes through a scenario editor
- observe 2-hop structural ripple effects
- compare before vs after network health

The MVP is optimized for:

- finishability
- interpretability
- demo strength
- technical credibility
- clean division of team work

---

# 2. Locked MVP Decisions

## 2.1 Product framing
Balanced hybrid.

This means the project should feel like both:

- a serious network science analysis tool
- a usable decision-support style interactive product

## 2.2 Geographic scope
U.S. domestic only.

## 2.3 Time granularity
Monthly snapshots.

## 2.4 Graph type
Primary graph:
- directed weighted airport graph

Secondary graph:
- undirected structural projection for ripple and selected community views

## 2.5 Default edge weight
Flight count.

## 2.6 Community algorithm
Leiden.

## 2.7 Scenario editor support in MVP
- airport removals
- route removals

## 2.8 Ripple model
Simple structural ripple model.

## 2.9 Ripple depth
2 hops maximum.

## 2.10 Ripple discounting
Second hop is discounted.
Locked value:
- lambda = 0.35

## 2.11 Frontend stack
- Streamlit
- Plotly

## 2.12 Graph stack
- pandas or polars for ETL
- NetworkX for main graph analysis
- igraph for Leiden if needed

---

# 3. Product Definition

## 3.1 One-sentence product definition
An interactive visual analytics platform for U.S. domestic airport networks that supports hub ranking, bridge detection, Leiden communities, airport and route disruption editing, and 2-hop structural ripple analysis.

## 3.2 Core product questions
The MVP must answer these questions clearly:

1. Which airports are the biggest hubs?
2. Which airports act as structural bridges?
3. How is the network partitioned into communities?
4. Which routes are structurally important?
5. What changes when an airport is removed?
6. What changes when a route is removed?
7. How far does structural disruption spread in the local network?
8. How much damage does a scenario cause overall?

## 3.3 What the MVP is not
The MVP will not attempt:

- real-world operational delay prediction
- aircraft rotation simulation
- crew connection modeling
- itinerary reconstruction
- multi-user editing
- full historical causal propagation modeling

---

# 4. MVP Architecture

## 4.1 High-level architecture

### Layer 1: Raw data
Raw BTS files stored unchanged.

### Layer 2: Cleaning and normalization
Scripts standardize airport identifiers, validate columns, and build monthly tables.

### Layer 3: Graph tables
Processed node and edge tables per monthly snapshot.

### Layer 4: Metrics engine
Precompute centrality, communities, route scores, ripple dependencies, and scenario outputs.

### Layer 5: App layer
Streamlit app loads precomputed artifacts and presents interactive views.

## 4.2 Recommended repository structure

```text
atna/
├── data/
│   ├── raw/
│   ├── interim/
│   ├── processed/
│   └── reference/
├── outputs/
│   ├── figures/
│   ├── tables/
│   └── scenarios/
├── notebooks/
│   └── exploration/
├── src/
│   ├── etl/
│   ├── graph/
│   ├── metrics/
│   ├── communities/
│   ├── scenarios/
│   ├── app/
│   └── utils/
├── docs/
│   └── specs/
├── tests/
├── requirements.txt
└── README.md
```

---

# 5. Data Inputs

## 5.1 Required data sources

### A. BTS Reporting Carrier On-Time Performance
Use for:
- domestic route records
- origin and destination
- time aggregation
- delay-related optional overlays

### B. BTS Master Coordinate / airport metadata
Use for:
- airport identity joins
- latitude and longitude
- map display

### C. BTS T-100 Segment
Use for:
- passengers
- seats
- departures performed
- alternate weights later

## 5.2 MVP data policy
The MVP will use flight count as the canonical analysis weight.
Passenger count may be stored as an alternate comparison field.

---

# 6. Canonical Data Model

## 6.1 airports.csv
One row per airport.

### Required columns
- airport_id_canonical
- airport_code_raw
- airport_name
- city
- state
- country
- latitude
- longitude
- timezone
- active_flag
- source_version

## 6.2 edges.csv
One row per directed route per snapshot.

### Required columns
- snapshot_id
- year
- month
- origin_id
- destination_id
- flight_count
- passenger_count
- seat_count
- avg_arr_delay
- pct_delayed
- analysis_weight
- route_key

### Definitions
- `snapshot_id` format: `YYYY-MM`
- `route_key` format: `origin_id__destination_id__snapshot_id`
- `analysis_weight = log(1 + flight_count)`

## 6.3 nodes.csv
One row per airport per snapshot.

### Required columns
- snapshot_id
- airport_id
- flights_out
- flights_in
- strength_out
- strength_in
- strength_total
- degree_out
- degree_in
- degree_total

## 6.4 metrics.csv
One row per airport per snapshot.

### Required columns
- snapshot_id
- airport_id
- pagerank
- betweenness
- eigenvector
- hub_score
- bridge_score
- vulnerability_score
- leiden_community_id

## 6.5 communities.csv
One row per community per snapshot.

### Required columns
- snapshot_id
- leiden_community_id
- community_size
- community_traffic
- internal_density
- top_hub_airport_ids
- top_bridge_airport_ids

## 6.6 route_metrics.csv
One row per directed route per snapshot.

### Required columns
- snapshot_id
- origin_id
- destination_id
- analysis_weight
- cross_community_flag
- route_criticality_score

## 6.7 scenarios.csv
One row per scenario execution.

### Required columns
- scenario_id
- snapshot_id
- scenario_type
- edited_airports
- edited_routes
- impact_score
- network_health
- lcc_loss
- reachability_loss
- ripple_severity
- created_at

## 6.8 scenario_exposure.csv
One row per affected airport per scenario.

### Required columns
- scenario_id
- airport_id
- hop_level
- exposure_score
- exposure_rank

---

# 7. Locked MVP Metrics and Formulas

## 7.1 Raw edge weight

```text
flight_count(i, j, t)
```

Used for:
- tables
- reporting
- tooltips
- exports

## 7.2 Analysis edge weight

```text
w(i, j, t) = log(1 + flight_count(i, j, t))
```

Used for:
- centrality
- visual edge thickness
- route comparison
- robustness
- scenario propagation

## 7.3 Airport traffic metrics

### Strength
```text
s_out(i) = Σ_j w(i, j)
s_in(i) = Σ_j w(j, i)
s_total(i) = s_in(i) + s_out(i)
```

### Degree
```text
deg_out(i) = number of outgoing neighbors
deg_in(i) = number of incoming neighbors
deg_total(i) = deg_in(i) + deg_out(i)
```

## 7.4 Airport centrality metrics

### PageRank
Compute on the directed weighted graph.

### Betweenness
Compute on the selected graph used for structural bridge analysis.

### Eigenvector
Secondary metric only.
Display it if stable and available.
Do not make it central to the MVP story.

## 7.5 Percentile scaling rule
For any display score:

```text
P(metric) = percentile rank of metric scaled to 0 through 100
```

This makes different metrics comparable in composite scores.

## 7.6 Hub Score
Purpose:
Identify the biggest overall hubs.

### Formula
```text
HubScore(i) = 0.50 * P(s_total(i)) + 0.30 * P(PageRank(i)) + 0.20 * P(deg_total(i))
```

## 7.7 Bridge Score
Purpose:
Identify structural connectors.

### Formula
```text
BridgeScore(i) = P(Betweenness(i))
```

## 7.8 Vulnerability Score
Purpose:
Estimate how damaging it is to remove a given airport.

### Formula
```text
Vulnerability(i) = 0.60 * P(ImpactScore(remove i)) + 0.40 * P(BridgeScore(i))
```

## 7.9 Community outputs
For each Leiden community `C`:

### Community traffic
```text
CommunityTraffic(C) = Σ_(i,j in C) w(i,j)
```

### Internal density
```text
InternalDensity(C) = internal_edges(C) / (|C| * (|C| - 1))
```

Store and display:
- community size
- community traffic
- internal density
- top airports by hub score
- top airports by bridge score

## 7.10 Route Criticality Score
Purpose:
Rank routes by structural importance for route-removal scenarios.

### Formula
```text
RouteCriticality(i, j) = 0.70 * P(w(i, j)) + 0.30 * CrossCommunity(i, j)
```

Where:

```text
CrossCommunity(i, j) = 100 if origin and destination are in different Leiden communities
CrossCommunity(i, j) = 0 otherwise
```

---

# 8. Locked Ripple Model

## 8.1 Model type
Simple structural ripple approximation.

This model estimates local structural disruption exposure.
It does not predict actual real-world delays.

## 8.2 Undirected structural dependency weight
For ripple only:

```text
W(i, j) = w(i, j) + w(j, i)
```

## 8.3 Local dependency share

```text
Share(i, j) = W(i, j) / Σ_k W(i, k)
```

Interpretation:
The stronger airport `i` depends on airport `j` structurally, the larger the share.

## 8.4 Airport removal ripple
If airport `r` is removed:

### First-hop exposure
```text
E1(j | r) = Shock(r) * Share(r, j)
```

### Second-hop exposure
```text
E2(k | r) = λ * Σ_j [E1(j | r) * Share(j, k)]
```

### Total exposure
```text
Exposure(k | r) = E1(k | r) + E2(k | r)
```

## 8.5 Route removal ripple
If route `(u, v)` is removed:

### Route shock
```text
Shock(u, v) = 100 * W(u, v) / max_route_weight
```

### Endpoint seeding
```text
Seed(u) = 0.5 * Shock(u, v)
Seed(v) = 0.5 * Shock(u, v)
```

Then propagate from both endpoints using the same 2-hop logic.

## 8.6 Locked constants
```text
Shock(airport removal) = 100
λ = 0.35
```

## 8.7 Hop policy
- hop 0: edited airport or route seed
- hop 1: strongest propagated effect
- hop 2: discounted propagated effect
- hop 3+: ignored in MVP

## 8.8 Exposure output policy
Store:
- per-airport exposure score
- hop level
- exposure rank within scenario

---

# 9. Locked Scenario Scores

## 9.1 Largest connected component loss

```text
LCC_Loss = 100 * (1 - LCC_post / LCC_pre)
```

## 9.2 Reachability loss

```text
Reachability_Loss = 100 * (1 - ReachablePairs_post / ReachablePairs_pre)
```

## 9.3 Ripple severity

```text
RippleSeverity = 100 * (number of airports with Exposure >= 10) / total_airports
```

## 9.4 Impact Score
Purpose:
One overall damage score for a scenario.

### Formula
```text
ImpactScore = 0.40 * LCC_Loss + 0.30 * Reachability_Loss + 0.30 * RippleSeverity
```

## 9.5 Network Health
Purpose:
One positive-facing summary card for the UI.

### Formula
```text
NetworkHealth = 100 - ImpactScore
```

---

# 10. Locked MVP Pages

## 10.1 Page 1: Overview
Display:
- total airports
- total routes
- total flight volume
- top hubs
- quick snapshot summary

## 10.2 Page 2: Network Map
Display:
- airport points
- route lines
- edge thickness by analysis weight
- filters by month and threshold

## 10.3 Page 3: Airport Explorer
Display:
- sortable airport ranking table
- hub score
- bridge score
- vulnerability score
- selected airport drilldown

## 10.4 Page 4: Communities
Display:
- Leiden community coloring
- community statistics
- top hubs per community
- top bridges per community

## 10.5 Page 5: Route Explorer
Display:
- route ranking table
- route criticality score
- cross-community indicator

## 10.6 Page 6: Scenario Editor
Display:
- remove airport control
- remove route control
- before vs after summary cards
- impact score
- network health
- ripple map
- affected airport table

## 10.7 Page 7: Methodology
Display:
- graph definitions
- formula explanations
- assumptions
- limitations

---

# 11. Exact Project Progression

## Phase 0: Locking and setup
Goal:
Freeze all definitions before the team spreads out.

### Deliverables
- locked MVP scope
- locked metric formulas
- locked file schemas
- locked page structure
- locked ownership map

### Required output
- this spec file committed to repo
- team signoff on canonical schema

## Phase 1: Data foundation
Goal:
Build a reproducible path from raw data to processed monthly graph tables.

### Tasks
1. collect raw BTS files
2. inspect columns
3. standardize airport IDs
4. join airport metadata
5. aggregate route records to monthly edges
6. generate nodes table
7. validate snapshot counts

### Deliverables
- airports.csv
- edges.csv
- nodes.csv
- data dictionary
- validation notes

### Exit criteria
- at least one monthly snapshot builds end-to-end without manual fixes
- no broken airport joins in the selected MVP slice

## Phase 2: Graph metrics
Goal:
Generate airport, route, and community metrics.

### Tasks
1. build NetworkX directed graph per snapshot
2. compute strength and degree metrics
3. compute PageRank
4. compute betweenness
5. compute eigenvector if stable
6. compute Hub Score
7. compute Bridge Score
8. run Leiden
9. generate communities.csv
10. generate route_metrics.csv

### Deliverables
- metrics.csv
- communities.csv
- route_metrics.csv

### Exit criteria
- top hubs are sensible
- bridge rankings are interpretable
- community assignments render cleanly on the map

## Phase 3: Scenario engine
Goal:
Build editable disruption logic and damage scoring.

### Tasks
1. implement airport removal function
2. implement route removal function
3. rebuild post-edit graph
4. compute LCC loss
5. compute reachability loss
6. compute 2-hop ripple exposures
7. compute ripple severity
8. compute Impact Score
9. compute Network Health
10. save scenarios and exposure outputs

### Deliverables
- scenario engine module
- scenarios.csv
- scenario_exposure.csv

### Exit criteria
- at least 3 demo scenarios run without failure
- ripple outputs match formula behavior

## Phase 4: App implementation
Goal:
Build Streamlit product around the precomputed artifacts.

### Tasks
1. implement overview page
2. implement network map
3. implement airport explorer
4. implement communities page
5. implement route explorer
6. implement scenario editor
7. implement methodology page
8. add filtering and tooltips
9. add export support if time allows

### Deliverables
- working Streamlit app

### Exit criteria
- full narrative demo can be run start to finish
- all locked pages load

## Phase 5: QA and polish
Goal:
Remove friction and prepare the final story.

### Tasks
1. test all filters
2. validate schema consistency
3. validate scenario edge cases
4. stress-test empty selections and small communities
5. refine visual design
6. capture final screenshots
7. rehearse presentation flow

### Deliverables
- stable demo build
- final report assets
- clean README

---

# 12. Team Workflow

## 12.1 Team tracks

### Track A: Data and ETL
Owns:
- raw inputs
- cleaning
- joins
- processed node and edge tables

### Track B: Graph and metrics
Owns:
- NetworkX graph construction
- PageRank
- betweenness
- composite scores
- Leiden integration
- route scoring

### Track C: Scenario engine
Owns:
- airport removal logic
- route removal logic
- ripple propagation
- impact scoring
- scenario artifacts

### Track D: Frontend and integration
Owns:
- Streamlit pages
- Plotly visuals
- filters
- UI state
- merging artifacts into the app

## 12.2 Cross-track owners

### Schema owner
Maintains canonical columns and file contracts.

### Integration owner
Ensures artifacts connect without hand edits.

### Demo owner
Maintains final story flow and presentation quality.

## 12.3 Workflow policy
- no team creates private schema variants
- every metric must flow into a documented CSV or parquet output
- app consumes processed artifacts, not ad hoc notebook state
- expensive metrics are precomputed offline whenever possible

---

# 13. Validation Checklist

## 13.1 Data validation
- airport IDs resolve correctly
- coordinates exist for mapped airports
- route aggregation matches source counts
- monthly snapshot IDs are consistent

## 13.2 Metrics validation
- major hub rankings make intuitive sense
- bridge airports are not identical to pure traffic hubs
- communities are non-trivial and spatially interpretable

## 13.3 Scenario validation
- airport removal changes connectivity as expected
- route removal updates exposure only through valid graph paths
- second hop is weaker than first hop
- network health falls when impact score rises

## 13.4 UI validation
- all pages load
- filters do not break charts
- selected airports and routes show correct metadata
- methodology text matches implemented formulas

---

# 14. Demo Workflow

## Recommended final demo sequence
1. open a monthly snapshot
2. show major hubs on the network map
3. switch to airport explorer and rank by Hub Score
4. rank by Bridge Score and explain the difference
5. open communities page and show Leiden partitioning
6. open route explorer and highlight cross-community routes
7. remove a major airport in the scenario editor
8. show ripple spread, impact score, and network health drop
9. remove a route and compare the outcome
10. close with the structural takeaway

---

# 15. Implementation Notes

## 15.1 Why NetworkX is still core
NetworkX remains the main graph engine for MVP analysis because it is readable, flexible, and good for centrality and structural logic.

## 15.2 Why Leiden may use igraph
Leiden support is cleaner through igraph or a compatible backend.
The community labels can be merged back into the common metrics table after computation.

## 15.3 Why formulas are intentionally simple
The project needs a believable and finishable MVP.
Simple formulas make the app easier to implement, explain, validate, and demo.

---

# 16. XML Prompt Pack

These prompts are designed to guide AI-assisted implementation in tools like Cursor, ChatGPT, Claude, or internal planning agents.

Use each prompt as a starting instruction block.
Replace placeholder values where needed.

## 16.1 Master project-manager prompt

```xml
<prompt>
  <role>
    You are the technical project planner for the ATNA MVP.
  </role>
  <objective>
    Convert the locked MVP scope into an execution-ready plan with milestones, module dependencies, file outputs, and implementation tasks.
  </objective>
  <project_context>
    <name>ATNA - Air Traffic Network Analysis</name>
    <product_type>Interactive visual analytics and scenario editing tool</product_type>
    <scope>U.S. domestic airport network only</scope>
    <time_granularity>Monthly snapshots</time_granularity>
    <default_weight>Flight count</default_weight>
    <community_algorithm>Leiden</community_algorithm>
    <scenario_support>
      <airport_removal>true</airport_removal>
      <route_removal>true</route_removal>
    </scenario_support>
    <ripple_model>
      <type>Simple structural ripple</type>
      <max_hops>2</max_hops>
      <lambda>0.35</lambda>
    </ripple_model>
    <frontend>Streamlit + Plotly</frontend>
    <graph_stack>NetworkX primary, igraph for Leiden if needed</graph_stack>
  </project_context>
  <required_outputs>
    <output>Phased execution plan</output>
    <output>Module dependency graph</output>
    <output>Task breakdown by team track</output>
    <output>Acceptance criteria for each milestone</output>
  </required_outputs>
  <constraints>
    <constraint>Do not expand scope beyond MVP</constraint>
    <constraint>Prefer precomputed metrics over expensive live computation</constraint>
    <constraint>Keep all outputs tied to documented CSV or parquet artifacts</constraint>
  </constraints>
</prompt>
```

## 16.2 Data pipeline prompt

```xml
<prompt>
  <role>
    You are the lead data engineer for the ATNA MVP.
  </role>
  <objective>
    Build a reproducible ETL workflow that converts raw BTS inputs into monthly airports, nodes, and edges tables for graph analysis.
  </objective>
  <input_sources>
    <source>BTS Reporting Carrier On-Time Performance</source>
    <source>BTS Master Coordinate / airport metadata</source>
    <source>BTS T-100 Segment</source>
  </input_sources>
  <required_tables>
    <table>airports.csv</table>
    <table>edges.csv</table>
    <table>nodes.csv</table>
  </required_tables>
  <schema_requirements>
    <airports>
      <column>airport_id_canonical</column>
      <column>airport_name</column>
      <column>latitude</column>
      <column>longitude</column>
    </airports>
    <edges>
      <column>snapshot_id</column>
      <column>origin_id</column>
      <column>destination_id</column>
      <column>flight_count</column>
      <column>analysis_weight</column>
    </edges>
    <nodes>
      <column>snapshot_id</column>
      <column>airport_id</column>
      <column>strength_total</column>
      <column>degree_total</column>
    </nodes>
  </schema_requirements>
  <business_rules>
    <rule>Scope to U.S. domestic only</rule>
    <rule>Aggregate by monthly snapshot</rule>
    <rule>Set analysis_weight = log(1 + flight_count)</rule>
    <rule>Preserve raw flight_count for reporting</rule>
  </business_rules>
  <required_outputs>
    <output>Step-by-step ETL plan</output>
    <output>Validation checklist</output>
    <output>Expected edge cases</output>
  </required_outputs>
</prompt>
```

## 16.3 Graph metrics prompt

```xml
<prompt>
  <role>
    You are the graph analytics engineer for the ATNA MVP.
  </role>
  <objective>
    Implement airport-level and route-level metrics using the locked MVP formulas.
  </objective>
  <inputs>
    <table>edges.csv</table>
    <table>nodes.csv</table>
  </inputs>
  <required_metrics>
    <metric>strength_in</metric>
    <metric>strength_out</metric>
    <metric>strength_total</metric>
    <metric>degree_in</metric>
    <metric>degree_out</metric>
    <metric>degree_total</metric>
    <metric>pagerank</metric>
    <metric>betweenness</metric>
    <metric>eigenvector_optional</metric>
    <metric>hub_score</metric>
    <metric>bridge_score</metric>
    <metric>route_criticality_score</metric>
  </required_metrics>
  <locked_formulas>
    <hub_score>0.50 * P(strength_total) + 0.30 * P(pagerank) + 0.20 * P(degree_total)</hub_score>
    <bridge_score>P(betweenness)</bridge_score>
    <route_criticality>0.70 * P(analysis_weight) + 0.30 * CrossCommunity</route_criticality>
  </locked_formulas>
  <required_outputs>
    <table>metrics.csv</table>
    <table>route_metrics.csv</table>
  </required_outputs>
  <constraints>
    <constraint>Prefer precomputation</constraint>
    <constraint>Keep formulas interpretable</constraint>
    <constraint>Use percentile scaling for display scores</constraint>
  </constraints>
</prompt>
```

## 16.4 Community detection prompt

```xml
<prompt>
  <role>
    You are the community detection engineer for the ATNA MVP.
  </role>
  <objective>
    Run Leiden on the locked graph representation and generate community artifacts for the UI.
  </objective>
  <inputs>
    <table>edges.csv</table>
  </inputs>
  <algorithm>
    <name>Leiden</name>
    <status>Locked default</status>
  </algorithm>
  <required_outputs>
    <table>communities.csv</table>
    <column_update table="metrics.csv">leiden_community_id</column_update>
  </required_outputs>
  <community_outputs>
    <output>community_size</output>
    <output>community_traffic</output>
    <output>internal_density</output>
    <output>top_hub_airport_ids</output>
    <output>top_bridge_airport_ids</output>
  </community_outputs>
  <constraints>
    <constraint>Do not introduce multiple community algorithms for MVP</constraint>
    <constraint>Keep outputs directly consumable by the Streamlit app</constraint>
  </constraints>
</prompt>
```

## 16.5 Scenario engine prompt

```xml
<prompt>
  <role>
    You are the scenario engine engineer for the ATNA MVP.
  </role>
  <objective>
    Implement airport-removal and route-removal scenarios using the locked 2-hop structural ripple model and impact score formulas.
  </objective>
  <scenario_support>
    <airport_removal>true</airport_removal>
    <route_removal>true</route_removal>
  </scenario_support>
  <locked_ripple_model>
    <undirected_weight>W(i,j) = w(i,j) + w(j,i)</undirected_weight>
    <share>Share(i,j) = W(i,j) / sum_k W(i,k)</share>
    <airport_removal>
      <first_hop>E1(j|r) = Shock(r) * Share(r,j)</first_hop>
      <second_hop>E2(k|r) = lambda * sum_j(E1(j|r) * Share(j,k))</second_hop>
      <total_exposure>Exposure(k|r) = E1 + E2</total_exposure>
    </airport_removal>
    <route_removal>
      <route_shock>Shock(u,v) = 100 * W(u,v) / max_route_weight</route_shock>
      <endpoint_seed>0.5 * shock to each endpoint</endpoint_seed>
    </route_removal>
    <constants>
      <shock_airport>100</shock_airport>
      <lambda>0.35</lambda>
      <max_hops>2</max_hops>
    </constants>
  </locked_ripple_model>
  <locked_scores>
    <lcc_loss>100 * (1 - LCC_post / LCC_pre)</lcc_loss>
    <reachability_loss>100 * (1 - ReachablePairs_post / ReachablePairs_pre)</reachability_loss>
    <ripple_severity>100 * affected_airports_with_exposure_gte_10 / total_airports</ripple_severity>
    <impact_score>0.40 * LCC_Loss + 0.30 * Reachability_Loss + 0.30 * RippleSeverity</impact_score>
    <network_health>100 - ImpactScore</network_health>
  </locked_scores>
  <required_outputs>
    <table>scenarios.csv</table>
    <table>scenario_exposure.csv</table>
  </required_outputs>
  <constraints>
    <constraint>Do not model real-world airline operations</constraint>
    <constraint>Keep the model structural and interpretable</constraint>
  </constraints>
</prompt>
```

## 16.6 Streamlit frontend prompt

```xml
<prompt>
  <role>
    You are the frontend engineer for the ATNA MVP.
  </role>
  <objective>
    Build a Streamlit + Plotly app that presents the locked airport, route, community, and scenario views using precomputed artifacts.
  </objective>
  <required_pages>
    <page>Overview</page>
    <page>Network Map</page>
    <page>Airport Explorer</page>
    <page>Communities</page>
    <page>Route Explorer</page>
    <page>Scenario Editor</page>
    <page>Methodology</page>
  </required_pages>
  <input_artifacts>
    <table>airports.csv</table>
    <table>edges.csv</table>
    <table>nodes.csv</table>
    <table>metrics.csv</table>
    <table>communities.csv</table>
    <table>route_metrics.csv</table>
    <table>scenarios.csv</table>
    <table>scenario_exposure.csv</table>
  </input_artifacts>
  <ui_rules>
    <rule>Prefer fast loading through precomputed tables</rule>
    <rule>Expose month and threshold filters</rule>
    <rule>Show formula explanations in Methodology</rule>
    <rule>Use clear labels for Hub Score, Bridge Score, Impact Score, and Network Health</rule>
  </ui_rules>
  <constraints>
    <constraint>Do not implement unnecessary custom frontend complexity</constraint>
    <constraint>Optimize for a clean demo and clear insight flow</constraint>
  </constraints>
</prompt>
```

## 16.7 QA prompt

```xml
<prompt>
  <role>
    You are the QA and integration engineer for the ATNA MVP.
  </role>
  <objective>
    Validate that all artifacts, metrics, scenario outputs, and UI pages are consistent with the locked MVP specification.
  </objective>
  <validation_targets>
    <target>schema consistency across all tables</target>
    <target>airport and route selections resolve correctly in UI</target>
    <target>community IDs align between metrics and communities outputs</target>
    <target>scenario outputs follow the locked formulas</target>
    <target>second hop ripple is weaker than first hop</target>
    <target>network health decreases when impact score increases</target>
  </validation_targets>
  <required_output>
    <output>Structured QA checklist with pass/fail criteria</output>
  </required_output>
  <constraints>
    <constraint>Flag scope creep separately from implementation bugs</constraint>
    <constraint>Do not approve pages whose methodology text does not match the actual formulas</constraint>
  </constraints>
</prompt>
```

---

# 17. Final Lock Statement

This document locks the ATNA MVP as:

- U.S. domestic only
- monthly directed airport graph
- flight count as default weight
- NetworkX-centered graph workflow
- Leiden communities
- airport and route removals in scenario editor
- 2-hop structural ripple model with lambda 0.35
- precomputed metrics and scenario outputs
- Streamlit + Plotly interface

This is the canonical MVP direction unless the team explicitly approves a later revision.

