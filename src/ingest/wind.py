"""NESO transmission-connected wind: day-ahead forecast issued before the cut-off, as hourly UTC."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.ingest.cutoff import forecast_cutoff, load_cutoff_settings

DEFAULT_PATH = Path("data/raw/neso_wind_dayahead_historic.csv")


def load_wind_features(path=DEFAULT_PATH, config_path="config/config.yaml"):
    """Hourly UTC transmission wind forecast. Days issued after the cut-off are dropped.

    Forecast_Timestamp is read as UTC. If it were really UK clock time, reading it as
    UTC makes summer issues look an hour later than they were, which can only drop
    days, never let a late forecast through.
    """
    gate, buffer = load_cutoff_settings(config_path)
    df = pd.read_csv(path)
    df["start_utc"] = pd.to_datetime(df["Datetime_GMT"], utc=True)
    df["issued"] = pd.to_datetime(df["Forecast_Timestamp"], utc=True)
    df["delivery_date"] = pd.to_datetime(df["Date"])

    cutoffs = {d: forecast_cutoff(d, gate, buffer) for d in df["delivery_date"].unique()}
    df["cutoff"] = df["delivery_date"].map(cutoffs)
    df = df[df["issued"] <= df["cutoff"]]

    latest = df.groupby("delivery_date")["issued"].transform("max")
    df = df[df["issued"] == latest].copy()

    df["hour_utc"] = df["start_utc"].dt.floor("h")
    out = df.groupby("hour_utc").agg(
        delivery_date=("delivery_date", "first"),
        tx_wind_fc_mw=("Incentive_forecast", "mean"),
        tx_wind_capacity_mw=("Capacity", "mean"),
        wind_issued_utc=("issued", "first"),
        wind_cutoff_utc=("cutoff", "first"),
    )

    # Keep only delivery days with every hour present (23, 24 or 25).
    days = out["delivery_date"]
    expected = (
        (days + pd.Timedelta(days=1)).dt.tz_localize("Europe/London")
        - days.dt.tz_localize("Europe/London")
    ) / pd.Timedelta(hours=1)
    have = out.groupby("delivery_date")["tx_wind_fc_mw"].transform("size")
    return out[have == expected].sort_index()