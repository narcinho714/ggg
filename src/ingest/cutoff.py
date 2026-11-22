"""Forecast cut-off: the latest moment information may be used for a delivery day."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import yaml

LONDON = "Europe/London"


def forecast_cutoff(delivery_date, gate_closure_local="09:50", buffer_minutes=0):
    """Return the cut-off as a UTC timestamp.

    For delivery day D the cut-off is gate closure (UK clock time) on D-1,
    minus an optional safety buffer.
    """
    day_before = pd.Timestamp(delivery_date).normalize() - pd.Timedelta(days=1)
    hour, minute = (int(x) for x in gate_closure_local.split(":"))
    local = pd.Timestamp(
        year=day_before.year, month=day_before.month, day=day_before.day,
        hour=hour, minute=minute, tz=LONDON,
    )
    return (local - pd.Timedelta(minutes=buffer_minutes)).tz_convert("UTC")


def _find_key(node, key):
    if isinstance(node, dict):
        if key in node:
            return node[key]
        for value in node.values():
            found = _find_key(value, key)
            if found is not None:
                return found
    return None


def load_cutoff_settings(path="config/config.yaml"):
    cfg = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    gate = _find_key(cfg, "gate_closure_local")
    if gate is None:
        raise ValueError("gate_closure_local is not set in the config")
    buffer = _find_key(cfg, "forecast_cutoff_buffer_minutes")
    return str(gate), int(buffer or 0)