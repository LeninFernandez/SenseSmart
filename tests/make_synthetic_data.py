"""
Generates a small synthetic dataset in the canonical schema, purely so the
pipeline can be tested end-to-end without the real Intel Lab file (which
lives on the project laptop, not here). This is a TEST FIXTURE ONLY — it is
not a substitute for the real dataset and should not be used for actual
results (see the Master Doc's Appendix on the fallback plan for the
difference between a test fixture and a reportable synthetic-data fallback).
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def make_synthetic_dataset(n=2000, seed=0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    t = pd.date_range("2026-01-01", periods=n, freq="2s")

    # Slow diurnal-ish drift + a couple of step changes + sensor noise —
    # same spirit as the appendix's Scenario A/B/C, combined into one series.
    drift = 22 + 3 * np.sin(np.linspace(0, 6 * np.pi, n))
    steps = np.zeros(n)
    steps[n // 3:] += 2.0
    steps[2 * n // 3:] -= 3.5
    noise = rng.normal(0, 0.15, n)
    temperature = drift + steps + noise

    humidity = 40 + 5 * np.cos(np.linspace(0, 4 * np.pi, n)) + rng.normal(0, 0.5, n)

    return pd.DataFrame({"timestamp": t, "temperature": temperature, "humidity": humidity})


if __name__ == "__main__":
    df = make_synthetic_dataset()
    df.to_csv("tests/synthetic_clean.csv", index=False)
    print(f"Wrote {len(df)} synthetic rows to tests/synthetic_clean.csv")
