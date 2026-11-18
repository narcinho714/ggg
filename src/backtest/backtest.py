"""Day-by-day backtest of battery dispatch over complete GB delivery days.

`run_backtest` takes the output of `complete_delivery_days` (hourly UTC index,
columns price_gbp_mwh, local_time, delivery_date) and returns one row per day.

Strategies
    perfect_foresight  optimise each day against that day's ACTUAL prices
                       (an unattainable ceiling)
    benchmark          fixed-window schedule that ignores prices

Every strategy is settled at the actual prices. A forecast-driven strategy
(week 6) will optimise against forecast prices and settle at actual prices.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.dispatch.battery import BatteryParams, Schedule, count_blocks, settle, solve_day
from src.dispatch.benchmark import fixed_window_schedule

STRATEGIES = ("perfect_foresight", "benchmark")


def run_backtest(
    prices: pd.DataFrame,
    params: BatteryParams,
    strategy: str = "perfect_foresight",
    time_limit_seconds: float | None = None,
) -> pd.DataFrame:
    """One row per delivery day: revenue in GBP and per MW, plus schedule diagnostics."""
    if strategy not in STRATEGIES:
        raise ValueError(f"strategy must be one of {STRATEGIES}")

    rows = []
    for day, g in prices.groupby("delivery_date", sort=True):
        p = g["price_gbp_mwh"].to_numpy(dtype=float)
        if strategy == "perfect_foresight":
            sched: Schedule = solve_day(p, params, time_limit_seconds)
        else:
            sched = fixed_window_schedule(g["local_time"].dt.hour.to_numpy(), params)

        s = settle(p, sched, params)
        rows.append(
            {
                "delivery_date": day,
                "hours": len(p),
                **s,
                "net_gbp_per_mw": s["net_gbp"] / params.power_mw,
                "charge_blocks": count_blocks(sched.charge_mw),
                "discharge_blocks": count_blocks(sched.discharge_mw),
                "end_soc_mwh": float(sched.soc_mwh[-1]),
            }
        )
    return pd.DataFrame(rows).set_index("delivery_date")


def summarise(daily: pd.DataFrame) -> dict:
    """Headline statistics for one strategy's daily results."""
    net = daily["net_gbp_per_mw"]
    positive = net.clip(lower=0).sort_values(ascending=False)
    top_n = max(1, int(np.ceil(0.05 * len(net))))
    total_positive = positive.sum()
    return {
        "days": int(len(net)),
        "mean_gbp_per_mw_day": float(net.mean()),
        "median_gbp_per_mw_day": float(net.median()),
        "total_gbp": float(daily["net_gbp"].sum()),
        "worst_day_gbp_per_mw": float(net.min()),
        "profitable_days_pct": float((net > 0).mean() * 100),
        "top5pct_days_share_of_positive_value": (
            float(positive.head(top_n).sum() / total_positive)
            if total_positive > 0
            else float("nan")
        ),
        "days_with_multiple_charge_blocks": int((daily["charge_blocks"] > 1).sum()),
        "days_with_multiple_discharge_blocks": int((daily["discharge_blocks"] > 1).sum()),
    }
