# Value of a Forecast: GB Day-Ahead Power Price Forecasting and Battery Dispatch

> **Status:** Weeks 1-3 of 9 complete (updated 25 Nov 2026). Price loader, battery model, benchmark and perfect-foresight ceiling (**M1**) are done. Week 3 built a leak-safe hourly feature table (907 complete days, 2 Jan 2023 to 29 Mar 2026) with an automated leakage test. Forecasting starts in week 4. Everything marked `[TBD]` is filled in only from reproducible runs.

A reproducible research project that asks one practical trading question:

**How much value can a forecast-driven battery schedule capture in the Great Britain (GB) day-ahead market, and how robust is that value across market scenarios, forecast errors and operating costs?**

The project forecasts GB day-ahead prices, turns the forecasts into a battery charge/discharge schedule, and compares the result with a simple benchmark and a perfect-foresight upper bound.

> **Disclaimer.** Historical simulation for research and learning. It is not trading advice and does not show real trading results or P&L. It uses public data only. No employer data, systems or proprietary logic are used.

---

## 1. Summary

| | |
|---|---|
| **Market** | GB day-ahead wholesale electricity market (N2EX hourly auction). Excludes Northern Ireland. |
| **Price unit** | GBP/MWh (confirmed) |
| **Resolution** | Hourly (half-hourly is a later extension, only if a consistent, licensed history exists) |
| **Forecast model** | LightGBM against naive and regularised-linear baselines |
| **Scenarios** | Bearish, central and bullish, made by changing a few documented fundamentals |
| **Asset (hypothetical)** | 20 MW / 20 MWh (1-hour) battery, 85% round-trip efficiency, SoC window 10-90%, 1 cycle per day, £5/MWh degradation cost. Illustrative, editable in `config/config.yaml`. |
| **Decision layer** | Linear-programme dispatch |
| **Analysis window** | Prices and M1: 1 Jan 2023 onwards (1,416 complete delivery days). Forecasting: **2 Jan 2023 to 29 Mar 2026 (907 days)**, the days on which every leak-safe input exists (section 5.2). The 2021-22 energy crisis is excluded from the headline and kept as a sensitivity. |
| **Information cut-off** | 09:50 UK time on the day before delivery (N2EX gate closure). No feature uses anything published later; checked by an automated test. |
| **Benchmarks** | Fixed-hour schedule (charge 04:00, discharge 18:00 local time, every day), forecast-driven schedule, perfect foresight |
| **Final outputs** | Reproducible backtest, written report, Streamlit dashboard |
| **M1 result (ceiling)** | Perfect foresight £38.00/MW/day vs fixed-hour benchmark £22.36/MW/day, so a forecast can capture at most about £15.6/MW/day above the benchmark |
| **Headline result** | `[TBD: value captured vs perfect foresight, with range and caveats]` |

---

## 2. What you need before starting

**Software**
- Python **3.13** (supported range 3.10 to 3.14). Python 3.15 is not supported yet: some dependencies, such as PyYAML, had no pre-built wheels for it at the time of writing and fail to build.
- Git, and a GitHub account to publish the repository
- A code editor (VS Code, Spyder or similar). If using Spyder, point it at the project's `.venv` interpreter and install `spyder-kernels==3.1.*` in that environment.
- Around 2 GB free disk space for raw and cached data

**Accounts and keys**
| Item | Needed? | Notes |
|---|---|---|
| NESO data portal | No key | Day-ahead price CSV is downloaded manually for now. Licence and retrieval date are recorded in `DATA.md`. |
| Elexon Insights / BMRS | No key | Reviewed in week 3; its day-ahead wind and solar forecast is published after gate closure, so it is not used (`DATA.md` section 4.1). |
| Open-Meteo | No key | Not used in version 1 (no raw weather). Planned for an optional week 7 experiment. |
| ENTSO-E | Optional | GB day-ahead coverage may be limited after Brexit, so it is not the primary price source. |

**Time**
- About **8 hours a week for 9 weeks (roughly 70 hours)**.
- Weeks 6 and 7 fall over Christmas and are planned lighter.

**Skills already in hand:** Python, SQL, VBA. New for this project: LightGBM, walk-forward validation, linear programming and Streamlit. Budget extra time in the weeks that introduce them.

---

## 3. Timeline

Start: **Monday 16 November 2026**. Finish: **Sunday 17 January 2027**.
Build order: **a thin end-to-end slice first** (prices, then battery, then forecasting), so there is a real result in week 2 and the optimiser is tested before the forecasting work begins.

| Week | Dates | Focus | Output | Hours |
|---|---|---|---|---|
| **1** | 16 Nov - 22 Nov | Repo setup, price file profiled, loader and tests, config, licence and timezone confirmed | Clean hourly price table, tests passing | 8 |
| **2** | 23 Nov - 29 Nov | Battery LP, simple benchmark, perfect foresight | **M1:** value ceiling in £/MW/day over all complete days | 8 |
| **3** | 30 Nov - 6 Dec | Demand, wind and solar forecast ingest; weather-history approach settled; publication-time tracking | Feature table with a forecast cut-off function | 8 |
| **4** | 7 Dec - 13 Dec | Naive and linear baselines, walk-forward framework | **M2:** baseline accuracy table | 8 |
| **5** | 14 Dec - 20 Dec | LightGBM, error analysis by hour, season and regime | Forecast error report | 8 |
| **6** | 21 Dec - 27 Dec | Central forecast-driven backtest (holiday week, lighter) | **M3:** headline value captured | 5 |
| **7** | 28 Dec - 3 Jan | Scenarios, sensitivity and stress tests (holiday week, lighter) | Scenario curves, robustness charts | 5 |
| **8** | 4 Jan - 10 Jan | Streamlit dashboard | **M4:** working dashboard | 8 |
| **9** | 11 Jan - 17 Jan | Report, README results, clean-run reproduction, publish | **M5:** public repository | 8 |

**Milestone exit criteria**
- **M1 (done):** `run_backtest` produces perfect-foresight and benchmark revenue for every complete delivery day, constraint tests pass, and one chart exists. M1 answers: *with perfect knowledge of tomorrow's prices, how much could a 20 MW / 20 MWh battery earn?* This is the ceiling, not a forecast result.
- **M2:** baselines scored with MAE, RMSE and bias under walk-forward validation, with no look-ahead (leakage test passes).
- **M3:** forecast-driven revenue evaluated at actual prices, value captured reported with the undefined-ratio case handled.
- **M4:** dashboard reads pipeline outputs only, with no separate modelling logic.
- **M5:** a fresh clone reproduces the headline numbers from the config file alone.

**Slip rule:** if a week runs over, cut scope in this order: bullish/bearish scenario dashboard panel, then the stress-test extras, then anything optional. Do not cut the leakage tests or the limitations section.

---

## 4. Current status

### Done

| Item | Status |
|---|---|
| Price file profiled, licence and timezone confirmed; loader and 11 tests | Done (week 1) |
| `DATA.md`, config, `.gitignore`, clean-clone check on Python 3.13 | Done (week 1) |
| Battery LP, fixed-hour benchmark, backtest, 53 dispatch tests | Done (week 2) |
| **M1:** perfect-foresight ceiling and benchmark from 2023-01-01 | Done (section 8.1) |
| Forecast cut-off rule (09:50 UK time on D-1) in config and code | Done (week 3) |
| Loaders: demand forecast, embedded wind/solar, transmission wind | Done (week 3) |
| Calendar and lagged-price features | Done (week 3) |
| Feature table (907 days) and leakage test; 67 tests in total | Done (week 3) |

### Still to do

| Item | When |
|---|---|
| Naive and linear baselines, walk-forward validation (**M2**) | Week 4 |
| Re-run M1 on the 907 feature-table days so all strategies share one set of days | Week 6 |
| Clean-clone re-run of M1 and the feature build | Before week 4 closes |
| Fill the author section (section 15) | Any time; the repository is public |

---

## 5. Data

### 5.1 Price file (verified by script)

**Source.** NESO data portal, dataset "Day-Ahead Power Exchange prices (Nord Pool)", data file "N2EX GB Day-Ahead Price". Retrieved 17 Nov 2026. Licence: NESO Open Data Licence v1.0. Full details in `DATA.md`.

| Check | Result |
|---|---|
| Rows | 45,217 hourly periods |
| First / last period | 2021-09-20 22:00 / 2026-11-17 22:00 |
| Missing, duplicate or gapped periods | None |
| Rows per calendar date | Exactly 24, including UK clock-change days |
| Complete GB delivery days | 1,883 (two truncated edge days excluded) |
| Negative-price hours | 591 |
| Price range | -54.17 to 2,000.05 |

**Timezone.** Every date has 24 rows, so the labels are a continuous fixed clock, not UK local time. The weekday morning price ramp moves one label earlier after clocks go forward and later after they go back, consistent with UTC. The timezone is confirmed as UTC. The loader treats the file as UTC and derives the GB delivery day in `Europe/London`.

**Regimes.** Average prices differ sharply: about £198-204/MWh in the 2021-22 energy crisis against £73-£113 from 2023 to 2026.

**Analysis window.** The headline results use delivery days from **1 January 2023** (`data_window.analysis_start` in the config), which gives **1,416 complete days**. The 2021-22 crisis inflates the ceiling (perfect-foresight mean £54.02/MW/day over the full 1,883 days against £38.00 from 2023) and would distort every comparison, so it is reported as a sensitivity only.

### 5.2 Feature inputs (week 3)

Every feature for delivery day D uses only information published at or before **09:50 UK time on D-1**. Full details and handling rules are in `DATA.md`.

| Input | Source | Usable days from 2023 | Notes |
|---|---|---|---|
| Demand forecast | NESO Historic Day Ahead Demand Forecasts | 1,386 | Latest issue before the cut-off; daily max, min and range |
| Embedded wind and solar forecast | NESO Embedded Solar and Wind Forecast archives 2023-26 | 1,413 | Hourly runs; latest before the cut-off; half-hours to hourly UTC |
| Transmission wind forecast | NESO Historic Day Ahead Wind Forecasts | 930 | One issue per day; about 30% are issued on or after the delivery day and dropped; **none usable after 29 Mar 2026** |
| Calendar | `holidays` package | All | Local hour, day of week, month, weekend, bank holidays |
| Lagged prices | Price file | All | 24 h, 168 h, previous day's mean; never from the delivery day itself |
| Weather | Not used in version 1 | - | See below |
| Gas | Not used in version 1 | - | No clean, licensed history found |

**Feature table:** `python -m src.features.build` writes `data/cache/features.parquet`: 21,766 hourly rows, **907 complete delivery days from 2 Jan 2023 to 29 Mar 2026**. A day is kept only if every source supplies every hour.

**Weather decision.** Version 1 has no raw weather features. The demand, wind and solar forecasts already carry the weather's effect on the power system, and no leak-safe weather forecast archive covering 2023 was found (Open-Meteo's archived single runs and fixed-lead forecasts start in 2024; its stitched archive and observed-weather files contain hindsight). An optional week 7 experiment adds weather from 2024 onwards and compares results with and without it.

**Sources reviewed and rejected.** Elexon's day-ahead wind and solar forecast (DGWS) is published at about 16:45 UTC on D-1, after gate closure. NESO's Demand Data Update is a rolling window with no publication times; it is used for sanity checks only.

Elexon's Market Index Price is not the day-ahead auction price and is never used as the target.
Raw data is not committed, to keep the repository small and the pipeline reproducible from the config. This is a project choice: the NESO licence would permit redistribution with attribution. `data/` is git-ignored.

---

## 6. Scope and assumptions

- **Price-taker:** the battery does not move the price.
- **Settlement:** scheduled volumes are assumed to clear at the actual day-ahead price. No order-book, partial-fill or route-to-market effects.
- **Information timing:** forecasts for delivery day D use only information published at or before the N2EX day-ahead gate closure, **09:50 UK time on D-1** (`gate_closure_local` in the config).
- **Delivery day:** the `Europe/London` calendar day, so some days have 23 or 25 hours.
- **Asset (illustrative, all set in `config/config.yaml`):**

| Parameter | Value |
|---|---|
| Power | 20 MW |
| Energy | 20 MWh (1-hour duration) |
| Round-trip efficiency | 85% (applied as the square root, about 92.2%, on each of charge and discharge) |
| State-of-charge window | 10-90% (2-18 MWh, so 16 MWh usable) |
| Start and end-of-day state of charge | 10% (2 MWh) |
| Cycles per day | 1 (daily discharge limited to 16 MWh of stored energy) |
| Degradation cost | £5 per MWh discharged |

- **One block each way:** with these settings the battery charges in one block and discharges in one block each day.
- **Excluded:** ancillary and balancing revenue, intraday, network charges and taxes.

---

## 7. Method

**Features.** Built only from information available at the cut-off (section 5.2). Each row stores the issue time of every forecast it uses, and `check_no_leakage` fails the build and the tests if any is later than the cut-off.

**Forecasting.** Naive (same hour yesterday or last week), regularised linear, and LightGBM. Walk-forward validation only, with no random splits. Report MAE, RMSE and bias overall and by hour, season, wind/solar/demand condition and price level, including negative-price and spike periods.

**Scenarios.** One trained model, re-run with a few documented changes to wind, solar and demand inputs. Adjustment sizes come from historical forecast errors or are clearly labelled as illustrative stresses. Inputs stay within the training range because tree models cannot extrapolate. Scenarios are stresses, not calibrated probabilities.

**Battery dispatch.** For each delivery day, a linear programme maximising `Σ price × (discharge − charge) − degradation cost × throughput`, subject to power, energy and state-of-charge limits with efficiency, a cycle limit and an end-of-day state-of-charge target. The day ends at the same state of charge it started at. Solver: `scipy.optimize.linprog` (HiGHS).

**Benchmarks.**
- **Fixed-hour benchmark:** charges at 04:00 and discharges at 18:00 (Europe/London local time) every day, whatever the prices. The hours were chosen a priori as a plausible overnight low and evening peak, not fitted to the data. Because it ignores prices it is deliberately simple.
- **Forecast-driven schedule (week 6):** optimised on forecast prices, then paid at actual prices.
- **Perfect foresight:** the same optimiser given each day's actual prices. It picks different hours every day and may skip days where the spread does not cover the degradation cost. It is an unattainable upper bound, not a forecast.

**Metrics.** Net revenue per MW per day (net £ ÷ 20 MW, averaged over complete delivery days); value captured = (forecast-driven − benchmark) ÷ (perfect foresight − benchmark), reported on aggregated periods and handled explicitly where the denominator is near zero; worst days and drawdown; percentage of profitable days; share of value from the top 5% of days.

**Sensitivity.** Efficiency, degradation cost, cycle limits, added forecast noise and bias, seasons and volatility regimes, with and without the 2021-22 crisis period, and with the best days removed.

---

## 8. Results

Only numbers from reproducible runs appear here. Reproduce with `python -m src.backtest.run_m1` (section 11).

### 8.1 Perfect foresight vs benchmark (M1)

Window: 1 Jan 2023 onwards, 1,416 complete delivery days, 20 MW / 20 MWh battery. Net of the £5/MWh degradation cost, in £/MW/day unless stated.

| Metric | Perfect foresight | Fixed-hour benchmark (04:00 / 18:00) |
|---|---|---|
| Mean | **38.00** | **22.36** |
| Median | 28.44 | 15.34 |
| Total (£, whole fleet of 20 MW) | 1,076,291 | 633,268 |
| Profitable days | 99.93% | 89.12% |
| Worst day | 0.00 | -33.43 |
| Share of total from top 5% of days | 17% | 23% |

**How to read this.** Perfect foresight is handed each day's actual prices, so it picks the best hours that day. The benchmark uses the same hours every day. The gap between them, about **£15.6/MW/day**, is the most a forecast-driven schedule can add over the benchmark. Value captured in week 6 is the share of that gap a forecast closes. Checks that passed on every day: perfect foresight is never below the benchmark, the battery ends the day at its target state of charge, and there is one charge and one discharge block.

Outputs: `reports/m1_summary_from_2023-01-01.json` and `reports/m1_ceiling_from_2023-01-01.png`. Daily detail is written to `data/cache/` (git-ignored).

### 8.2 Forecast accuracy (M2)
`[TBD]`

### 8.3 Dispatch value and value captured (M3)
`[TBD]`

### 8.4 Scenario comparison
`[TBD]`

### 8.5 Robustness
`[TBD]` The full-history (2021-onward) perfect-foresight mean of £54.02/MW/day is the first sensitivity.

### 8.6 What did not work

- **First benchmark was too weak.** The original fixed-hour benchmark (charge 02:00, discharge 16:00) earned only **£4.50/MW/day** over the same window. That is a benchmark that barely trades at useful times, and it would have made any forecast look better than it is: the gap to perfect foresight was £33.5, against about £15.6 for the revised benchmark. The hours were revised to 04:00 and 18:00 after this result was seen, so the final choice was made once with knowledge of the first outcome. They were not searched or optimised.
- **Block fragmentation with a 50% end-of-day state of charge.** An early battery setting allowed the optimiser to split charging and discharging into several blocks per day. Setting the start and end state of charge to 10% fixed it, and the change is covered by tests.

---

## 9. Limitations

- Simulation only: no execution, liquidity or market impact.
- Price-taker with assumed fills at the day-ahead price.
- Hourly resolution hides within-hour variation.
- The fixed-hour benchmark is one simple rule, chosen a priori and revised once after a first weak result (section 8.6). A smarter fixed-hour rule would narrow the gap that a forecast can capture.
- The 20 MW / 20 MWh asset, efficiency, state-of-charge window and degradation cost are illustrative, and results depend on them.
- The headline window excludes the 2021-22 crisis, so it describes a calmer price regime.
- Archived forecasts may be more accurate than what was available in real time.
- No raw weather or gas price features in version 1. Lagged prices carry the gas-driven price level.
- The forecasting period ends on 29 Mar 2026: after that, NESO's transmission wind forecasts are stamped on the delivery day and cannot be used. About 30% of earlier days are also dropped for late wind forecasts, so results cover 907 days, not the full price history.
- Some forecasts are issued only minutes before the 09:50 cut-off, which a real trader might not act on in time. A safety buffer is a planned sensitivity.
- Where a forecast's time zone was undocumented, the reading that can only drop days (never admit a late forecast) was used.
- Scenario assumptions are simplified stresses.
- Results depend on the period, source and asset parameters.
- A good forecast is not proof of a durable trading edge.

---

## 10. Repository structure

```text
.
├── README.md
├── DATA.md                     # sources, findings, handling rules, open items
├── .gitignore
├── pyproject.toml              # requires-python >=3.10,<3.15
├── requirements.txt            # points to pyproject (-e .[dev])
├── config/
│   └── config.yaml             # dates, analysis window, asset parameters, sources, model settings
├── data/                       # git-ignored; raw/ holds the NESO CSVs, cache/ holds run outputs
├── src/
│   ├── ingest/
│   │   ├── prices.py           # done: price loader and validation
│   │   ├── cutoff.py           # done: 09:50 D-1 cut-off in UTC
│   │   ├── demand.py           # done: NESO demand forecast
│   │   ├── windsolar.py        # done: NESO embedded wind and solar
│   │   └── wind.py             # done: NESO transmission wind
│   ├── dispatch/
│   │   ├── battery.py          # done: battery parameters, settlement, day-by-day LP
│   │   └── benchmark.py        # done: fixed-hour schedule
│   ├── backtest/
│   │   ├── backtest.py         # done: run_backtest and summary statistics
│   │   └── run_m1.py           # done: M1 entry point
│   ├── features/
│   │   ├── basic.py            # done: calendar and lagged prices
│   │   └── build.py            # done: feature table and leakage check
│   ├── forecast/               # planned (weeks 4-5)
│   ├── scenarios/              # planned (week 7)
│   └── reporting/              # planned
├── app/dashboard.py            # planned: Streamlit (week 8)
├── notebooks/                  # exploration only; results come from src/
├── tests/
│   ├── test_prices.py          # done: 11 tests
│   ├── test_dispatch.py        # done: 53 tests
│   └── test_features.py        # done: leakage and completeness tests
└── reports/                    # M1 summary (JSON) and ceiling chart (PNG)
```

---

## 11. Quick start

```bash
git clone https://github.com/narcinho714/ggg.git
cd ggg
python -m venv .venv               # use Python 3.13; on Windows: py -3.13 -m venv .venv
source .venv/bin/activate          # Windows PowerShell: .\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"            # or: pip install -r requirements.txt

# download "N2EX GB Day-Ahead Price" from the NESO data portal and save it as
# data/raw/neso_n2ex_gb_da.csv, then:
python -m pytest -v

# reproduce M1 (needs matplotlib for the chart; included in the dev extras once added to pyproject)
pip install matplotlib
python -m src.backtest.run_m1

# build the feature table (needs the NESO feature files listed in DATA.md section 3)
python -m src.features.build
```

Add `pip install -e ".[dashboard]"` from week 8. Data-dependent tests are skipped if the raw file is missing: expect 67 passed with the price file and feature table present; data-dependent tests skip without them.

---

## 12. Testing and quality

- Timestamp handling, clock-change days (23 and 25 hours), contiguity and completeness (done).
- Truncated edge days are never mistaken for clock-change days (done).
- Data-dependent tests skip cleanly when the raw file is absent (done).
- Leakage test: no feature uses information published after the cut-off; the test also proves it catches a forecast stamped one minute late (done, week 3).
- Battery tests: state of charge within limits, no simultaneous charge and discharge, energy balance, a hand-calculated revenue case, 23- and 25-hour days, and perfect foresight never below the benchmark (done, week 2).
- Backtest tests: forecast-driven decisions use forecasts; perfect foresight stays separate (week 6).
- Fixed random seeds and pinned versions (`pip freeze` after the first full run).
- Note: two price tests assert on the last date of the current CSV (2026-11-17). They will need updating when the file is refreshed.

---

## 13. Definition of done

- A fresh clone reproduces every number in section 8 from the config file.
- All tests pass.
- Every assumption is stated and every limitation is listed.
- Results include at least one thing that did not work.
- No employer data, logic or systems are used anywhere.

---

## 14. Acknowledgements and data attribution

**Supported by National Energy SO Open Data.**

- Day-ahead prices: National Energy System Operator (NESO), dataset "Day-Ahead Power Exchange prices (Nord Pool)", file "N2EX GB Day-Ahead Price", retrieved 17 Nov 2026. Licensed under the [NESO Open Data Licence v1.0](https://www.neso.energy/data-portal/neso-open-licence). Delivery periods are UTC and prices are in GBP/MWh.
- Forecast inputs: National Energy System Operator (NESO), "Historic Day Ahead Demand Forecasts" (retrieved 21 Nov 2026), "Embedded Solar and Wind Forecast" archives 2023-2026 (retrieved 22 Nov 2026) and "Historic Day Ahead Wind Forecasts" (retrieved 25 Nov 2026). Licensed under the [NESO Open Data Licence v1.0](https://www.neso.energy/data-portal/neso-open-licence).
- Demand Data Update: NESO, retrieved 18 Nov 2026, same licence. Sanity checks only; not a training source.
- No Elexon or weather data is used in version 1.
- NESO logos and trademarks are not used, and NESO does not endorse this project.
- Inspired by the open-source [EpexPredictor](https://github.com/b3nn0/EpexPredictor); this is an independent implementation with a different scope.

## 15. Author

**[Your Name]**, Trade Control Analyst, UK and European power and gas markets. [LinkedIn URL] | [Email]

## 16. Licence

`[Choose a licence, e.g. MIT for the code, after checking that the code and any bundled material can be distributed under it. Note: Raw data is not committed.]`