"""M2: score the baseline forecasts under walk-forward validation and save everything."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from src.features.build import OUT_PATH as FEATURES_PATH
from src.forecast.baselines import naive_forecasts, ridge_walk_forward
from src.forecast.evaluate import score
from src.forecast.splits import load_split_settings, walk_forward_splits

PRED_PATH = Path("data/cache/m2_predictions.parquet")
SUMMARY_PATH = Path("reports/m2_baselines.json")
BY_HOUR_PATH = Path("reports/m2_mae_by_hour.csv")


def run(config_path="config/config.yaml"):
    table = pd.read_parquet(FEATURES_PATH)
    min_train, step = load_split_settings(config_path)
    splits = list(walk_forward_splits(table["delivery_date"], min_train, step))

    ridge = ridge_walk_forward(table, splits)
    test = table.loc[ridge.index]
    preds = naive_forecasts(test).assign(ridge=ridge)

    summary = {
        "validation": {
            "min_train_days": min_train,
            "step_days": step,
            "folds": len(splits),
            "first_test_day": str(splits[0][1][0].date()),
            "last_test_day": str(splits[-1][1][-1].date()),
        },
        "models": {name: score(test, preds[name]) for name in preds},
    }

    err = preds.sub(test["price_gbp_mwh"], axis=0).abs()
    by_hour = err.groupby(test["hour_local"]).mean().round(3)

    out = preds.assign(delivery_date=test["delivery_date"], actual=test["price_gbp_mwh"])
    for path in (PRED_PATH, SUMMARY_PATH):
        path.parent.mkdir(parents=True, exist_ok=True)
    out.to_parquet(PRED_PATH)
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    by_hour.to_csv(BY_HOUR_PATH)
    return summary, by_hour


if __name__ == "__main__":
    summary, by_hour = run()
    v = summary["validation"]
    print(f"{v['folds']} folds, test days {v['first_test_day']} to {v['last_test_day']}")
    print(pd.DataFrame(summary["models"]).round(3))
    print(f"Written: {SUMMARY_PATH}, {BY_HOUR_PATH}, {PRED_PATH}")