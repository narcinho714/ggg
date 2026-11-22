"""Calendar features and lagged-price features, built so none looks past the cut-off."""
from __future__ import annotations

import holidays
import pandas as pd

LONDON = "Europe/London"


def calendar_features(index_utc):
    """Calendar features for each hourly UTC timestamp, from UK local time."""
    local = index_utc.tz_convert(LONDON)
    years = range(local.year.min(), local.year.max() + 1)
    bank_holidays = holidays.UnitedKingdom(subdiv="England", years=years)
    return pd.DataFrame(
        {
            "hour_local": local.hour,
            "day_of_week": local.dayofweek,
            "month": local.month,
            "is_weekend": local.dayofweek >= 5,
            "is_bank_holiday": [d in bank_holidays for d in local.date],
        },
        index=index_utc,
    )


def price_lag_features(prices, lag_hours=(24, 168)):
    """Lagged prices plus the previous delivery day's average.

    Prices for delivery day D-1 are public before the D-1 09:50 cut-off, so a lag is
    allowed only if the hour it comes from belongs to a delivery day before D.
    On a 25-hour day the last hour's 24-hour lag falls inside D itself, so it is
    set to NaN rather than leaked.
    """
    delivery = pd.to_datetime(prices["delivery_date"])
    out = pd.DataFrame(index=prices.index)
    for h in lag_hours:
        value = prices["price_gbp_mwh"].shift(h, freq="h").reindex(prices.index)
        source_day = delivery.shift(h, freq="h").reindex(prices.index)
        out[f"price_lag_{h}h"] = value.where(source_day < delivery)

    daily_mean = prices.groupby(delivery)["price_gbp_mwh"].mean()
    out["price_prev_day_mean"] = delivery.map(
        lambda d: daily_mean.get(d - pd.Timedelta(days=1))
    )
    return out