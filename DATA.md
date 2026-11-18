# DATA.md

Source, findings and handling rules for every dataset in this project.
Raw data is not committed (`data/` is git-ignored). Settings live in `config/config.yaml`.

> History: rebuilt on 17 Nov 2026 from the README (section 5.1) plus the feature-source reviews. Updated on 18 Nov 2026 with the profiled Demand Data Update file and the licence review.

---

## 1. Day-ahead prices (target)

- **Dataset:** "Day-Ahead Power Exchange prices (Nord Pool)", NESO data portal. Dataset id `day-ahead-power-exchange-prices-nordpool`. Updated daily.
- **Data file:** "N2EX GB Day-Ahead Price" (CSV, columns `Date`, `Delivery Period`, `Price`). Resource id `4f27eea5-7038-4f73-9740-e3e4ad47c26a`.
- **Saved as:** `data/raw/neso_n2ex_gb_da.csv`
- **Retrieval date:** 17 Nov 2026 `[change if you downloaded it on a different day]`
- **Licence:** NESO Open Data Licence v1.0 (the dataset page lists its rights as this licence). Based on the Open Government Licence v3.0. Free to copy, publish, adapt and use commercially, including by combining with other data.
- **Required attribution:** "Supported by National Energy SO Open Data". Must appear in the README and anywhere results are published.
- **Other licence conditions:** protect NESO's logos and trademarks, do not suggest NESO endorses the project. Data is provided as-is with no warranty. NESO can revise the licence without notice, so keep the retrieval date.
- **Redistribution:** the licence would permit it with attribution. Raw data is kept out of git as a project choice (size, reproducibility from config), not a licence requirement.
- **Licence page:** https://www.neso.energy/data-portal/neso-open-licence
- **Timezone:** **UTC (confirmed)**
- **Units:** **GBP/MWh (confirmed)**
- **Not the target:** Elexon's Market Index Price is not the day-ahead auction price and is never used as the target.

### Verified by script

| Check | Result |
|---|---|
| Rows | 45,217 hourly periods |
| First / last period | 2021-09-20 22:00 / 2026-11-17 22:00 |
| Missing, duplicate or gapped periods | None |
| Rows per calendar date | Exactly 24, including UK clock-change days |
| Complete GB delivery days | 1,883 (two truncated edge days excluded) |
| Negative-price hours | 591 |
| Price range | -54.17 to 2,000.05 |

### Handling rules

| Issue | Rule |
|---|---|
| Labels are a continuous UTC clock, not UK local time | Load as UTC. Derive the GB delivery day in `Europe/London`, so some delivery days have 23 or 25 hours. |
| Truncated first and last day | Excluded from backtests, never mistaken for clock-change days. |
| Regimes: about 198-204 GBP/MWh in 2021-22 vs 73-113 from 2023 to 2026 | Run models and battery results with and without 2021-22. |
| Negative prices and spikes | Keep them. Report error and value for these periods separately. |
| Refreshing the CSV | Two tests assert on the last date of the current file (2026-11-17). Update them when the file is refreshed. |

---

## 2. Feature sources (reviewed 17-18 Nov 2026, not yet ingested)

### 2.1 NESO Demand Data Update

- **Page:** https://www.neso.energy/data-portal/daily-demand-update/demand_data_update
- **Access:** CSV download or CKAN API (`api.neso.energy`), no key seen.
- **Retrieved:** 18 Nov 2026. Suggested local path: `data/raw/demand_data_update_2026-11-18.csv` (ignored by git).
- **Coverage (profiled file):** 1 Oct to 24 Nov 2026, 2,641 rows, 23 columns, no missing values. Outturn (`A`) rows run to 18 Nov period 16 (2,321 rows). Forecast (`F`) rows run from 18 Nov period 17 to 24 Nov (320 rows). Usually updated daily by 08:30 UTC.
- **Resolution:** half-hourly settlement periods. `SETTLEMENT_DATE` and `SETTLEMENT_PERIOD` (period 1 = 00:00-00:30). **Local settlement time confirmed:** 25 Oct 2026 has 50 periods (autumn clock change). One other date has 47 rows and has not been traced. `[check before ingest]`
- **Useful columns:** `ND`, `TSD` (MW); `FORECAST_ACTUAL_INDICATOR` (A or F); `EMBEDDED_WIND_GENERATION`, `EMBEDDED_WIND_CAPACITY`, `EMBEDDED_SOLAR_GENERATION`, `EMBEDDED_SOLAR_CAPACITY`.
- **Interconnector flows** (`IFA_FLOW`, `BRITNED_FLOW`, etc.) are outturn. Not allowed as day-ahead features (leakage).
- **Licence:** NESO Open Data Licence v1.0, same terms and attribution as section 1. Licence text reviewed 18 Nov 2026. The licence page says each dataset is licensed individually; the dataset's own "Rights" field was checked on 18 Nov 2026 and reads "NESO Open Data Licence", linking to the licence page above (v1.0).
- **Attribution used:** "Supported by National Energy SO Open Data". NESO logos and trademarks are not used and no endorsement by NESO is implied.

| Issue | Rule |
|---|---|
| Rolling window only (about 7 weeks in the profiled file): cannot give 2021-2026 history | Do not use for training. Find a long-history source (NESO historic demand dataset, `[check coverage]`). Use this dataset for recent or live checks only. |
| `F` rows carry embedded wind and solar only: `ND`, `TSD` and `ENGLAND_WALES_DEMAND` are zero in every forecast row | There is no demand forecast in this file. Source demand forecasts from NESO "Historic Day Ahead Demand Forecasts". |
| Half-hourly local-time settlement periods | Convert to UTC timestamps first, then aggregate to hourly (mean MW). Clock-change days have 46 or 50 periods: test explicitly, as for prices. |
| `F` rows are an overwritten snapshot with no publication time | Cannot prove what was known at D-1 gate closure. Treat as a limitation, or log snapshots daily from now on. |
| `EMBEDDED_WIND_CAPACITY` differs between actual and forecast rows (6417 early in the file vs 5908 in forecast rows) | Probably an estimation change. Do not use as a clean feature until understood. |
| Embedded wind and solar are modelled estimates | Label as NESO estimates, not metered output. |
| No transmission-metered wind | Source separately (Elexon Insights / BMRS), `[check]`. |

### 2.2 Open-Meteo, UK Met Office (UKMO) forecasts

- **Page:** https://open-meteo.com/en/docs/ukmo-api
- **Access:** free for non-commercial use, no key.
- **Models:** `ukmo_seamless` (UKV 2 km for UK and Ireland, hourly, 2-day horizon; Global 10 km, 7 days).
- **Licence:** UKMO data is **CC BY-SA 4.0**. Any derived data product shared must carry the same or a compatible licence, with attribution. The code licence is chosen separately.
- **Known limits:** extra ~4 hour publication delay for UKMO open data; solar radiation only out to a 2-day horizon; wind at 100 m and above is UKV-only.
- **Archived history: 93 days at most (confirmed 17 Nov 2026).** It cannot supply archived forecasts for the 2021-2026 price history. See section 3.

| Issue | Rule |
|---|---|
| Time zone default | Always request `timezone=UTC` so keys match the price table. |
| Wind speed default is km/h | Request m/s explicitly. |
| Look-ahead bias | Use archived forecast runs, not observed or reanalysis weather, wherever possible. |
| GB is one price zone, weather is local | Choose representative points and weights, document them in config. |
| Publication delay | Apply the 4-hour delay (`extra_source_delay_hours.ukmo`) in the cut-off function. |

---

## 3. Decision needed: weather history (before week 3)

UKMO via Open-Meteo covers only the last 93 days, so it cannot be a training feature across the full price history. Options, in the order to check them:

1. **Published day-ahead forecasts with publication times** (demand, wind, solar from Elexon Insights / BMRS and NESO). Best fit for the no-look-ahead rule. **Promising lead found for demand:** NESO's "Historic Day Ahead Demand Forecasts" (NESO Open Data Licence) is described as all historic day-ahead demand forecasts from 2018, and its example shows a timestamp field (publication time, to be confirmed). NESO says the day-ahead national demand forecast is published twice daily, at about 09:00-09:15 and 12:00-12:15 clock time. Only the earlier one can be used, and only if it is before gate closure `[verify against the gate-closure time]`. `[check: field names, publication timestamps, coverage; wind and solar still to find]`
2. **Other Open-Meteo models via the Historical Forecast API.** Archived forecasts, but from a different model. `[check: start date and licence per model]`
3. **Reanalysis (observed-style weather).** Long history, but it is not what was known at D-1, so forecast accuracy and battery value will look better than they would live. If used, label it as an optimistic proxy in the README limitations, and consider adding noise to mimic forecast error.
4. **Keep the 93-day UKMO window** only for a live or recent sanity check, not for training.

Record the choice here, in `config.yaml` (`features.weather.history_approach`), and in the README (section 5.2 weather row and the limitations list).

---

## 4. Open items

- [x] Price file timezone: UTC
- [x] Price units: GBP/MWh
- [x] Price dataset name, retrieval date, licence (NESO Open Data Licence v1.0)
- [x] NESO demand licence: Rights field checked on the dataset page (18 Nov 2026), NESO Open Data Licence v1.0
- [x] Demand Data Update file profiled (18 Nov 2026): rolling window, not a training source
- [x] Add the NESO attribution line to the README acknowledgements
- [ ] Gate-closure time (needed before week 3)
- [ ] Weather-history approach (section 3, needed before week 3)
- [ ] Trace the date with 47 rows in the Demand Data Update file, and map settlement periods to UTC (week 3)
- [ ] Understand the `EMBEDDED_WIND_CAPACITY` change between actual and forecast rows (week 3)
