"""Forecast scores: size and direction of error, and whether the right hours are picked."""
from __future__ import annotations

import numpy as np
import pandas as pd


def error_metrics(actual, pred):
    err = (pred - actual).dropna()
    return {
        "n_hours": int(len(err)),
        "mae": float(err.abs().mean()),
        "rmse": float(np.sqrt((err**2).mean())),
        "bias": float(err.mean()),
    }


def hour_pick_scores(actual, pred, delivery_date):
    """How well the forecast picks each day's cheapest and dearest hour.

    hit:    share of days where the forecast picks exactly the right hour.
    regret: average £/MWh lost by using the forecast's pick instead of the best hour,
            judged at actual prices (0 on days it picks right).
    """
    df = pd.DataFrame({"a": actual, "p": pred, "day": delivery_date}).dropna()
    g = df.groupby("day")
    pick_cheap, pick_dear = g["p"].idxmin(), g["p"].idxmax()
    best_cheap, best_dear = g["a"].idxmin(), g["a"].idxmax()
    a = df["a"]
    return {
        "n_days": int(g.ngroups),
        "cheapest_hour_hit": float((pick_cheap == best_cheap).mean()),
        "dearest_hour_hit": float((pick_dear == best_dear).mean()),
        "cheapest_hour_regret": float((a[pick_cheap].to_numpy() - a[best_cheap].to_numpy()).mean()),
        "dearest_hour_regret": float((a[best_dear].to_numpy() - a[pick_dear].to_numpy()).mean()),
    }


def score(table, pred):
    """All scores for one forecast against table['price_gbp_mwh']."""
    actual = table["price_gbp_mwh"]
    out = error_metrics(actual, pred)
    out.update(hour_pick_scores(actual, pred, table["delivery_date"]))
    return out