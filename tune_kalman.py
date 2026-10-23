"""
Tune the Kalman filter's q (process_var) and r (measurement_var) fairly.

Why this exists: the Kalman result swings from much better to much worse than deadband
depending on (q, r) -- the defaults in run_experiment.py are an arbitrary starting point,
not a tuned configuration. Comparing a tuned-by-nobody Kalman with a parameter-free
deadband is not a fair test.

Method (no peeking): choose (q, r) on the FIRST part of the data (--train-frac), then report
the result on the REMAINING part, which tuning never saw. Quote the held-out numbers.
The deadband baseline is evaluated on the same part with the same thresholds.

Usage:
    python tune_kalman.py --data data\\clean_mote1.csv
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from src.harness import reconstruction_mae
from src.load_data import load_clean_csv
from src.mechanisms.deadband import deadband_trigger
from src.mechanisms.kalman import kalman_trigger

DEFAULT_QS = [1e-8, 1e-7, 1e-6, 1e-5, 1e-4, 1e-3]
DEFAULT_RS = [4e-4, 1.6e-3, 1e-2, 1e-1]
DEFAULT_THRESHOLDS = [0.1, 0.2, 0.4, 0.8]
BASE_THRESHOLDS = [0.05, 0.1, 0.2, 0.4, 0.8, 1.5, 3.0]   # deadband curve to interpolate


def _stats(values, out):
    return float(np.mean(out.triggers)), reconstruction_mae(values, out.reconstruction)


def deadband_curve(values):
    pts = sorted(_stats(values, deadband_trigger(values, t))[::-1] for t in BASE_THRESHOLDS)  # (mae, rate)
    return np.log([p[0] for p in pts]), np.log([p[1] for p in pts]), pts[0][0], pts[-1][0]


def matched_ratio(values, q, r, thresholds, curve, gate=10.0):
    """Mean over thresholds of (kalman tx rate) / (deadband tx rate at the same MAE).
    <1 = fewer transmissions than deadband at equal error. NaN if fewer than 2 usable thresholds."""
    lm, lr, lo, hi = curve
    ratios = []
    for th in thresholds:
        rate, mae = _stats(values, kalman_trigger(values, q, r, th, gate))
        if lo <= mae <= hi and mae > 0:
            ratios.append(rate / np.exp(np.interp(np.log(mae), lm, lr)))
    return float(np.mean(ratios)) if len(ratios) >= 2 else float("nan")


def tune(values, qs=DEFAULT_QS, rs=DEFAULT_RS, thresholds=DEFAULT_THRESHOLDS,
         train_frac=0.5, defaults=(1e-6, 1e-2), gate=10.0):
    values = np.asarray(values, dtype=float)
    cut = int(len(values) * train_frac)
    train, test = values[:cut], values[cut:]
    if len(train) < 500 or len(test) < 500:
        raise ValueError("need at least 500 readings in both the train and test parts")
    c_train, c_test = deadband_curve(train), deadband_curve(test)
    grid = [{"q": q, "r": r, "train_ratio": matched_ratio(train, q, r, thresholds, c_train, gate)}
            for q in qs for r in rs]
    valid = [g for g in grid if not np.isnan(g["train_ratio"])]
    if not valid:
        raise ValueError("no (q, r) produced a usable result; widen --thresholds")
    best = min(valid, key=lambda g: g["train_ratio"])
    return {
        "grid": grid, "best": best, "n_train": len(train), "n_test": len(test),
        "test_best": matched_ratio(test, best["q"], best["r"], thresholds, c_test, gate),
        "test_default": matched_ratio(test, defaults[0], defaults[1], thresholds, c_test, gate),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", default="data/clean_mote1.csv")
    ap.add_argument("--train-frac", type=float, default=0.5)
    ap.add_argument("--thresholds", nargs="+", type=float, default=DEFAULT_THRESHOLDS)
    ap.add_argument("--kalman-gate", type=float, default=10.0, help="0 disables")
    ap.add_argument("--qs", nargs="+", type=float, default=DEFAULT_QS, help="grid for q")
    ap.add_argument("--rs", nargs="+", type=float, default=DEFAULT_RS, help="grid for r")
    ap.add_argument("--out", default="results/kalman_tuning.csv")
    a = ap.parse_args()

    df = load_clean_csv(a.data)
    res = tune(df["temperature"].to_numpy(), qs=a.qs, rs=a.rs, thresholds=a.thresholds, train_frac=a.train_frac,
               gate=a.kalman_gate or None)

    print(f"Train: first {res['n_train']} readings | held-out test: last {res['n_test']} readings")
    print("Ratio = Kalman transmissions / deadband transmissions at equal error (below 1 = Kalman better)")
    print(f"\nTraining-part grid (rows q, columns r):")
    g = pd.DataFrame(res["grid"]).pivot(index="q", columns="r", values="train_ratio")
    print(g.round(2).to_string())
    b = res["best"]
    print(f"\nBest on training part: q={b['q']:g}, r={b['r']:g}  (train ratio {b['train_ratio']:.2f})")
    edge = [n for n, val, grid in (("q", b["q"], a.qs), ("r", b["r"], a.rs))
            if len(grid) > 1 and val in (min(grid), max(grid))]
    if edge:
        print(f"WARNING: best {' and '.join(edge)} sits on the edge of the grid -- the true optimum may be "
              f"outside it. Re-run with a wider --qs / --rs range.")
    print("\nHELD-OUT result (the number to quote):")
    print(f"  tuned   (q={b['q']:g}, r={b['r']:g}): {res['test_best']:.2f}")
    print(f"  default (q=1e-06, r=0.01):        {res['test_default']:.2f}")
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(res["grid"]).to_csv(a.out, index=False)
    print(f"\nGrid saved to {a.out}")
    print(f"Re-run the benchmark with:  python run_experiment.py --data {a.data} "
          f"--kalman-q {b['q']:g} --kalman-r {b['r']:g}")


if __name__ == "__main__":
    main()
