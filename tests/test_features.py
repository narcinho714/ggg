from pathlib import Path

import pandas as pd
import pytest

from src.features.build import OUT_PATH, check_no_leakage


@pytest.fixture
def table():
    if not Path(OUT_PATH).exists():
        pytest.skip("feature table not built; run python -m src.features.build")
    return pd.read_parquet(OUT_PATH)


def test_no_forecast_issued_after_cutoff(table):
    check_no_leakage(table)


def test_every_day_is_complete(table):
    hours = table.groupby("delivery_date").size()
    assert set(hours.unique()) <= {23, 24, 25}


def test_check_catches_a_late_forecast(table):
    bad = table.copy()
    bad.iloc[0, bad.columns.get_loc("wind_issued_utc")] = (
        bad["cutoff_utc"].iloc[0] + pd.Timedelta(minutes=1)
    )
    with pytest.raises(ValueError):
        check_no_leakage(bad)