# DATA.md

Source, findings and handling rules for every dataset in this project.
Raw data is not committed (`data/` is git-ignored). Settings live in `config/config.yaml`.

> History: rebuilt on 17 Nov 2026. Updated 18 Nov 2026 (Demand Data Update profile, licence review) and 25 Nov 2026 (week 3: feature sources ingested, cut-off rule, weather decision, feature table).

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

## 2. Information cut-off (applies to every feature)

- **Rule:** a feature for delivery day D may use only information published at or before **09:50 UK clock time on D-1**, the N2EX day-ahead gate closure (confirmed by the project owner). Set in `config.yaml` as `gate_closure_local: "09:50"` with `forecast_cutoff_buffer_minutes: 0`.
- **Code:** `src/ingest/cutoff.py` builds 09:50 as UK wall-clock time and converts to UTC (08:50 UTC in summer, 09:50 UTC in winter).
- **Proof:** every row of the feature table carries each source's issue time and the cut-off. `check_no_leakage` in `src/features/build.py` fails if any issue time is later than the cut-off; `tests/test_features.py` runs it on every `pytest`.
- **Optimism note:** some forecasts are issued only minutes before 09:50. A real trader may not act on them that fast, so a buffer is a planned sensitivity.

---

## 3. Feature sources used (ingested in week 3)

### 3.1 NESO day-ahead demand forecast

- **Dataset / file:** NESO "Day Ahead Demand Forecast", file "Historic Day Ahead Demand Forecasts" (2018 onwards). Retrieved 21 Nov 2026. NESO Open Data Licence v1.0 `[confirm the Rights field on the dataset page]`.
- **Saved as:** `data/raw/archive_1dayahead.csv` (path set in `src/ingest/demand.py`).
- **Format:** about 11 "cardinal points" per target day (fixed times, daily peaks and troughs), columns include `TARGETDATE`, `FORECASTDEMAND` (MW), `CARDINALPOINT`, `CP_TYPE`, `CP_ST_TIME`, `FORECAST_TIMESTAMP`.
- **Publication time:** `FORECAST_TIMESTAMP` (UTC, `Z` suffix). Usually two issues a day (about 08:40 and 11:45 UTC); only the earlier can pass the cut-off.

| Issue | Rule |
|---|---|
| Several issues per day | Keep the latest issue at or before the cut-off. |
| No usable issue for some days | Drop the day. 30 of 1,416 price days from 2023 dropped; 1,386 kept. |
| Morning issue stamp is about 08:38 UTC in both winter and summer, close to the 08:50 UTC summer cut-off | Stamp read as UTC (the later, safe reading). Recorded as a limitation. |
| `CP_ST_TIME` time zone is undocumented for this file (NESO pages for related files disagree) | Not used. Only daily features: max, min and range of the points. |
| Point set varies (9-13 per day) | Features use max and min, not named points. |

### 3.2 NESO embedded wind and solar forecasts

- **Dataset / files:** NESO "Embedded Solar and Wind Forecast" yearly archives 2023, 2024, 2025, 2026 (half-hourly, 0-14 days ahead). Retrieved 22 Nov 2026. NESO Open Data Licence v1.0.
- **Saved as:** `data/raw/embedded_archive_<year>.csv` (0.4-0.65 GB each). 2022 not downloaded, so 1 Jan 2023 has no embedded forecast.
- **Publication time:** `Forecast_Datetime`, a new run every hour at :12. **UK clock time** (confirmed: the 01:00 hour is missing on the spring clock-change day in all four files).
- **Coverage:** embedded (distribution-connected) generation only. Transmission wind is in section 3.3.

| Issue | Rule |
|---|---|
| About 300 runs per target half-hour | Keep the latest run at or before the cut-off; ignore runs more than 6 hours older than the cut-off (day dropped instead). |
| `TIME_GMT` is the period end and the last period sits under the next `DATE_GMT` | Ignore the `*_GMT` columns. Use `SETTLEMENT_DATE` and `SETTLEMENT_PERIOD`: period 1 starts at UK midnight, each period is 30 minutes. |
| Some timestamps carry a `Z` suffix | Read as clock time regardless of suffix. |
| Half-hourly | Average to hourly UTC. Result: 1,413 days with 23, 24 or 25 hours as expected. |

### 3.3 NESO day-ahead transmission wind forecast

- **Dataset / file:** NESO "Day Ahead Wind Forecast", file "Historic Day Ahead Wind Forecasts" (2018 onwards). Retrieved 25 Nov 2026. NESO Open Data Licence v1.0.
- **Saved as:** `data/raw/neso_wind_dayahead_historic.csv`. Columns `Datetime_GMT` (UTC period start), `Date`, `Settlement_period`, `Capacity` (transmission-connected wind, MW), `Incentive_forecast` (MW), `Forecast_Timestamp`.
- **Publication time:** `Forecast_Timestamp`, one issue per target day.

| Issue | Rule |
|---|---|
| Time zone of `Forecast_Timestamp` not stated, and one issue per day so it cannot be tested on a clock-change day | Read as UTC. If it is really UK time this can only drop good days, never admit a late one. |
| Many issues are on or after the delivery day (lead time 0 or negative, about 30% of days from 2023) | Fail the cut-off and are dropped. 930 days from 2023 kept. |
| **No usable issues after 29 Mar 2026** | From then on forecasts are stamped on the delivery day. This sets the end of the usable period. |
| Incomplete days | Dropped. |

### 3.4 Calendar and lagged prices

- **Calendar:** local hour, day of week, month, weekend, England and Wales bank holidays (`holidays` package). Known in advance.
- **Lagged prices:** 24 and 168 hours earlier, and the previous delivery day's mean, from the price file. D-1 prices are public before the D-1 cut-off.
- **Rule:** a lag is used only if its source hour belongs to an earlier delivery day. On a 25-hour day the last hour's 24-hour lag falls inside D, so it is set to missing (one hour per autumn clock change).

### 3.5 Feature table

- **Built by:** `python -m src.features.build`, written to `data/cache/features.parquet` (git-ignored).
- **Result (25 Nov 2026):** 21,766 hourly rows, **907 complete delivery days, 2 Jan 2023 to 29 Mar 2026**. A day is kept only if every source supplies every hour. Leakage check passed.
- **Comparability:** perfect foresight, the benchmark and the forecast-driven schedule must be scored on these same days. M1 (1,416 days) is re-run on this set in week 6.

---

## 4. Sources reviewed and not used

### 4.1 Elexon day-ahead wind and solar (DGWS / B1440)

- **Endpoint:** `data.elexon.co.uk/bmrs/api/v1/forecast/generation/wind-and-solar/day-ahead`, no key.
- **Finding (tested 25 Nov 2026):** one `publishTime` per target day, about **16:45 UTC on D-1**, which is after the 09:50 gate closure. Offshore wind, onshore wind and solar are split.
- **Decision:** not usable as a day-ahead feature. It could not fill the transmission-wind gaps.

### 4.2 Weather

- **Decision:** **no raw weather features in version 1.** The demand, embedded wind/solar and transmission wind forecasts already carry the weather's effect on the power system, and no leak-safe weather forecast archive covers 2023.
- **Reviewed:** Open-Meteo Historical Forecast API (stitched runs, so each hour comes from a near-real-time run: hindsight); Previous Runs API (fixed lead time, most models from Jan 2024; only "previous day 2" is safe for every hour against a 09:50 cut-off); Single Runs API (ECMWF IFS HRES from March 2024); UKMO via Open-Meteo (93 days only); a daily London observed-weather CSV (observed, not a forecast).
- **Planned extension (week 7, optional):** weather from 2024 via Open-Meteo "previous day 2", comparing the model with and without it on the same days. Not yet tested against the live API.

### 4.3 NESO Demand Data Update (sanity checks only)

- **Page:** https://www.neso.energy/data-portal/daily-demand-update/demand_data_update
- **Access:** CSV download or CKAN API (`api.neso.energy`), no key seen.
- **Retrieved:** 18 Nov 2026. Suggested local path: `data/raw/demand_data_update_2026-11-18.csv` (ignored by git).
- **Coverage (profiled file):** 1 Oct to 24 Nov 2026, 2,641 rows, 23 columns, no missing values. Outturn (`A`) rows run to 18 Nov period 16 (2,321 rows). Forecast (`F`) rows run from 18 Nov period 17 to 24 Nov (320 rows). Usually updated daily by 08:30 UTC.
- **Resolution:** half-hourly settlement periods. `SETTLEMENT_DATE` and `SETTLEMENT_PERIOD` (period 1 = 00:00-00:30). **Local settlement time confirmed:** 25 Oct 2026 has 50 periods (autumn clock change). One other date has 47 rows and has not been traced. `[check before ingest]`
- **Useful columns:** `ND`, `TSD` (MW); `FORECAST_ACTUAL_INDICATOR` (A or F); `EMBEDDED_WIND_GENERATION`, `EMBEDDED_WIND_CAPACITY`, `EMBEDDED_SOLAR_GENERATION`, `EMBEDDED_SOLAR_CAPACITY`.
- **Interconnector flows** (`IFA_FLOW`, `BRITNED_FLOW`, etc.) are outturn. Not allowed as day-ahead features (leakage).
- **Licence:** NESO Open Data Licence v1.0, same terms and attribution as section 1. Licence text reviewed 18 Nov 2026. The licence page says each dataset is licensed individually; the dataset's own "Rights" field is recorded here as the same licence `[confirm the Rights field wording on the dataset page; change this line if it differs]`.
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

### 4.4 Open-Meteo, UK Met Office (UKMO) forecasts (not used)

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

## 5. Open items

- [x] Price file timezone (UTC), units (GBP/MWh), dataset name, retrieval date, licence
- [x] NESO attribution line in the README
- [x] Gate-closure time: 09:50 UK clock time on D-1
- [x] Weather approach: none in version 1 (section 4.2)
- [x] Settlement periods mapped to hourly UTC (sections 3.2, 3.3)
- [x] Leak-safe feature table and leakage test (section 3.5)
- [ ] Confirm the "Rights" field wording on each NESO dataset page
- [ ] Re-run M1 on the 907 feature-table days (week 6)
- [ ] Optional: check whether NESO publishes timestamped transmission wind forecasts after 29 Mar 2026 elsewhere
- [ ] Optional: trace the 47-row date and the `EMBEDDED_WIND_CAPACITY` change in the Demand Data Update file (not used for training)