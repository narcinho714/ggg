"""Walk-forward splits: train on every day so far, test on the next block of days."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import yaml


def walk_forward_splits(days, min_train_days, step_days):
    """Yield (train_days, test_days) pairs, both sorted.

    Counts days that exist in the data, not calendar days. Every training day is
    earlier than every test day in its fold, and each day is tested exactly once.
    """
    days = pd.DatetimeIndex(sorted(pd.unique(pd.to_datetime(days))))
    if min_train_days < 1 or step_days < 1:
        raise ValueError("min_train_days and step_days must both be at least 1")
    if len(days) <= min_train_days:
        raise ValueError(f"Only {len(days)} days, need more than {min_train_days}")
    for start in range(min_train_days, len(days), step_days):
        yield days[:start], days[start:start + step_days]


def load_split_settings(path="config/config.yaml"):
    cfg = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    v = cfg.get("validation") or {}
    if v.get("min_train_days") is None or v.get("step_days") is None:
        raise ValueError("validation.min_train_days and validation.step_days must be set")
    return int(v["min_train_days"]), int(v["step_days"])