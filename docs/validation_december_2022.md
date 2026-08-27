# Validation against real disruptions

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
| Spearman ρ, exposure vs observed damage | **+0.411** | 3.1 × 10⁻⁷ |
| Pearson r | +0.347 | 2.1 × 10⁻⁵ |
| **Partial ρ, controlling for airport size** | **+0.457** | 8.3 × 10⁻⁹ |
| Airport size alone vs observed damage | +0.246 | — |

The obvious objection is that large airports both attract more predicted exposure and
cancel more flights in any disruption. They do — size alone correlates at +0.246. But
partialling size out of both variables leaves the relationship essentially untouched,
at +0.457. **Exposure carries information beyond how big an airport is.**

## The event also corrected the model

This test is not only a scorecard; it selected between candidate formulations of the
ripple model. Four combinations of shock rule and severity rule were measured against
it:

| Formulation | Distinct values | Hubs in top 10 | ρ | Partial ρ |
|---|---:|---:|---:|---:|
| Fixed shock, count ≥ 10 (original) | 9 | 0 | +0.387 | +0.386 |
| Fixed shock, traffic-weighted | 332 | 0 | +0.387 | +0.386 |
| Strength shock, count ≥ 10 | 1 | 0 | +0.411 | +0.457 |
| **Strength shock, traffic-weighted** | **332** | **9** | **+0.411** | **+0.457** |

Only the adopted pair both discriminates between airports and agrees better with what
happened. Neither change was argued into place; both were measured.

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


---

# Second event: the January 2023 FAA outage

One event is an observation, not a track record. The obvious question is whether the
December result generalises or fits that event, so the harness was pointed at a second
disruption with a **different failure mode**.

On 11 January 2023 an FAA NOTAM system failure grounded departures nationwide.
Cancellations went from a ~0.5% baseline to **6.96%** on the day and returned
immediately:

| Date | Cancellations |
|---|---:|
| Jan 9 | 0.69% |
| Jan 10 | 1.01% |
| **Jan 11** | **6.96%** |
| Jan 12 | 0.67% |
| Jan 13 | 0.46% |

Same method: network built from **December 2022**, seeds chosen from the observed data,
event window 11–12 January against a 1–10 January control.

## Result

| Measure | Dec 2022 | Jan 2023 |
|---|---:|---:|
| Airports tested | 144 | 98 |
| Spearman ρ | **+0.411** (p = 3.1 × 10⁻⁷) | **+0.206** (p = 0.042) |
| Partial ρ, size controlled | **+0.457** (p = 8.3 × 10⁻⁹) | **+0.302** (p = 0.0025) |
| Airport size alone | +0.246 | **−0.073** |

The signal is real but weaker, and the reason is informative rather than
disappointing.

## Why the second event is weaker, and what that tells you

The two disruptions fail differently:

- **December 2022** was a *propagating* failure. A carrier's scheduling collapsed at
  specific airports and the damage spread outward through the routes connecting them.
  That is precisely what a two-hop ripple over route dependencies models, and the
  correlation is correspondingly strong.
- **January 2023** was a *uniform* failure. A national system went down and grounded
  departures everywhere at once. Nothing propagated through the network, because the
  network was not the transmission mechanism.

That the correlation survives at all on a uniform outage is notable, and the size
column explains why it is worth reporting: **airport size carries essentially no
information about who suffered on 11 January (−0.073), while network position still
does (+0.302).** Controlling for size *raises* the correlation here, the opposite of
December.

**The honest reading:** ATNA predicts disruptions that spread through the route
network. It predicts them well when spreading is the mechanism, and weakly when it is
not. That is a boundary on the model's claim, established by measurement rather than
asserted.

## Reproducing

```bash
python scripts/download/download_bts_data.py --year 2023 --months 1 --only on_time
PYTHONPATH=src python scripts/validation/validate_disruption.py \
    --config config/atna-2022-12.yaml \
    --event-on-time data/raw/on_time/2023/on_time_2023_01.csv \
    --event-days 11-12 --control-days 1-10
```
