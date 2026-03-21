# Phase 1 Work - Airport Hub Analysis

This directory contains data and analysis scripts for identifying major airport hubs in the US airline transportation network.

## Contents

### Data Files

#### Input Data
- **`T_ONTIME_REPORTING.csv`** (539,748 records)
  - Flight on-time reporting data
  - Columns: `YEAR`, `QUARTER`, `MONTH`, `DAY_OF_MONTH`, `DAY_OF_WEEK`, `FL_DATE`, `ORIGIN_AIRPORT_ID`, `ORIGIN`, `DEST_AIRPORT_ID`, `FLIGHTS`
  - Each row represents flight activity on a specific date between an origin and destination
  - Contains 2025 flight data (January)

- **`T_MASTER_CORD.csv`** (20,230 records, 6,850 current airports)
  - Airport master coordinate and metadata file
  - Columns: `AIRPORT_ID`, `DISPLAY_AIRPORT_NAME`, `DISPLAY_AIRPORT_CITY_NAME_FULL`, location data, etc.
  - Includes historical records (use `AIRPORT_IS_LATEST=1` for current airports)
  - Contains geographic coordinates, state, and full airport information

#### Output Data
- **`airport_hubs_ranked.csv`** (329 airports)
  - Airports ranked by **total throughput** (departures + arrivals)
  - Standard industry metric for hub identification
  - Columns: `RANK`, `AIRPORT_ID`, `AIRPORT_CODE`, `AIRPORT_NAME`, `CITY`, `DEPARTURES`, `ARRIVALS`, `TOTAL_THROUGHPUT`

- **`airport_balanced_hubs_ranked.csv`** (329 airports)
  - Airports ranked by **min(departures, arrivals)**
  - Identifies hubs with balanced bidirectional traffic, penalizing "destination" or "arrival" airports since we want to know the big hubs that are the most connected instead of the source and sink nodes
  - Additional columns: `MIN_FLOW`, `BALANCE_RATIO`
  - Balance ratio indicates how evenly traffic flows both ways (100% = perfectly balanced)

### Analysis Scripts

#### `analyze_airport_hubs.py`
Identifies major airport hubs using total throughput metric.

**Usage:**
```bash
python3 analyze_airport_hubs.py
```

**What it does:**
1. Loads flight data from `T_ONTIME_REPORTING.csv`
2. Aggregates total departures and arrivals per airport
3. Calculates total throughput (sum of both)
4. Enriches with airport names and locations from `T_MASTER_CORD.csv`
5. Outputs ranked results to `airport_hubs_ranked.csv`
6. Displays top 20 airports in console

**Requirements:**
- Python 3.x
- pandas library (`pip install pandas`)

#### `analyze_balanced_hubs.py`
Identifies airports with balanced bidirectional traffic flows.

**Usage:**
```bash
python3 analyze_balanced_hubs.py
```

**What it does:**
1. Loads flight data from `T_ONTIME_REPORTING.csv`
2. Calculates departures and arrivals per airport
3. Computes min(departures, arrivals) as the balanced flow metric
4. Calculates balance ratio to show traffic symmetry
5. Outputs ranked results to `airport_balanced_hubs_ranked.csv`
6. Displays top 20 balanced hubs in console

**Requirements:**
- Python 3.x
- pandas library (`pip install pandas`)

## Key Findings

### Top 10 Airport Hubs (by Total Throughput)

| Rank | Airport | Code | City | Total Flights |
|------|---------|------|------|---------------|
| 1 | Dallas/Fort Worth International | DFW | Dallas/Fort Worth, TX | 50,249 |
| 2 | Denver International | DEN | Denver, CO | 49,472 |
| 3 | Hartsfield-Jackson Atlanta International | ATL | Atlanta, GA | 47,762 |
| 4 | Chicago O'Hare International | ORD | Chicago, IL | 43,284 |
| 5 | Charlotte Douglas International | CLT | Charlotte, NC | 33,760 |
| 6 | Phoenix Sky Harbor International | PHX | Phoenix, AZ | 31,905 |
| 7 | Los Angeles International | LAX | Los Angeles, CA | 30,300 |
| 8 | Harry Reid International | LAS | Las Vegas, NV | 30,011 |
| 9 | Orlando International | MCO | Orlando, FL | 26,110 |
| 10 | Seattle/Tacoma International | SEA | Seattle, WA | 23,775 |

### Analysis Insights

**Total Network Statistics:**
- Total airports analyzed: 329
- Total flights processed: 1,079,494
- Data period: January 2025

**Metric Comparison:**
- Both throughput and min-flow metrics produce identical top-20 rankings
- Major US hubs show 99.95-100% balance ratios
- This indicates commercial aviation naturally balances inbound/outbound traffic
- Aircraft must return to base, creating symmetric traffic patterns

**Hub Characteristics:**
- Top hubs serve as major connection points for passenger traffic
- Geographic distribution covers major US regions (South, Midwest, West, East Coast)
- DFW, DEN, and ATL are the three dominant super-hubs
- All top-20 airports handle over 14,000 flights per month

## Methodology

### Total Throughput Metric
```
Total Throughput = Departures + Arrivals
```
- **Best for:** Identifying busiest airports overall
- **Use case:** Capacity planning, infrastructure investment, general hub identification

### Balanced Flow Metric
```
Balanced Flow = min(Departures, Arrivals)
Balance Ratio = (MIN_FLOW / (Total/2)) × 100%
```
- **Best for:** Identifying true connecting hubs with symmetric traffic
- **Use case:** Finding airports where traffic flows equally in both directions
- **Note:** Less useful when all airports are naturally balanced (like in this dataset)

## Data Source

Data appears to be from the Bureau of Transportation Statistics (BTS) Airline On-Time Performance dataset, covering scheduled domestic flights in the United States.

## Future Analysis Opportunities

1. **Temporal Analysis**: Analyze hub patterns by quarter or season
2. **Route Density**: Count unique destination pairs per hub
3. **Geographic Clustering**: Analyze hub distribution by region
4. **Market Concentration**: Calculate market share by airline per hub
5. **Connection Efficiency**: Identify which hubs provide the most route options
6. **Imbalance Detection**: Find airports where min() differs significantly from average (tourist destinations, cargo hubs)

## Author

Shalya Jha and Claude Sonnet
