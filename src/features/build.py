"""Join every leak-safe input into one hourly feature table, and check it for leakage."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import yaml

from src.features.basic import calendar_features, price_lag_features
from src.ingest.cutoff import forecast_cutoff, load_cutoff_settings
from src.ingest.prices import complete_delivery_days

OUT_PATH = Path("data/cache/features.parquet")
ISSUED_COLUMNS = ["demand_fc_issued_utc", "ws_issued_utc", "wind_issued_utc"]
LONDON = "Europe/London"


def build_feature_table(prices, demand, embedded, wind, start, gate="09:50", buffer=0):
    """One row per delivery hour. price_gbp_mwh is the target, never a feature."""
    p = complete_delivery_days(prices)
    table = pd.DataFrame(index=p.index)
    table["delivery_date"] = pd.to_datetime(p["delivery_date"])
    table["price_gbp_mwh"] = p["price_gbp_mwh"]
    table = table.join(price_lag_features(p)).join(calendar_features(p.index))

    table = table.join(embedded[["wind_fc_mw", "solar_fc_mw", "ws_issued_utc"]], how="inner")
    table = table.join(
        wind[["tx_wind_fc_mw", "tx_wind_capacity_mw", "wind_issued_utc"]], how="inner"
    )
    table = table.join(demand.drop(columns="cutoff_utc"), on="delivery_date", how="inner")
    table = table[table["delivery_date"] >= pd.Timestamp(start)]

    cutoffs = {d: forecast_cutoff(d, gate, buffer) for d in table["delivery_date"].unique()}
    table["cutoff_utc"] = table["delivery_date"].map(cutoffs)

    # Keep only delivery days where every source supplied every hour.
    days = table["delivery_date"]
    expected = (
        (days + pd.Timedelta(days=1)).dt.tz_localize(LONDON) - days.dt.tz_localize(LONDON)
    ) / pd.Timedelta(hours=1)
    have = table.groupby("delivery_date")["price_gbp_mwh"].transform("size")
    return table[have == expected].sort_index()


def check_no_leakage(table):
    """Raise if any forecast was issued after its cut-off or a row sits in the wrong day."""
    for col in ISSUED_COLUMNS:
        late = table[col] > table["cutoff_utc"]
        if late.any():
            raise ValueError(f"{col}: {late.sum()} rows issued after the cut-off")
    local_day = pd.to_datetime(table.index.tz_convert(LONDON).date)
    if (local_day != table["delivery_date"].to_numpy()).any():
        raise ValueError("Some rows are attached to the wrong delivery day")


def main(config_path="config/config.yaml"):
    from src.ingest.demand import load_demand_features
    from src.ingest.prices import load_prices
    from src.ingest.wind import load_wind_features
    from src.ingest.windsolar import load_embedded_features

    cfg = yaml.safe_load(Path(config_path).read_text(encoding="utf-8"))
    start = cfg["data_window"]["analysis_start"]
    gate, buffer = load_cutoff_settings(config_path)

    table = build_feature_table(
        prices=load_prices("data/raw/neso_n2ex_gb_da.csv"),
        demand=load_demand_features(),
        embedded=load_embedded_features(),
        wind=load_wind_features(),
        start=start,
        gate=gate,
        buffer=buffer,
    )
    check_no_leakage(table)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    table.to_parquet(OUT_PATH)
    print(f"{len(table)} rows, {table['delivery_date'].nunique()} delivery days, "
          f"{table['delivery_date'].min().date()} to {table['delivery_date'].max().date()}")
    print(f"Leakage check passed. Written to {OUT_PATH}")


if __name__ == "__main__":
    main()