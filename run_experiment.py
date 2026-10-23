"""
End-to-end SenseSmart comparative study.

Usage:
    python run_experiment.py --data data/clean_mote1.csv --energy-source placeholder

What it does:
  1. Loads the dataset (already-cleaned CSV, canonical schema).
  2. Runs all three mechanisms (deadband, Kalman, learned model) over the
     'temperature' column, at a few parameter settings each, sweeping from
     "trigger almost everything" to "trigger almost nothing" so the
     energy-vs-accuracy trade-off is visible, not just one point per mechanism.
  3. Scores every run with the shared harness (reconstruction MAE + total
     energy, under whichever energy_source was requested).
  4. Saves a results table (CSV) and an energy-vs-accuracy plot to results/.

This is Phase 3 (energy_source=placeholder) and Phase 6 (energy_source=measured
or estimated) — literally the same script, only the --energy-source flag changes.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.analysis import matched_accuracy_vs_deadband
from src.energy_model import load_energy_model
from src.harness import run_harness
from src.load_data import load_clean_csv
from src.mechanisms.deadband import deadband_trigger
from src.mechanisms.kalman import kalman_trigger
from src.mechanisms.learned_model import learned_model_trigger


def sweep_deadband(values, thresholds):
    for t in thresholds:
        yield f"deadband(thr={t})", "deadband", deadband_trigger(values, threshold=t)


def sweep_kalman(values, thresholds, process_var=1e-6, measurement_var=0.01, gate=10.0):
    for t in thresholds:
        yield f"kalman(thr={t})", "kalman", kalman_trigger(
            values, process_var=process_var, measurement_var=measurement_var,
            innovation_threshold=t, innovation_gate=gate)


def sweep_learned_model(values, thresholds, window_size=5):
    for t in thresholds:
        yield f"learned_model(thr={t})", "learned_model", learned_model_trigger(
            values, threshold=t, window_size=window_size)


def main():
    parser = argparse.ArgumentParser(description="SenseSmart comparative study")
    parser.add_argument("--data", default="data/clean_mote1.csv",
                        help="Path to a canonical-schema CSV (timestamp,temperature,humidity)")
    parser.add_argument("--energy-source", default="placeholder",
                        choices=["placeholder", "measured", "estimated"])
    parser.add_argument("--energy-data", default=None,
                        help="energy JSON (default: the one shipped in src/)")
    parser.add_argument("--out", default="results/comparison.csv")
    parser.add_argument("--plot", default="results/energy_vs_accuracy.png")
    parser.add_argument("--thresholds", nargs="+", type=float,
                        default=[0.05, 0.1, 0.2, 0.4, 0.8, 1.5])
    parser.add_argument("--kalman-q", type=float, default=1e-6,
                        help="Kalman process variance (trend noise per step^2)")
    parser.add_argument("--kalman-r", type=float, default=0.01,
                        help="Kalman measurement variance (sensor noise)")
    parser.add_argument("--kalman-gate", type=float, default=10.0,
                        help="glitch gate (multiples of the threshold); 0 disables it")
    parser.add_argument("--learned-window", type=int, default=5)
    args = parser.parse_args()

    df = load_clean_csv(args.data)
    values = df["temperature"].tolist()
    print(f"Loaded {len(values)} readings from {args.data}")

    energy_model = load_energy_model(source=args.energy_source, path=args.energy_data)
    print(f"Using energy source: '{energy_model.source}'")

    rows = []
    for label, mech_name, output in list(sweep_deadband(values, args.thresholds)) + \
                                        list(sweep_kalman(values, args.thresholds, args.kalman_q,
                                                          args.kalman_r,
                                                          args.kalman_gate or None)) + \
                                        list(sweep_learned_model(values, args.thresholds,
                                                                  args.learned_window)):
        result = run_harness(mech_name, values, output, energy_model)
        result["run_label"] = label
        rows.append(result)
        print(f"  {label:28s} trigger_rate={result['trigger_rate']:.3f}  "
              f"MAE={result['reconstruction_mae']:.4f}  "
              f"E_total={result['energy_total_uj']:.1f} uJ")

    results_df = pd.DataFrame(rows)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    results_df.to_csv(args.out, index=False)
    print(f"\nResults table saved to {args.out}")

    matched = matched_accuracy_vs_deadband(results_df)
    if len(matched):
        print("\nAt EQUAL reconstruction error, compared with deadband (ratio < 1 = better than deadband):")
        for _, m in matched.iterrows():
            print(f"  {m['run_label']:28s} MAE={m['mae']:.4f}  transmissions x{m['tx_ratio']:.2f}  "
                  f"energy x{m['energy_ratio']:.3f}")
        matched.to_csv(Path(args.out).with_name("matched_vs_deadband.csv"), index=False)

    fig, ax = plt.subplots(figsize=(7, 5))
    for mech, group in results_df.groupby("mechanism"):
        group_sorted = group.sort_values("reconstruction_mae")
        ax.plot(group_sorted["reconstruction_mae"], group_sorted["energy_total_uj"],
                marker="o", label=mech)
    ax.set_xlabel("Reconstruction MAE (lower = more accurate)")
    ax.set_ylabel("Total energy per run (uJ, lower = cheaper)")
    ax.set_title(f"Energy vs. accuracy trade-off (energy_source='{energy_model.source}')")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    Path(args.plot).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.plot, dpi=150)
    print(f"Plot saved to {args.plot}")


if __name__ == "__main__":
    main()
