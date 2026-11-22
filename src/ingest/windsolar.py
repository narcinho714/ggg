"""NESO embedded wind and solar forecasts: latest run before the cut-off, as hourly UTC."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.ingest.cutoff import forecast_cutoff, load_cutoff_settings

LONDON = "Europe/London"
USECOLS = [
    "SETTLEMENT_DATE",
    "SETTLEMENT_PERIOD",
    "EMBEDDED_WIND_FORECAST",
    "EMBEDDED_SOLAR_FORECAST",
    "Forecast_Datetime",
]
# A run older than this, relative to the cut-off, counts as stale: that day is dropped.
MAX_FORECAST_AGE_HOURS = 6
CHUNK_ROWS = 500_000

def _clock(series):
    """Read timestamps as plain clock times, ignoring any Z or +00:00 suffix."""
    return pd.to_datetime(series, utc=True).dt.tz_localize(None)
def _candidates(chunk, gate, buffer):
    """Keep only rows from runs issued shortly before the cut-off for their delivery day."""
    chunk = chunk.copy()
    chunk["delivery_date"] = _clock(chunk["SETTLEMENT_DATE"])

    # Forecast_Datetime is UK clock time. Ambiguous or non-existent clock-change
    # hours become NaT and are dropped (they are never near 09:50).
    chunk["issued"] = (
        _clock(chunk["Forecast_Datetime"])
        .dt.tz_localize(LONDON, ambiguous="NaT", nonexistent="NaT")
        .dt.tz_convert("UTC")
    
    )
    chunk = chunk.dropna(subset=["issued"])

    cutoffs = {d: forecast_cutoff(d, gate, buffer) for d in chunk["delivery_date"].unique()}
    chunk["cutoff"] = chunk["delivery_date"].map(cutoffs)

    age = chunk["cutoff"] - chunk["issued"]
    keep = (age >= pd.Timedelta(0)) & (age <= pd.Timedelta(hours=MAX_FORECAST_AGE_HOURS))
    return chunk.loc[keep].drop(columns=["Forecast_Datetime"])


def load_embedded_features(raw_dir="data/raw", config_path="config/config.yaml"):
    """Hourly UTC wind and solar forecast, one run per delivery day, none after the cut-off."""
    gate, buffer = load_cutoff_settings(config_path)

    parts = []
    for path in sorted(Path(raw_dir).glob("embedded_archive_*.csv")):
        for chunk in pd.read_csv(path, usecols=USECOLS, chunksize=CHUNK_ROWS):
            parts.append(_candidates(chunk, gate, buffer))
    cand = pd.concat(parts, ignore_index=True)

    # Settlement period 1 starts at UK local midnight of the settlement date and
    # every period is 30 real minutes, so 23- and 25-hour days come out right.
    midnight_utc = cand["delivery_date"].dt.tz_localize(LONDON).dt.tz_convert("UTC")
    cand["start_utc"] = midnight_utc + pd.to_timedelta(
        (cand["SETTLEMENT_PERIOD"] - 1) * 30, unit="m"
    )

    # Keep only the latest run for each delivery day.
    latest = cand.groupby("delivery_date")["issued"].transform("max")
    cand = cand[cand["issued"] == latest]

    cand["hour_utc"] = cand["start_utc"].dt.floor("h")
    out = cand.groupby("hour_utc").agg(
        delivery_date=("delivery_date", "first"),
        wind_fc_mw=("EMBEDDED_WIND_FORECAST", "mean"),
        solar_fc_mw=("EMBEDDED_SOLAR_FORECAST", "mean"),
        ws_issued_utc=("issued", "first"),
        ws_cutoff_utc=("cutoff", "first"),
    )
    return out.sort_index()