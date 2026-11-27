import pandas as pd

from src.forecast.splits import load_split_settings, walk_forward_splits

DAYS = pd.date_range("2023-01-02", periods=500).to_series().iloc[::2]  # gappy, like the real data


def test_train_always_before_test():
    for train, test in walk_forward_splits(DAYS, 100, 28):
        assert train.max() < test.min()


def test_every_day_after_first_block_tested_once():
    tested = [d for _, test in walk_forward_splits(DAYS, 100, 28) for d in test]
    assert len(tested) == len(set(tested)) == len(DAYS) - 100


def test_training_window_expands():
    sizes = [len(train) for train, _ in walk_forward_splits(DAYS, 100, 28)]
    assert sizes == sorted(sizes) and sizes[0] == 100


def test_config_settings_are_set():
    assert load_split_settings() == (365, 28)

from src.forecast.evaluate import score

def test_regret_matches_hand_calculation():
    idx = pd.date_range("2025-01-01", periods=48, freq="h", tz="UTC")
    a = pd.Series(60.0, index=idx)
    a.iloc[[3, 27]] = 50.0      # cheapest hour each day
    a.iloc[[18, 42]] = 100.0    # dearest hour each day
    a.iloc[29], a.iloc[44] = 54.0, 90.0
    p = a.copy()
    p.iloc[27], p.iloc[29] = 70.0, 40.0   # day 2: forecast picks the £54 hour to charge
    p.iloc[42], p.iloc[44] = 80.0, 120.0  # day 2: forecast picks the £90 hour to discharge
    t = pd.DataFrame({"price_gbp_mwh": a, "delivery_date": [d.date() for d in idx]})
    s = score(t, p)
    assert s["cheapest_hour_hit"] == 0.5 and s["dearest_hour_hit"] == 0.5
    assert s["cheapest_hour_regret"] == 2.0   # (0 + 4) / 2
    assert s["dearest_hour_regret"] == 5.0    # (0 + 10) / 2