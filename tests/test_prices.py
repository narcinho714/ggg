from pathlib import Path

import pandas as pd
import pytest

from src.ingest.prices import complete_delivery_days, load_prices, validate_prices

DATA = Path(__file__).resolve().parents[1] / "data" / "raw" / "neso_n2ex_gb_da.csv"


@pytest.fixture(scope="module")
def prices():
    if not DATA.exists():
        pytest.skip("raw price file not present; see README quick start")
    return load_prices(DATA)


def test_index_is_tz_aware_utc_sorted_unique(prices):
    assert str(prices.index.tz) == "UTC"
    assert prices.index.is_monotonic_increasing
    assert not prices.index.has_duplicates


def test_hourly_and_contiguous(prices):
    steps = prices.index.to_series().diff().dropna()
    assert (steps == pd.Timedelta(hours=1)).all()


def test_no_missing_prices(prices):
    assert prices["price_gbp_mwh"].notna().all()


def test_validate_runs(prices):
    report = validate_prices(prices)
    assert report["rows"] == len(prices)
    assert report["negative_hours"] > 0


def test_spring_forward_day_has_23_local_hours(prices):
    day = prices[prices["delivery_date"] == pd.Timestamp("2022-03-27").date()]
    assert len(day) == 23


def test_autumn_back_day_has_25_local_hours(prices):
    day = prices[prices["delivery_date"] == pd.Timestamp("2022-10-30").date()]
    assert len(day) == 25


def test_ordinary_day_has_24_hours(prices):
    day = prices[prices["delivery_date"] == pd.Timestamp("2023-06-15").date()]
    assert len(day) == 24


def test_complete_days_filter_drops_partial_edges(prices):
    full = complete_delivery_days(prices)
    dates = set(full["delivery_date"])
    # truncated first and last days must be gone
    assert pd.Timestamp("2021-09-20").date() not in dates
    assert pd.Timestamp("2026-11-17").date() not in dates
    # genuine DST days must be kept
    assert pd.Timestamp("2022-03-27").date() in dates
    assert pd.Timestamp("2022-10-30").date() in dates


def test_truncated_last_day_is_not_mistaken_for_dst_day(prices):
    report = validate_prices(prices)
    assert pd.Timestamp("2026-11-17").date() in report["partial_delivery_days"]
    assert pd.Timestamp("2026-11-17").date() not in report["short_days_23h"]


def test_local_time_offset_flips_across_dst(prices):
    winter = prices.loc["2023-01-10 12:00", "local_time"]
    summer = prices.loc["2023-07-10 12:00", "local_time"]
    assert winter.utcoffset() == pd.Timedelta(0)
    assert summer.utcoffset() == pd.Timedelta(hours=1)


def test_rejects_bad_columns(tmp_path):
    bad = tmp_path / "bad.csv"
    bad.write_text("a,b\n1,2\n")
    with pytest.raises(ValueError):
        load_prices(bad)
