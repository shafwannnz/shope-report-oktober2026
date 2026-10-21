"""Jalankan seluruh pipeline: ETL -> analisis -> simulasi -> grafik -> ekspor untuk Laravel.

    python run_all.py [--raw data/raw/shopee_orders_2026-10.xlsx] [--reps 5000]
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from pipeline import analytics, charts, etl, simulation  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", default=str(HERE / "data/raw/shopee_orders_2026-10.xlsx"))
    ap.add_argument("--reps", type=int, default=simulation.N_REP)
    a = ap.parse_args()

    out = HERE / "output"; out.mkdir(exist_ok=True)
    print("[1/4] ETL ...")
    lines, orders = etl.run(Path(a.raw), HERE / "data/processed")
    print(f"      {len(lines)} baris item, {len(orders)} pesanan")

    print("[2/4] Analisis pola & anomali ...")
    R = analytics.analyse(lines, orders)

    print(f"[3/4] Simulasi Monte Carlo ({a.reps} replikasi) ...")
    import pandas as pd
    daily = analytics.daily_table(orders, R["window"]["last_full_day"])
    S = simulation.simulate(orders, lines, daily, R["promo_days"], n_rep=a.reps)

    print("[4/4] Grafik ...")
    pl = charts.plotly_charts(R, S)
    static_dir = HERE.parent / "public" / "charts"
    st = charts.static_charts(lines, orders, R, S, static_dir)

    (out / "results.json").write_text(json.dumps({"analysis": R, "simulation": S, "static_charts": st},
                                                 ensure_ascii=False, default=str, indent=1))
    (out / "plotly_charts.json").write_text(json.dumps(pl, ensure_ascii=False))
    print("Selesai ->", out)


if __name__ == "__main__":
    main()
