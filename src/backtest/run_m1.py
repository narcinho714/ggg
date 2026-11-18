"""M1: perfect-foresight value ceiling vs the fixed-pattern benchmark.

Run from the project root:   python -m src.backtest.run_m1

Reads config/config.yaml, runs both strategies over every complete delivery day,
writes daily results to data/cache/ (git-ignored) and a chart to reports/.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import yaml

from src.backtest.backtest import run_backtest, summarise
from src.dispatch.battery import load_battery_params
from src.ingest.prices import complete_delivery_days, load_prices


def main(config_path: str = "config/config.yaml") -> None:
    with open(config_path, encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)
    params = load_battery_params(config_path)
    limit = cfg.get("solver", {}).get("time_limit_seconds")

    prices = complete_delivery_days(load_prices(cfg["paths"]["raw_prices"]))
    # Optional analysis window: set data_window.analysis_start in the config
    # (e.g. "2023-01-01") to report only from that delivery day onwards.
    start = cfg.get("data_window", {}).get("analysis_start")
    tag = ""
    if start:
        prices = prices[prices["delivery_date"] >= pd.Timestamp(start).date()]
        tag = f"_from_{start}"
    print(f"Analysis window: {start or 'full history'}")
    print(f"Complete delivery days: {prices['delivery_date'].nunique()}")

    results = {}
    for strategy in ("perfect_foresight", "benchmark"):
        daily = run_backtest(prices, params, strategy, time_limit_seconds=limit)
        results[strategy] = daily
        print(f"\n{strategy}")
        for k, v in summarise(daily).items():
            print(f"  {k}: {v:,.2f}" if isinstance(v, float) else f"  {k}: {v}")

    cache = Path(cfg["paths"]["cache_dir"])
    cache.mkdir(parents=True, exist_ok=True)
    for name, daily in results.items():
        daily.to_csv(cache / f"m1_daily_{name}{tag}.csv")

    out = Path(cfg["paths"]["outputs_dir"])
    out.mkdir(parents=True, exist_ok=True)
    summary = {name: summarise(d) for name, d in results.items()}
    text = json.dumps(summary, indent=2, default=str)
    (out / f"m1_summary{tag}.json").write_text(text, encoding="utf-8")

    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("\nmatplotlib not installed: skipping chart (pip install matplotlib)")
        return

    fig, ax = plt.subplots(figsize=(10, 5))
    for name, daily in results.items():
        monthly = daily["net_gbp_per_mw"].copy()
        monthly.index = pd.to_datetime(monthly.index)
        monthly.resample("MS").mean().plot(ax=ax, label=name.replace("_", " "))
    ax.set_ylabel("Net revenue, GBP per MW per day (monthly mean)")
    ax.set_xlabel("")
    ax.set_title("M1: perfect-foresight ceiling vs fixed-pattern benchmark")
    ax.legend()
    fig.tight_layout()
    fig.savefig(out / f"m1_ceiling{tag}.png", dpi=150)
    print(f"\nSaved {out / f'm1_ceiling{tag}.png'} and {out / f'm1_summary{tag}.json'}")


if __name__ == "__main__":
    main()
