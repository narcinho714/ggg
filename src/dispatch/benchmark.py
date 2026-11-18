"""Simple fixed-pattern benchmark schedule (ignores prices entirely).

Every day: charge at full power during fixed local-clock hours until the SoC
ceiling, then discharge at full power during fixed local-clock hours until the
SoC is back at the end-of-day target (or the cycle cap is reached).

The default windows avoid 01:00-02:00 local time, the hour that is repeated or
skipped on clock-change days, so the same pattern is valid on 23-, 24- and
25-hour days.
"""

from __future__ import annotations

import numpy as np

from src.dispatch.battery import BatteryParams, Schedule, soc_path

DEFAULT_CHARGE_HOURS = (2, 3, 4, 5)
DEFAULT_DISCHARGE_HOURS = (16, 17, 18, 19)


def fixed_window_schedule(
    local_hours: np.ndarray,
    params: BatteryParams,
    charge_hours: tuple[int, ...] = DEFAULT_CHARGE_HOURS,
    discharge_hours: tuple[int, ...] = DEFAULT_DISCHARGE_HOURS,
) -> Schedule:
    """Rule-based schedule keyed on the local clock hour of each period."""
    hours = np.asarray(local_hours)
    n = len(hours)
    eta, p_max = params.eta, params.power_mw
    s0 = params.soc_target_mwh

    charge = np.zeros(n)
    discharge = np.zeros(n)
    e = s0
    drawn = 0.0  # energy taken out of the battery so far today
    for t in range(n):
        h = int(hours[t])
        if h in charge_hours:
            c = max(0.0, min(p_max, (params.soc_max_mwh - e) / eta))
            charge[t] = c
            e += eta * c
        elif h in discharge_hours:
            d = max(0.0, min(p_max, (e - s0) * eta, (params.daily_discharge_cap_mwh - drawn) * eta))
            discharge[t] = d
            e -= d / eta
            drawn += d / eta
    return Schedule(charge, discharge, soc_path(charge, discharge, params))
