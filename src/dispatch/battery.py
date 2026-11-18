"""Battery model and single-day dispatch linear programme.

One delivery day at a time. The decision variables are charge power c_t and
discharge power d_t (MW, grid side) for each hour t, plus the state of charge
e_t (MWh, stored energy). Efficiency is applied as sqrt(round-trip) on each leg:

    e_{t+1} = e_t + eta * c_t - d_t / eta          (1-hour steps, so MW = MWh)

The day starts and ends at the end-of-day SoC target from the config, so every
day is self-contained and nothing carries over.

Objective (maximise):  sum_t price_t * (d_t - c_t)  -  degradation * sum_t d_t

Constraints: power limits, SoC limits, start = end = target, and a daily cycle
cap on discharged energy measured at the battery (d_t / eta), in units of
usable energy (soc_max - soc_min).
"""

from __future__ import annotations

from dataclasses import dataclass, fields
from pathlib import Path

import numpy as np
import yaml
from scipy.optimize import linprog

_TOL = 1e-6


@dataclass(frozen=True)
class BatteryParams:
    power_mw: float
    energy_mwh: float
    round_trip_efficiency: float
    soc_min_fraction: float
    soc_max_fraction: float
    max_cycles_per_day: float
    end_of_day_soc_fraction: float
    degradation_cost_gbp_per_mwh: float

    def __post_init__(self) -> None:
        if self.power_mw <= 0 or self.energy_mwh <= 0:
            raise ValueError("power_mw and energy_mwh must be positive")
        if not 0 < self.round_trip_efficiency <= 1:
            raise ValueError("round_trip_efficiency must be in (0, 1]")
        lo, tgt, hi = self.soc_min_fraction, self.end_of_day_soc_fraction, self.soc_max_fraction
        if not 0 <= lo <= tgt <= hi <= 1:
            raise ValueError("need 0 <= soc_min <= end_of_day_soc <= soc_max <= 1")
        if self.max_cycles_per_day < 0 or self.degradation_cost_gbp_per_mwh < 0:
            raise ValueError("max_cycles_per_day and degradation cost must be >= 0")

    @property
    def eta(self) -> float:
        """One-way efficiency (square root of round-trip)."""
        return float(np.sqrt(self.round_trip_efficiency))

    @property
    def soc_min_mwh(self) -> float:
        return self.soc_min_fraction * self.energy_mwh

    @property
    def soc_max_mwh(self) -> float:
        return self.soc_max_fraction * self.energy_mwh

    @property
    def soc_target_mwh(self) -> float:
        return self.end_of_day_soc_fraction * self.energy_mwh

    @property
    def usable_mwh(self) -> float:
        return self.soc_max_mwh - self.soc_min_mwh

    @property
    def daily_discharge_cap_mwh(self) -> float:
        """Max energy drawn from the battery per day (one cycle = usable energy)."""
        return self.max_cycles_per_day * self.usable_mwh


def load_battery_params(config_path: str | Path = "config/config.yaml") -> BatteryParams:
    """Read the `battery:` block of the config. Unknown keys are ignored."""
    with open(config_path, encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)
    block = cfg["battery"]
    names = {f.name for f in fields(BatteryParams)}
    missing = names - set(block)
    if missing:
        raise ValueError(f"battery config is missing: {sorted(missing)}")
    return BatteryParams(**{k: float(block[k]) for k in names})


@dataclass(frozen=True)
class Schedule:
    """Hourly MW (grid side) and the implied SoC path (length n + 1)."""

    charge_mw: np.ndarray
    discharge_mw: np.ndarray
    soc_mwh: np.ndarray


def soc_path(charge_mw: np.ndarray, discharge_mw: np.ndarray, params: BatteryParams) -> np.ndarray:
    """SoC (MWh) at the start of each hour plus the end of the last hour."""
    step = params.eta * charge_mw - discharge_mw / params.eta
    return params.soc_target_mwh + np.concatenate([[0.0], np.cumsum(step)])


def settle(prices: np.ndarray, schedule: Schedule, params: BatteryParams) -> dict:
    """Revenue of a schedule at the given prices (use ACTUAL prices to settle)."""
    p = np.asarray(prices, dtype=float)
    gross = float(np.sum(p * (schedule.discharge_mw - schedule.charge_mw)))
    discharged = float(np.sum(schedule.discharge_mw))
    degradation = params.degradation_cost_gbp_per_mwh * discharged
    return {
        "gross_gbp": gross,
        "degradation_gbp": degradation,
        "net_gbp": gross - degradation,
        "discharged_mwh": discharged,
        "charged_mwh": float(np.sum(schedule.charge_mw)),
    }


def count_blocks(x: np.ndarray, tol: float = _TOL) -> int:
    """Number of separate runs of consecutive hours where x > tol."""
    on = np.asarray(x) > tol
    return int(np.sum(on & ~np.concatenate([[False], on[:-1]])))


def solve_day(
    prices: np.ndarray, params: BatteryParams, time_limit_seconds: float | None = None
) -> Schedule:
    """Optimal schedule for one delivery day given a price vector (23, 24 or 25 hours).

    Pass actual prices for perfect foresight, or forecast prices for a
    forecast-driven schedule (then settle it at actual prices with `settle`).
    """
    p = np.asarray(prices, dtype=float)
    n = len(p)
    if n < 2:
        raise ValueError("need at least 2 hourly prices")
    if np.isnan(p).any():
        raise ValueError("NaN in prices")

    eta, s0 = params.eta, params.soc_target_mwh
    n_e = n - 1  # e_1 .. e_{n-1} are free; e_0 = e_n = s0
    n_var = 2 * n + n_e

    # minimise  sum p*c + sum (deg - p)*d
    cost = np.concatenate([p, params.degradation_cost_gbp_per_mwh - p, np.zeros(n_e)])

    a_eq = np.zeros((n, n_var))
    b_eq = np.zeros(n)
    for t in range(n):
        a_eq[t, t] = -eta  # charge
        a_eq[t, n + t] = 1.0 / eta  # discharge
        if t + 1 <= n - 1:
            a_eq[t, 2 * n + t] = 1.0  # e_{t+1}
        else:
            b_eq[t] -= s0  # e_n is the fixed end target
        if t >= 1:
            a_eq[t, 2 * n + t - 1] = -1.0  # e_t
        else:
            b_eq[t] += s0  # e_0 is the fixed start

    a_ub = np.zeros((1, n_var))
    a_ub[0, n : 2 * n] = 1.0 / eta
    b_ub = np.array([params.daily_discharge_cap_mwh])

    bounds = (
        [(0.0, params.power_mw)] * (2 * n) + [(params.soc_min_mwh, params.soc_max_mwh)] * n_e
    )

    options = {"time_limit": float(time_limit_seconds)} if time_limit_seconds else {}
    res = linprog(
        cost, A_ub=a_ub, b_ub=b_ub, A_eq=a_eq, b_eq=b_eq, bounds=bounds,
        method="highs", options=options,
    )
    if res.status != 0:
        raise RuntimeError(f"Dispatch LP failed (status {res.status}): {res.message}")

    charge = np.where(res.x[:n] < _TOL, 0.0, res.x[:n])
    discharge = np.where(res.x[n : 2 * n] < _TOL, 0.0, res.x[n : 2 * n])
    return Schedule(charge, discharge, soc_path(charge, discharge, params))
