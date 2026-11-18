# Value of a Forecast: GB Day-Ahead Power Price Forecasting and Battery Dispatch

> **Status:** Week 1 of 9 complete (updated 18 Nov 2026). Price data profiled and licence confirmed, loader and tests complete, config and data notes done, repository published and verified from a clean clone on Python 3.13. Everything marked `[TBD]` is filled in only from reproducible runs. Do not publish headline numbers until they come from a clean run.

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
| **Asset (hypothetical)** | 20 MW / 20 MWh battery, 85% round-trip efficiency, up to 1 cycle per day `[illustrative defaults, editable in config]` |
| **Decision layer** | Linear-programme dispatch |
| **Benchmarks** | Simple fixed-pattern schedule, forecast-driven schedule, perfect foresight |
| **Final outputs** | Reproducible backtest, written report, Streamlit dashboard |
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
| Elexon Insights / BMRS | `[Check]` | Confirm whether an API key is needed before week 3. |
| Open-Meteo | No key | Free for non-commercial use. UK Met Office (UKMO) archived forecasts only go back about 93 days, so they cannot supply the full price history (see section 5.2). |
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
- **M1:** `run_backtest` produces perfect-foresight and benchmark revenue for every complete delivery day, constraint tests pass, and one chart exists. M1 answers: *with perfect knowledge of tomorrow's prices, how much could a 1 MW / 2 MWh battery earn?* This is the ceiling, not a forecast result.
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
| NESO N2EX GB price file downloaded and profiled | Done |
| Price loader (`src/ingest/prices.py`) | Done |
| Tests for timestamps, completeness and clock-change days (11 passing) | Done |
| File timezone confirmed (UTC) and units confirmed (GBP/MWh) | Done |
| Price dataset name, retrieval date and licence recorded | Done |
| `DATA.md` with sources, findings, handling rules and open items | Done |
| `config/config.yaml` and `.gitignore` drafted | Done |
| Feature sources reviewed (NESO demand, Open-Meteo UKMO) | Done |
| NESO Demand Data Update file profiled (rolling window, not a training source), Rights field checked (NESO Open Data Licence) and licence terms recorded | Done |
| Git repository created, commits pushed to GitHub | Done |
| `pytest` verified from a clean clone on Python 3.13 (11 passed with data; data tests skip cleanly without it) | Done |
| Python version range documented (3.10 to 3.14, 3.13 recommended) | Done |

### Still to do in week 1

None.

### Decisions pending (needed before week 3, not week 2)

| Decision | Notes |
|---|---|
| Gate-closure time | Confirm from exchange rules. Currently `null` in the config. |
| Weather-history approach | UKMO via Open-Meteo covers about 93 days only. Options are in `DATA.md` section 3. |
| Half-hourly to hourly mapping for demand and wind/solar inputs | NESO demand data uses GB settlement periods (48 a day, 50 on the October clock change); prices are hourly UTC. Map periods to UTC and aggregate before joining. |

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

**Regimes.** Average prices differ sharply: about £198-204/MWh in the 2021-22 energy crisis against £73-£113 from 2023 to 2026. The model and the battery result are tested with and without 2021-22.

### 5.2 Other inputs

| Dataset | Planned source | Notes |
|---|---|---|
| Demand forecasts | NESO "Historic Day Ahead Demand Forecasts" (lead found, `[verify]` field names, publication timestamps and coverage); Elexon Insights / BMRS | Use forecasts available at the cut-off, never later outturn. NESO publishes the day-ahead forecast about twice a day, so only the one before gate closure can be used. |
| Demand outturn | NESO data portal | Targets and checks only, never features for day D. |
| Wind forecasts | Elexon Insights / BMRS; NESO data portal | Use archived forecast runs with publication times. `[source still to find]` |
| Solar forecasts | NESO data portal and other public GB datasets | Check coverage of embedded solar. `[source still to find]` |
| Weather | `[TBD: see below]` | UKMO via Open-Meteo goes back about 93 days only. |
| Gas | Not in version 1 | Add only if a clean, licensed history exists. |
| Calendar | Python and UK holiday data | Day of week, month, holidays. |

**Weather-history decision (open).** Options, in the order they will be checked: (1) published day-ahead forecasts with publication times, (2) another Open-Meteo model through its historical forecast archive, (3) reanalysis as an optimistic proxy, clearly labelled, (4) the 93-day UKMO window only for recent sanity checks. The choice will be recorded here and in the limitations.

**Not used for training.** The NESO Demand Data Update (retrieved 18 Nov 2026) is a rolling window, so it cannot supply the 2021-2026 history. The file profiled covers 1 Oct to 24 Nov 2026 in half-hourly GB settlement periods. Its forecast rows carry embedded wind and solar only (demand fields are zero), and it has no publication timestamps, so it is unusable as a leakage-safe feature source. Its interconnector flow columns are outturn and are never used as day-ahead features. Embedded wind capacity changes between its actual and forecast rows and must be checked before any use.

Elexon's Market Index Price is not the day-ahead auction price and is never used as the target.
Raw data is not committed, to keep the repository small and the pipeline reproducible from the config. This is a project choice: the NESO licence would permit redistribution with attribution. `data/` is git-ignored.

---

## 6. Scope and assumptions

- **Price-taker:** the battery does not move the price.
- **Settlement:** scheduled volumes are assumed to clear at the actual day-ahead price. No order-book, partial-fill or route-to-market effects.
- **Information timing:** forecasts for delivery day D use only information published before the day-ahead gate closure on D-1. The gate-closure time is `[TBD: confirm from exchange rules]`.
- **Delivery day:** the `Europe/London` calendar day, so some days have 23 or 25 hours.
- **Asset:** 20 MW / 20 MWh, 85% round-trip efficiency, state of charge 10-90%, 10% start and end of day, up to 1 cycle a day, degradation cost £5/MWh discharged (placeholder; sensitivity-tested £0-£30). Illustrative, set in the config.
- **Excluded:** ancillary and balancing revenue, intraday, network charges and taxes.

---

## 7. Method

**Forecasting.** Naive (same hour yesterday or last week), regularised linear, and LightGBM. Walk-forward validation only, with no random splits. Report MAE, RMSE and bias overall and by hour, season, wind/solar/demand condition and price level, including negative-price and spike periods.

**Scenarios.** One trained model, re-run with a few documented changes to wind, solar and demand inputs. Adjustment sizes come from historical forecast errors or are clearly labelled as illustrative stresses. Inputs stay within the training range because tree models cannot extrapolate. Scenarios are stresses, not calibrated probabilities.

**Battery dispatch.** For each delivery day, a linear programme maximising `Σ price × (discharge − charge) − degradation cost × throughput`, subject to power, energy and state-of-charge limits with efficiency, a cycle limit and an end-of-day state-of-charge target. Solver: `scipy.optimize.linprog` (HiGHS) `[confirm]`.

**Benchmarks.** Simple fixed-pattern schedule; central forecast-driven schedule evaluated at actual prices; perfect foresight (an unattainable upper bound).

**Metrics.** Revenue per MW per day; value captured = (forecast-driven − benchmark) ÷ (perfect foresight − benchmark), reported on aggregated periods and handled explicitly where the denominator is near zero; worst days and drawdown; percentage of profitable days; share of value from the top 5% of days.

**Sensitivity.** Efficiency, degradation cost, cycle limits, added forecast noise and bias, seasons and volatility regimes, with and without 2021-22, and with the best days removed.

---

## 8. Results

`[TBD: populate only from reproducible runs]`

- 8.1 Perfect foresight vs benchmark (M1)
- 8.2 Forecast accuracy (M2)
- 8.3 Dispatch value and value captured (M3)
- 8.4 Scenario comparison
- 8.5 Robustness
- 8.6 What did not work

---

## 9. Limitations

- Simulation only: no execution, liquidity or market impact.
- Price-taker with assumed fills at the day-ahead price.
- Hourly resolution hides within-hour variation.
- Archived forecasts may be more accurate than what was available in real time.
- Weather history: the full-period weather features may rely on a proxy rather than true archived forecasts `[TBD: update once the approach is chosen]`.
- Some demand and wind inputs are published snapshots with limited publication-time history.
- Scenario assumptions are simplified stresses.
- Results depend on the period, source and asset parameters.
- A good forecast is not proof of a durable trading edge.

---

## 10. Repository structure

```text
.
├── README.md
├── DATA.md                     # done: sources, findings, handling rules, open items
├── .gitignore                  # done
├── pyproject.toml              # done: requires-python >=3.10,<3.15
├── requirements.txt
├── config/
│   └── config.yaml             # drafted: dates, asset parameters, sources, model settings
├── data/                       # git-ignored; raw/ holds the NESO CSVs
├── src/
│   ├── ingest/prices.py        # done: loader and validation
│   ├── features/               # planned
│   ├── forecast/               # planned
│   ├── scenarios/              # planned
│   ├── dispatch/               # planned: battery model and LP (week 2)
│   ├── backtest/               # planned
│   └── reporting/              # planned
├── app/dashboard.py            # planned: Streamlit (week 8)
├── notebooks/                  # exploration only; results come from src/
├── tests/test_prices.py        # done
└── reports/                    # planned
```

---

## 11. Quick start

```bash
git clone https://github.com/narcinho714/ggg.git
cd ggg
python -m venv .venv               # use Python 3.13; on Windows: py -3.13 -m venv .venv
source .venv/bin/activate          # Windows PowerShell: .\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"            # or: pip install -r requirements.txt (a pointer to pyproject.toml)

# download "N2EX GB Day-Ahead Price" from the NESO data portal and save it as
# data/raw/neso_n2ex_gb_da.csv, then:
python -m pytest -v
```

Add `pip install -e ".[dashboard]"` from week 8. Data-dependent tests are skipped if the raw file is missing (expect `1 passed, 10 skipped` without it and `11 passed` with it).

---

## 12. Testing and quality

- Timestamp handling, clock-change days (23 and 25 hours), contiguity and completeness (done).
- Truncated edge days are never mistaken for clock-change days (done).
- Data-dependent tests skip cleanly when the raw file is absent (done).
- Leakage test: no feature uses information published after the cut-off (week 3-4).
- Battery tests: state of charge within limits, no simultaneous charge and discharge, energy balance (week 2).
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
- Demand data: National Energy System Operator (NESO), "Demand Data Update", retrieved 18 Nov 2026. The dataset's Rights field (checked 18 Nov 2026) links to the [NESO Open Data Licence](https://www.neso.energy/data-portal/neso-open-licence), v1.0. Used for sanity checks only; not a training source. Other NESO demand datasets will be attributed here when added.
- Generation data: Elexon Insights / BMRS `[add attribution]`.
- Weather: Open-Meteo, UK Met Office model data (CC BY-SA 4.0) `[add exact attribution wording; update if another weather source is chosen]`.
- NESO logos and trademarks are not used, and NESO does not endorse this project.
- Inspired by the open-source [EpexPredictor](https://github.com/b3nn0/EpexPredictor); this is an independent implementation with a different scope.

## 15. Author

**[Your Name]**, Trade Control Analyst, UK and European power and gas markets. [LinkedIn URL] | [Email]

## 16. Licence

`[Choose a licence, e.g. MIT for the code, after checking that the code and any bundled material can be distributed under it. Note: UKMO weather data is CC BY-SA 4.0, so any shared weather-derived data must carry a compatible licence. Raw data is not committed.]`
