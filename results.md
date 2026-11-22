# Results: BoE words vs SONIA pricing

_Generated 2026-11-21 by `src/analyse.py` from cached BoE downloads in `data/raw/`._

## Data

- **MPC decisions:** 73 (announcements 2018-02-08 to 2026-11-05), including the two March 2020 special meetings. Text = Monetary Policy Summary + Minutes (72 from the official PDF, 1 from HTML).
- **Scored:** 72 decisions (19 Mar 2020 special excluded: only a ~470-word summary exists; its minutes were published jointly with 26 Mar 2020).
- **Vote splits:** parsed from the minutes for all 73 decisions. Every parsed dissent count matches the headline split (e.g. 7-2), and every Bank Rate change matches the rate path. One manual override, documented in `src/parse.py`: Aug 2025's two-round vote.
- **OIS:** BoE SONIA OIS spot curve (6m, 1y, 2y), 2394 business days, 2017-06-01 to 2026-11-19. Source: the `oisddata.zip` archive plus `latest-yield-curve-data.zip`.

## Headline stats

| Test | Result |
|---|---|
| Score vs net hawkish-dissent count (level) | Pearson r = 0.31 (p = 0.008), Spearman = 0.27, n = 72 |
| Score vs committee mean preferred move, bp | Pearson r = 0.42 (p = 0.000), Spearman = 0.55, n = 72 |
| Change in score vs change in net hawkish dissent | Pearson r = 0.17 (p = 0.153), n = 71 |
| Surprise regression: d1y OIS (bp) on d score | coef = +0.27 bp per point, t = 1.45 (HC1 t = 0.68), R^2 = 0.029, n = 71 |
| Surprise regression: d2y OIS (bp) on d score | coef = +0.23 bp per point, t = 1.13 (HC1 t = 0.53), R^2 = 0.018, n = 71 |
| Surprise regression: d6m OIS (bp) on d score | coef = +0.17 bp per point, t = 1.10 (HC1 t = 0.65), R^2 = 0.017, n = 71 |
| Surprise regression: d1y OIS, ex-Mar 2020 (bp) on d score | coef = +0.28 bp per point, t = 1.47 (HC1 t = 0.69), R^2 = 0.031, n = 69 |
| Benchmark: d1y OIS on change in net hawkish dissent | coef = +0.37 bp per dissenter, t = 1.06 (HC1 t = 0.82), R^2 = 0.016, n = 72 |

**Reading.** The lexicon score tracks the vote split (r = 0.31 on levels). The words-to-pricing link on announcement day is weak and not significant at 5%: R^2 = 0.029 for 1y OIS. A one-SD change in the score (5.0 points) maps to about +1.3bp in 1y OIS. Most of the day's move is driven by things this score does not capture: the decision versus expectations, the vote split versus expectations, the MPR projections, and the press conference.

## Divergences

Rule: the hawk score moved by at least 0.5 SD (2.51 points) versus the prior meeting, and 1y OIS moved at least 5bp the opposite way (close before to close after). **5 of 71 eligible meetings are flagged.**

| Announced | Decision | Vote | Dissent (pref. vs decision) | d score | d 6m | d 1y | d 2y | Type |
|---|---|---|---|---|---|---|---|---|
| 2022-03-17 | hike +25bp to 0.75% | 8-1 | 1x+0bp | +4.50 | -13.8 | -17.2 | -18.0 | words hawkish, 1y OIS fell |
| 2023-08-03 | hike +25bp to 5.25% | 6-3 | 2x+50bp; 1x+0bp | +5.40 | -7.4 | -5.8 | -6.3 | words hawkish, 1y OIS fell |
| 2024-08-01 | cut -25bp to 5% | 5-4 | 4x+0bp | +11.40 | -8.5 | -11.4 | -14.9 | words hawkish, 1y OIS fell |
| 2025-08-07 | cut -25bp to 4% | 5-4 | 4x+0bp | -8.00 | +2.6 | +5.1 | +4.8 | words dovish, 1y OIS rose |
| 2026-07-30 | hold +0bp to 3.75% | 6-3 | 3x+25bp | +5.66 | -7.0 | -10.8 | -12.7 | words hawkish, 1y OIS fell |

In the dissent column, `4x+0bp` means four members preferred no change.

## Current reading

- **Latest decision: 2026-11-05.** Hike +25bp, vote 8-1 (dissent: 1x+50bp).
- **Hawk score +9.27.** That is the 97th percentile of 72 scored meetings since 2018 (rank 3 most hawkish), z = +1.68, change versus the prior meeting +2.46. The most hawkish on record is 2024-08 (+14.20).
- **Pricing.** 1y OIS moved +4.2bp and 2y +2.0bp on the day. Latest curve (2026-11-19): 1y 4.56%, 2y 4.75%.
- **Top phrases:** second-round effect*(+)20; persist*(+)12; slack(-)11; weak*(-)9; resilien*(+)8; increase in bank rate(+)7

## All meetings

Full table: `data/processed/events.csv`.

| Announced | Dec. bp | Vote | Net hawk dissent | Score | d score | d 1y bp | d 2y bp |
|---|---|---|---|---|---|---|---|
| 2018-02-08 | +0 | 9-0 | +0 | +3.44 | n/a | +4.4 | +5.2 |
| 2018-03-22 | +0 | 7-2 | +2 | +0.22 | -3.22 | -1.1 | -3.3 |
| 2018-05-10 | +0 | 7-2 | +2 | -3.21 | -3.43 | -4.1 | -4.5 |
| 2018-06-21 | +0 | 6-3 | +3 | -2.65 | +0.57 | +2.1 | +0.8 |
| 2018-08-02 | +25 | 9-0 | +0 | -1.19 | +1.45 | +0.2 | -0.6 |
| 2018-09-13 | +0 | 9-0 | +0 | +1.34 | +2.53 | +0.2 | +0.6 |
| 2018-11-01 | +0 | 9-0 | +0 | -3.32 | -4.65 | +0.8 | +1.5 |
| 2018-12-20 | +0 | 9-0 | +0 | -6.02 | -2.70 | -0.9 | -0.4 |
| 2019-02-07 | +0 | 9-0 | +0 | -7.20 | -1.18 | -2.4 | -2.7 |
| 2019-03-21 | +0 | 9-0 | +0 | -8.90 | -1.70 | -4.0 | -6.8 |
| 2019-05-02 | +0 | 9-0 | +0 | +0.19 | +9.09 | -0.4 | +0.9 |
| 2019-06-20 | +0 | 9-0 | +0 | -4.88 | -5.07 | -3.9 | -5.9 |
| 2019-08-01 | +0 | 9-0 | +0 | -3.51 | +1.37 | +0.4 | -0.7 |
| 2019-09-19 | +0 | 9-0 | +0 | -8.78 | -5.27 | +0.1 | -0.3 |
| 2019-11-07 | +0 | 7-2 | -2 | -10.15 | -1.36 | -2.5 | -0.7 |
| 2019-12-19 | +0 | 7-2 | -2 | -8.53 | +1.62 | +2.4 | +2.3 |
| 2020-01-30 | +0 | 7-2 | -2 | -6.58 | +1.94 | +8.6 | +6.9 |
| 2020-03-11 | -50 | 9-0 | +0 | -6.97 | -0.39 | -10.6 | -6.5 |
| 2020-03-19 | -15 | 9-0 | +0 | n/a | n/a | -9.2 | -7.0 |
| 2020-03-26 | +0 | 9-0 | +0 | -1.60 | +5.37 | -2.2 | -0.2 |
| 2020-05-07 | +0 | 9-0 | +0 | -3.17 | -1.57 | +0.4 | -0.5 |
| 2020-06-18 | +0 | 9-0 | +0 | -4.08 | -0.91 | +0.6 | +0.5 |
| 2020-08-06 | +0 | 9-0 | +0 | -2.72 | +1.36 | +3.1 | +3.4 |
| 2020-09-17 | +0 | 9-0 | +0 | -3.17 | -0.44 | -2.8 | -4.7 |
| 2020-11-05 | +0 | 9-0 | +0 | -6.63 | -3.46 | +0.9 | +0.9 |
| 2020-12-17 | +0 | 9-0 | +0 | -5.01 | +1.62 | -0.1 | -0.1 |
| 2021-02-04 | +0 | 9-0 | +0 | -2.72 | +2.29 | +2.9 | +3.6 |
| 2021-03-18 | +0 | 9-0 | +0 | -6.71 | -3.99 | +0.2 | +0.7 |
| 2021-05-06 | +0 | 9-0 | +0 | -2.90 | +3.81 | -0.2 | -1.6 |
| 2021-06-24 | +0 | 9-0 | +0 | +0.00 | +2.90 | -0.8 | -1.8 |
| 2021-08-05 | +0 | 9-0 | +0 | +1.98 | +1.98 | +1.8 | +2.3 |
| 2021-09-23 | +0 | 9-0 | +0 | +3.44 | +1.46 | +7.2 | +9.6 |
| 2021-11-04 | +0 | 7-2 | +2 | +0.75 | -2.69 | -20.8 | -22.1 |
| 2021-12-16 | +15 | 8-1 | -1 | +2.85 | +2.10 | +4.4 | +3.7 |
| 2022-02-03 | +25 | 5-4 | +4 | +1.23 | -1.63 | +18.4 | +15.6 |
| 2022-03-17 | +25 | 8-1 | -1 | +5.73 | +4.50 | -17.2 | -18.0 |
| 2022-05-05 | +25 | 6-3 | +3 | +3.71 | -2.02 | -12.7 | -13.0 |
| 2022-06-16 | +25 | 6-3 | +3 | +6.68 | +2.97 | +9.2 | +7.5 |
| 2022-08-04 | +50 | 8-1 | -1 | +3.31 | -3.37 | +1.4 | -1.9 |
| 2022-09-22 | +50 | 5-4 | +2 | +1.64 | -1.67 | -3.5 | +5.2 |
| 2022-11-03 | +75 | 7-2 | -2 | +0.00 | -1.64 | +5.3 | +5.6 |
| 2022-12-15 | +50 | 6-3 | -1 | -1.40 | -1.40 | -3.6 | -3.7 |
| 2023-02-02 | +50 | 7-2 | -2 | +0.41 | +1.81 | -10.3 | -21.1 |
| 2023-03-23 | +25 | 7-2 | -2 | -0.16 | -0.57 | -11.5 | -22.2 |
| 2023-05-11 | +25 | 7-2 | -2 | +8.14 | +8.31 | -2.3 | -8.1 |
| 2023-06-22 | +50 | 7-2 | -2 | +6.36 | -1.78 | +13.7 | +4.1 |
| 2023-08-03 | +25 | 6-3 | +1 | +11.77 | +5.40 | -5.8 | -6.3 |
| 2023-09-21 | +0 | 5-4 | +4 | +2.29 | -9.48 | -3.5 | -1.1 |
| 2023-11-02 | +0 | 6-3 | +3 | +6.56 | +4.28 | -2.1 | -6.3 |
| 2023-12-14 | +0 | 6-3 | +3 | +1.88 | -4.69 | -2.8 | -7.0 |
| 2024-02-01 | +0 | 6-3 | +1 | +1.40 | -0.48 | +2.9 | -0.5 |
| 2024-03-21 | +0 | 8-1 | -1 | +2.68 | +1.29 | -6.6 | -9.6 |
| 2024-05-09 | +0 | 7-2 | -2 | +4.62 | +1.93 | -4.0 | -7.2 |
| 2024-06-20 | +0 | 7-2 | -2 | +2.80 | -1.82 | -5.6 | -5.5 |
| 2024-08-01 | -25 | 5-4 | +4 | +14.20 | +11.40 | -11.4 | -14.9 |
| 2024-09-19 | +0 | 8-1 | -1 | -3.52 | -17.72 | +3.1 | +1.8 |
| 2024-11-07 | -25 | 8-1 | +1 | -1.32 | +2.20 | -2.0 | -7.0 |
| 2024-12-19 | +0 | 6-3 | -3 | -0.97 | +0.36 | -2.8 | -3.3 |
| 2025-02-06 | -25 | 7-2 | -2 | -1.14 | -0.17 | -1.9 | +0.4 |
| 2025-03-20 | +0 | 8-1 | -1 | -0.59 | +0.55 | +3.1 | +1.6 |
| 2025-05-08 | -25 | 5-4 | +0 | -1.42 | -0.84 | +11.5 | +10.7 |
| 2025-06-19 | +0 | 6-3 | -3 | -6.87 | -5.44 | -0.3 | +0.7 |
| 2025-08-07 | -25 | 5-4 | +4 | -14.87 | -8.00 | +5.1 | +4.8 |
| 2025-09-18 | +0 | 7-2 | -2 | -6.96 | +7.91 | -0.7 | -1.3 |
| 2025-11-06 | +0 | 5-4 | -4 | -16.07 | -9.11 | -0.5 | -2.0 |
| 2025-12-18 | -25 | 5-4 | +4 | -12.39 | +3.68 | +3.1 | +2.7 |
| 2026-02-05 | +0 | 5-4 | -4 | -16.27 | -3.88 | -6.3 | -5.8 |
| 2026-03-19 | +0 | 9-0 | +0 | +2.94 | +19.22 | +37.4 | +39.4 |
| 2026-04-30 | +0 | 8-1 | +1 | +5.34 | +2.40 | -8.9 | -12.2 |
| 2026-06-18 | +0 | 7-2 | +2 | +2.68 | -2.66 | +1.2 | +2.2 |
| 2026-07-30 | +0 | 6-3 | +3 | +8.33 | +5.66 | -10.8 | -12.7 |
| 2026-09-17 | +0 | 6-3 | +3 | +6.81 | -1.53 | +2.6 | +3.4 |
| 2026-11-05 | +25 | 8-1 | +1 | +9.27 | +2.46 | +4.2 | +2.0 |

## Limitations

- **Daily close-to-close window.** BoE curve estimates are end-of-day. Data releases and global moves on the same day contaminate the window, and an intraday window around 12:00 is not available from public BoE data.
- **No expectations baseline.** The score change versus the prior meeting is a crude proxy for surprise. Market expectations of the decision and the vote are not modelled, and these dominate the day's move.
- **Bag of phrases.** The lexicon (`lexicon.csv`, 104 phrases) was written before any results were seen and was not tuned to them. It cannot read conditionality ('if X persists, then...'), attribution (whether a phrase is the Committee's view or one member's), or sterling direction ('weaker sterling' is inflationary but scores dovish). Minutes length and format changed a lot over time: 2024+ minutes are shorter and include per-member views.
- **What gets scored.** Summary and Minutes only, not the MPR or the press conference. On 26 Mar 2020 the PDF combines the minutes of the 19 Mar special meeting and the 25 Mar meeting.
- **Vote anchor is Bank Rate only.** QE and QT dissents (e.g. Haldane in 2020-21, the Sep 2025 QT split) are not counted.
- **Sample size.** n is about 70 decisions, spanning very different regimes (the ZLB, COVID, 2022 hiking, 2024-25 cutting, the 2026 energy shock). The divergence thresholds are judgement calls and are set as constants in `src/analyse.py`.
