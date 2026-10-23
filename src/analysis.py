from __future__ import annotations

import numpy as np
import pandas as pd


def matched_accuracy_vs_deadband(results: pd.DataFrame) -> pd.DataFrame:
    """Compare mechanisms against deadband at matched reconstruction MAE."""

    db = results[results["mechanism"] == "deadband"].copy()

    if len(db) < 2:
        raise ValueError("need at least two deadband runs to interpolate a baseline")

    if (db["reconstruction_mae"] < 0).any():
        raise ValueError("reconstruction_mae must be non-negative")

    if (db["trigger_rate"] <= 0).any() or (db["energy_total_uj"] <= 0).any():
        raise ValueError("trigger rates and energy must be positive")

    zero = db[db["reconstruction_mae"] == 0]
    positive = db[db["reconstruction_mae"] > 0]

    # Combine duplicate MAE values using the best observed metric values.
    positive = (
        positive.groupby("reconstruction_mae", as_index=False)
        .agg(
            trigger_rate=("trigger_rate", "min"),
            energy_total_uj=("energy_total_uj", "min"),
        )
        .sort_values("reconstruction_mae")
    )

    rows = []

    for _, r in results[results["mechanism"] != "deadband"].iterrows():
        mae = float(r["reconstruction_mae"])

        if mae < 0:
            continue

        if mae == 0:
            if zero.empty:
                continue

            db_rate = float(zero["trigger_rate"].min())
            db_energy = float(zero["energy_total_uj"].min())

        else:
            # Do not extrapolate outside the positive-MAE baseline range.
            if len(positive) < 2:
                continue

            min_mae = positive["reconstruction_mae"].min()
            max_mae = positive["reconstruction_mae"].max()

            if mae < min_mae or mae > max_mae:
                continue

            x_values = np.log(positive["reconstruction_mae"].to_numpy())
            x = np.log(mae)

            db_rate = float(np.exp(np.interp(
                x, x_values, np.log(positive["trigger_rate"].to_numpy())
            )))
            db_energy = float(np.exp(np.interp(
                x, x_values, np.log(positive["energy_total_uj"].to_numpy())
            )))

        rows.append({
            "run_label": r["run_label"],
            "mechanism": r["mechanism"],
            "mae": mae,
            "trigger_rate": r["trigger_rate"],
            "deadband_rate_at_same_mae": db_rate,
            "tx_ratio": r["trigger_rate"] / db_rate,
            "energy_ratio": r["energy_total_uj"] / db_energy,
        })

    return pd.DataFrame(rows)