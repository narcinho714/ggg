from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.backtest.backtest import run_backtest, summarise
from src.dispatch.battery import (
    BatteryParams,
    Schedule,
    count_blocks,
    load_battery_params,
    settle,
    solve_day,
)
from src.dispatch.benchmark import fixed_window_schedule
from src.ingest.prices import complete_delivery_days, load_prices

CONFIG = Path(__file__).resolve().parents[1] / "config" / "config.yaml"


def params(**overrides) -> BatteryParams:
    base = dict(
        power_mw=20.0,
        energy_mwh=20.0,
        round_trip_efficiency=0.85,
        soc_min_fraction=0.10,
        soc_max_fraction=0.90,
        max_cycles_per_day=1.0,
        end_of_day_soc_fraction=0.50,
        degradation_cost_gbp_per_mwh=5.0,
    )
    base.update(overrides)
    return BatteryParams(**base)


def random_prices(n: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.normal(80, 40, n)


# ---- configuration ---------------------------------------------------------------


def test_config_battery_block_loads_and_is_valid():
    p = load_battery_params(CONFIG)
    assert p.power_mw > 0 and p.energy_mwh > 0
    assert p.soc_min_fraction <= p.end_of_day_soc_fraction <= p.soc_max_fraction


def test_invalid_params_rejected():
    with pytest.raises(ValueError):
        params(end_of_day_soc_fraction=0.95)  # above soc_max
    with pytest.raises(ValueError):
        params(round_trip_efficiency=1.2)


# ---- LP constraints -------------------------------------------------------------


@pytest.mark.parametrize("n", [23, 24, 25])
@pytest.mark.parametrize("seed", range(5))
def test_constraints_hold(n, seed):
    p = params()
    prices = random_prices(n, seed)
    s = solve_day(prices, p)

    assert len(s.charge_mw) == n and len(s.soc_mwh) == n + 1
    # power limits
    assert (s.charge_mw >= -1e-9).all() and (s.charge_mw <= p.power_mw + 1e-6).all()
    assert (s.discharge_mw >= -1e-9).all() and (s.discharge_mw <= p.power_mw + 1e-6).all()
    # state of charge within limits, starts and ends at the target
    assert (s.soc_mwh >= p.soc_min_mwh - 1e-6).all()
    assert (s.soc_mwh <= p.soc_max_mwh + 1e-6).all()
    assert s.soc_mwh[0] == pytest.approx(p.soc_target_mwh)
    assert s.soc_mwh[-1] == pytest.approx(p.soc_target_mwh, abs=1e-5)
    # cycle cap on energy drawn from the battery
    assert (s.discharge_mw / p.eta).sum() <= p.daily_discharge_cap_mwh + 1e-6


@pytest.mark.parametrize("seed", range(5))
def test_energy_balance(seed):
    p = params()
    s = solve_day(random_prices(24, seed), p)
    delta = s.soc_mwh[-1] - s.soc_mwh[0]
    expected = p.eta * s.charge_mw.sum() - s.discharge_mw.sum() / p.eta
    assert delta == pytest.approx(expected, abs=1e-5)


@pytest.mark.parametrize("seed", range(10))
def test_no_simultaneous_charge_and_discharge(seed):
    s = solve_day(random_prices(24, seed), params())
    assert ((s.charge_mw > 1e-6) & (s.discharge_mw > 1e-6)).sum() == 0


def test_flat_prices_do_nothing():
    s = solve_day(np.full(24, 70.0), params())
    assert s.charge_mw.sum() == pytest.approx(0, abs=1e-6)
    assert s.discharge_mw.sum() == pytest.approx(0, abs=1e-6)


def test_known_single_cycle_value():
    """Start empty-ish: charge 10 -> 90% in cheap hours, discharge back in dear hours."""
    p = params(end_of_day_soc_fraction=0.10, degradation_cost_gbp_per_mwh=0.0)
    prices = np.full(24, 50.0)
    prices[2:6] = 10.0  # cheap
    prices[16:20] = 100.0  # dear
    s = solve_day(prices, p)

    stored = p.usable_mwh  # 16 MWh moves through the battery
    expected = (stored * p.eta) * 100.0 - (stored / p.eta) * 10.0
    assert settle(prices, s, p)["net_gbp"] == pytest.approx(expected, rel=1e-6)
    assert count_blocks(s.charge_mw) == 1 and count_blocks(s.discharge_mw) == 1


def test_degradation_cost_reduces_trading():
    prices = np.full(24, 70.0)
    prices[3] = 60.0
    prices[18] = 80.0  # spread too small to cover losses plus degradation
    cheap = solve_day(prices, params(degradation_cost_gbp_per_mwh=0.0))
    costly = solve_day(prices, params(degradation_cost_gbp_per_mwh=50.0))
    assert costly.discharge_mw.sum() <= cheap.discharge_mw.sum()
    assert costly.discharge_mw.sum() == pytest.approx(0, abs=1e-6)


def test_more_cycles_never_lower_value():
    prices = random_prices(24, 3)
    p1, p2 = params(max_cycles_per_day=1), params(max_cycles_per_day=2)
    one = settle(prices, solve_day(prices, p1), p1)
    two = settle(prices, solve_day(prices, p2), p2)
    assert two["net_gbp"] >= one["net_gbp"] - 1e-6


def test_negative_prices_are_used():
    p = params(end_of_day_soc_fraction=0.10)
    prices = np.full(24, 60.0)
    prices[2:5] = -20.0
    prices[17:19] = 120.0
    s = solve_day(prices, p)
    assert s.charge_mw[2:5].sum() > 0  # paid to charge
    assert settle(prices, s, p)["net_gbp"] > 0


# ---- benchmark ------------------------------------------------------------------


@pytest.mark.parametrize("n", [23, 24, 25])
def test_benchmark_is_feasible_and_ends_at_target(n):
    p = params(end_of_day_soc_fraction=0.10)
    hours = (np.arange(n) + (0 if n == 24 else 0)) % 24
    s = fixed_window_schedule(hours, p)
    assert (s.soc_mwh >= p.soc_min_mwh - 1e-6).all() and (s.soc_mwh <= p.soc_max_mwh + 1e-6).all()
    assert s.soc_mwh[-1] == pytest.approx(p.soc_target_mwh, abs=1e-6)
    assert (s.discharge_mw / p.eta).sum() <= p.daily_discharge_cap_mwh + 1e-6


@pytest.mark.parametrize("seed", range(10))
def test_perfect_foresight_beats_benchmark_each_day(seed):
    p = params()
    prices = random_prices(24, seed)
    hours = np.arange(24)
    pf = settle(prices, solve_day(prices, p), p)["net_gbp"]
    bm = settle(prices, fixed_window_schedule(hours, p), p)["net_gbp"]
    assert pf >= bm - 1e-6


# ---- backtest on a synthetic price file through the real loader -----------------


def make_price_csv(path: Path, start: str, end: str, seed: int = 0) -> None:
    idx = pd.date_range(start, end, freq="h")  # UTC hourly, 24 rows per UTC date
    rng = np.random.default_rng(seed)
    hour = idx.hour.to_numpy()
    shape = 60 + 25 * np.sin((hour - 6) / 24 * 2 * np.pi)  # dear evenings, cheap nights
    price = np.round(shape + rng.normal(0, 8, len(idx)), 2)
    end_hour = (hour + 1) % 24
    pd.DataFrame(
        {
            "Date": idx.strftime("%Y-%m-%d"),
            "Delivery Period": [
                f"{h:02d}:00 - {e:02d}:00" for h, e in zip(hour, end_hour, strict=True)
            ],
            "Price": price,
        }
    ).to_csv(path, index=False)


def test_backtest_runs_across_clock_changes(tmp_path):
    csv = tmp_path / "p.csv"
    # spring clock change 2022-03-27 and autumn change 2022-10-30 both inside
    make_price_csv(csv, "2022-03-25 00:00", "2022-03-30 23:00")
    prices = complete_delivery_days(load_prices(csv))
    p = params()

    pf = run_backtest(prices, p, "perfect_foresight")
    bm = run_backtest(prices, p, "benchmark")

    assert pf.loc[pd.Timestamp("2022-03-27").date(), "hours"] == 23
    assert (pf["net_gbp"] >= bm["net_gbp"] - 1e-6).all()
    assert (pf["end_soc_mwh"] - p.soc_target_mwh).abs().max() < 1e-5
    s = summarise(pf)
    assert s["days"] == len(pf)
    assert s["mean_gbp_per_mw_day"] == pytest.approx(pf["net_gbp_per_mw"].mean())

    csv2 = tmp_path / "p2.csv"
    make_price_csv(csv2, "2022-10-28 00:00", "2022-11-01 23:00")
    prices2 = complete_delivery_days(load_prices(csv2))
    pf2 = run_backtest(prices2, p, "perfect_foresight")
    assert pf2.loc[pd.Timestamp("2022-10-30").date(), "hours"] == 25


def test_backtest_rejects_unknown_strategy(tmp_path):
    csv = tmp_path / "p.csv"
    make_price_csv(csv, "2022-06-01 00:00", "2022-06-04 23:00")
    prices = complete_delivery_days(load_prices(csv))
    with pytest.raises(ValueError):
        run_backtest(prices, params(), "magic")


def test_settle_uses_the_prices_it_is_given():
    """A schedule built on forecast prices must be settled at actual prices."""
    p = params(degradation_cost_gbp_per_mwh=0.0)
    s = Schedule(
        charge_mw=np.array([10.0, 0.0]),
        discharge_mw=np.array([0.0, 10.0]),
        soc_mwh=np.zeros(3),
    )
    assert settle(np.array([20.0, 100.0]), s, p)["net_gbp"] == pytest.approx(800.0)
    assert settle(np.array([100.0, 20.0]), s, p)["net_gbp"] == pytest.approx(-800.0)
