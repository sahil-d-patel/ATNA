# Validation against the December 2022 disruption

Every score ATNA produces is a modelling output. This document records the one check
that asks whether those outputs correspond to something that happened.

## The natural experiment

Between 21 and 29 December 2022 a winter storm and a carrier scheduling collapse took
a large share of U.S. domestic capacity offline. The signal in the raw BTS on-time
data is unambiguous:

| Date | Cancellations |
|---|---:|
| Dec 18 | 0.6% |
| Dec 21 | 2.9% |
| **Dec 23** | **27.6%** |
| Dec 26 | 21.7% |
| Dec 29 | 13.6% |
| Dec 30 | 0.7% |

## Method

1. Build the network from **November 2022**, so nothing about the event informs the
   graph. 348 airports, 5,657 directed routes, 540,221 flights.
2. Identify the airports where the disruption originated **from the data itself**,
   ranked by cancellation increase weighted by airport size. No assumption about which
   carrier was involved: BUF, MDW, DAL, LGB, OAK, SMF.
3. Remove those six simultaneously in the two-hop ripple model and record predicted
   exposure for every other airport.
4. Measure observed degradation per airport: cancellation rate over 22–29 December
   against 1–20 December of the same month, so each airport is its own control.
5. Rank-correlate prediction against observation across the 144 airports that clear a
   200-flight control threshold, **excluding the six seeds** — they are the cause, not
   the effect.

## Result

| Measure | Value | p |
|---|---:|---:|
| Spearman ρ, exposure vs observed damage | **+0.387** | 1.6 × 10⁻⁶ |
| Pearson r | +0.289 | 4.5 × 10⁻⁴ |
| **Partial ρ, controlling for airport size** | **+0.386** | 1.8 × 10⁻⁶ |
| Airport size alone vs observed damage | +0.246 | — |

The obvious objection is that large airports both attract more predicted exposure and
cancel more flights in any disruption. They do — size alone correlates at +0.246. But
partialling size out of both variables leaves the relationship essentially untouched,
at +0.386. **Exposure carries information beyond how big an airport is.**

Ten highest-exposure airports, with what actually happened to them:

| Airport | Predicted exposure | Observed change |
|---|---:|---:|
| LAS | 29.8 | +24.2 pp |
| DEN | 28.9 | +26.7 pp |
| PHX | 26.3 | +18.5 pp |
| SLC | 20.9 | +11.5 pp |
| LAX | 18.8 | +11.7 pp |
| HOU | 17.8 | +40.3 pp |
| ATL | 16.8 | +10.3 pp |
| SEA | 15.4 | +16.7 pp |
| SAN | 15.1 | +32.9 pp |

## What this does not establish

- **Geography is a confounder.** The storm hit regionally, and geographic proximity
  correlates with network position. This result cannot separate the two.
- **The model removes; reality degraded.** Southwest did not vanish. Airports serve
  many carriers, so a single-carrier collapse only partly removes any airport.
- **One event.** A single disruption is one observation of the model's behaviour, not
  a track record. The same test on other events would be worth running.
- **Correlation is moderate.** ρ = +0.387 means exposure explains part of the variance
  in who suffered, not most of it.

## Reproducing

```bash
python scripts/download/download_bts_data.py --year 2022 --months 11,12
PYTHONPATH=src python -m etl.run_pipeline --config config/atna-2022-11.yaml
PYTHONPATH=src python scripts/validation/validate_disruption.py \
    --config config/atna-2022-11.yaml \
    --event-on-time data/raw/on_time/2022/on_time_2022_12.csv
```

---

# Stability across snapshots

A score that swings between consecutive months is measuring one month's sampling, not
network structure. Comparing the two real snapshots, over the 345 airports present in
both:

| Score | Spearman ρ, Nov vs Dec 2022 |
|---|---:|
| `hub_score` | **+0.972** |
| `bridge_score` | +0.912 |
| `vulnerability_score` | +0.963 |

The rankings are stable. That holds even though December 2022 contained the largest
domestic disruption in years, which is the right outcome: the metrics describe the
route network, and the network did not change shape because a week of flights was
cancelled.

## The exceptions have a reason

The airports that moved most are the useful part of this check, because an aggregate
correlation hides them.

| Airport | Nov | Dec | Change |
|---|---:|---:|---:|
| HDN — Hayden / Steamboat Springs | 19.3 | 64.5 | **+45.2** |
| EGE — Eagle / Vail | 34.0 | 66.9 | +32.9 |
| GUC — Gunnison / Crested Butte | 7.8 | 38.0 | +30.2 |
| MTJ — Montrose / Telluride | 34.4 | 62.3 | +27.9 |
| PAH — Paducah | 35.1 | 4.7 | −30.4 |
| HIB — Hibbing | 36.3 | 8.2 | −28.1 |

The four largest gains are all Colorado ski airports, which pick up seasonal service in
December. That is the behaviour a structural metric should show: stable where the
network is stable, moving where service genuinely changed.

## Reproducing

```bash
PYTHONPATH=src python scripts/validation/snapshot_stability.py \
    --baseline 2022-11 --comparison 2022-12
```
