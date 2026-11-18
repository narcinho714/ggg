"""Load and validate the GB N2EX day-ahead hourly price series.

Source file (downloaded from the NESO data portal, "Day-Ahead Power Exchange
prices (Nord Pool)", N2EX GB Day-Ahead Price): columns Date, Delivery Period, Price.

Findings from profiling the file (see DATA.md):
  * The timeline is a continuous hourly clock with exactly 24 rows on EVERY
    calendar date, including the UK clock-change days. A UK local-time series
    would have 23- and 25-hour days, so the labels are a fixed-offset clock.
  * The morning price ramp moves one label earlier after clocks go forward and
    one label later after clocks go back, which is the signature of UTC labels.
  => We treat Date + start of Delivery Period as UTC. CONFIRM against the NESO
     dataset metadata before publishing.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

LOCAL_TZ = "Europe/London"
EXPECTED_COLUMNS = {"Date", "Delivery Period", "Price"}


def load_prices(path: str | Path, assume_tz: str = "UTC") -> pd.DataFrame:
    """Return a DataFrame indexed by tz-aware UTC period start.

    Columns:
        price_gbp_mwh   float
        local_time      Europe/London timestamp of the period start
        delivery_date   Europe/London calendar date (the GB delivery day)
    """
    raw = pd.read_csv(path)

    missing = EXPECTED_COLUMNS - set(raw.columns)
    if missing:
        raise ValueError(f"Missing expected columns: {sorted(missing)}")

    start_label = raw["Delivery Period"].str.slice(0, 5)
    end_label = raw["Delivery Period"].str.slice(-5)
    start_hour = start_label.str.slice(0, 2).astype(int)
    end_hour = end_label.str.slice(0, 2).astype(int)
    if not ((start_hour + 1) % 24 == end_hour).all():
        raise ValueError("Delivery Period labels are not all one hour long")

    naive = pd.to_datetime(raw["Date"] + " " + start_label)
    ts = naive.dt.tz_localize(assume_tz)

    out = pd.DataFrame({"price_gbp_mwh": raw["Price"].astype(float).to_numpy()}, index=ts)
    out.index.name = "ts_utc"
    out.index = out.index.tz_convert("UTC")
    out = out.sort_index()

    local = out.index.tz_convert(LOCAL_TZ)
    out["local_time"] = local
    out["delivery_date"] = local.date
    return out


def validate_prices(df: pd.DataFrame) -> dict:
    """Run integrity checks. Raises on hard failures, returns a report."""
    if df.index.has_duplicates:
        raise ValueError("Duplicate timestamps in price series")
    if not df.index.is_monotonic_increasing:
        raise ValueError("Price series is not sorted")

    steps = df.index.to_series().diff().dropna()
    gaps = steps[steps != pd.Timedelta(hours=1)]
    if len(gaps):
        raise ValueError(f"Non-hourly gaps found, first at {gaps.index[0]}")

    if df["price_gbp_mwh"].isna().any():
        raise ValueError("NaN prices present")

    expected = expected_hours_by_day(df)
    actual = df.groupby("delivery_date").size()
    partial = actual[actual != expected.reindex(actual.index)]

    return {
        "rows": len(df),
        "start_utc": df.index[0],
        "end_utc": df.index[-1],
        "partial_delivery_days": {d: int(n) for d, n in partial.items()},
        "short_days_23h": expected[expected == 23].index.intersection(actual.index).tolist(),
        "long_days_25h": expected[expected == 25].index.intersection(actual.index).tolist(),
        "negative_hours": int((df["price_gbp_mwh"] < 0).sum()),
        "complete_delivery_days": int(len(actual) - len(partial)),
    }


def expected_hours_by_day(df: pd.DataFrame) -> pd.Series:
    """Calendar length in hours of each GB delivery day (23, 24 or 25)."""
    out = {}
    for d in pd.unique(df["delivery_date"]):
        day = pd.Timestamp(d)
        start = day.tz_localize(LOCAL_TZ)
        end = (day + pd.Timedelta(days=1)).tz_localize(LOCAL_TZ)
        out[d] = int((end - start) / pd.Timedelta(hours=1))
    return pd.Series(out)


def complete_delivery_days(df: pd.DataFrame) -> pd.DataFrame:
    """Keep only delivery days that have every hour their calendar day should have.

    The battery optimiser works per delivery day, so truncated first/last days
    are excluded rather than silently optimised. Comparing against the real
    calendar length matters: a truncated 23-row day must not be mistaken for a
    genuine 23-hour spring-forward day.
    """
    expected = expected_hours_by_day(df)
    actual = df.groupby("delivery_date")["price_gbp_mwh"].transform("size")
    exp_per_row = df["delivery_date"].map(expected)
    return df[actual == exp_per_row].copy()
