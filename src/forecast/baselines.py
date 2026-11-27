"""Baseline price forecasts. Every forecast uses only columns built before the cut-off."""
from __future__ import annotations

import pandas as pd

NUMERIC = [
    "price_lag_24h", "price_lag_168h", "price_prev_day_mean",
    "demand_fc_max_mw", "demand_fc_min_mw", "demand_fc_range_mw",
    "wind_fc_mw", "solar_fc_mw", "tx_wind_fc_mw", "tx_wind_capacity_mw",
    "wind_total_mw", "is_weekend", "is_bank_holiday",
]
CATEGORICAL = ["hour_local", "day_of_week", "month"]
RIDGE_ALPHA = 1.0  # fixed, not tuned: tuning would need its own inner validation


def naive_forecasts(table):
    """Same hour yesterday, and same hour last week.

    On the one hour per autumn clock change where the 24-hour lag is blanked
    (it would fall inside the delivery day), fall back to the previous day's mean.
    """
    return pd.DataFrame(
        {
            "naive_24h": table["price_lag_24h"].fillna(table["price_prev_day_mean"]),
            "naive_168h": table["price_lag_168h"],
        },
        index=table.index,
    )


def _inputs(table):
    x = table.copy()
    x["wind_total_mw"] = x["wind_fc_mw"] + x["tx_wind_fc_mw"]
    x[["is_weekend", "is_bank_holiday"]] = x[["is_weekend", "is_bank_holiday"]].astype(float)
    return x[NUMERIC + CATEGORICAL]


def _ridge_pipeline():
    from sklearn.compose import ColumnTransformer
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import Ridge
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import OneHotEncoder, StandardScaler

    prep = ColumnTransformer([
        ("num", make_pipeline(SimpleImputer(strategy="median"), StandardScaler()), NUMERIC),
        ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL),
    ])
    return make_pipeline(prep, Ridge(alpha=RIDGE_ALPHA))


def ridge_walk_forward(table, splits):
    """Refit ridge on each fold's training days, then forecast that fold's test days.

    Scaling and missing-value filling are learned inside the pipeline,
    so they only ever see training rows.
    """
    preds = []
    for train_days, test_days in splits:
        train = table[table["delivery_date"].isin(train_days)]
        test = table[table["delivery_date"].isin(test_days)]
        model = _ridge_pipeline().fit(_inputs(train), train["price_gbp_mwh"])
        preds.append(pd.Series(model.predict(_inputs(test)), index=test.index))
    return pd.concat(preds).rename("ridge").sort_index()