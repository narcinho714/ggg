"""NESO day-ahead demand forecast: pick the latest issue before the cut-off, make daily features."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.ingest.cutoff import forecast_cutoff, load_cutoff_settings

DEFAULT_PATH = Path("data/raw/archive_1dayahead.csv")


def load_demand_features(path=DEFAULT_PATH, config_path="config/config.yaml"):
    """One row per delivery date, using only forecasts issued at or before the cut-off."""
    gate, buffer = load_cutoff_settings(config_path)
    df = pd.read_csv(path)
    df["issued"] = pd.to_datetime(df["FORECAST_TIMESTAMP"], utc=True)
    df["delivery_date"] = pd.to_datetime(df["TARGETDATE"])

    cutoffs = {d: forecast_cutoff(d, gate, buffer) for d in df["delivery_date"].unique()}
    df["cutoff"] = df["delivery_date"].map(cutoffs)

    ok = df[df["issued"] <= df["cutoff"]]
    latest = ok.groupby("delivery_date")["issued"].transform("max")
    ok = ok[ok["issued"] == latest]

    out = ok.groupby("delivery_date").agg(
        demand_fc_max_mw=("FORECASTDEMAND", "max"),
        demand_fc_min_mw=("FORECASTDEMAND", "min"),
        demand_fc_n_points=("FORECASTDEMAND", "size"),
        demand_fc_issued_utc=("issued", "first"),
        cutoff_utc=("cutoff", "first"),
    )
    out["demand_fc_range_mw"] = out["demand_fc_max_mw"] - out["demand_fc_min_mw"]
    return out