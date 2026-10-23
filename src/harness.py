"""
Shared evaluation harness.

Scores any mechanism's TriggerOutput on the project's headline metrics:
  - reconstruction MAE: true readings vs. what the RECEIVER believes (the
    mechanism's own reconstruction — hold for deadband, extrapolated
    prediction for Kalman / learned model)
  - trigger count / rate
  - total energy via the pluggable EnergyModel (never a hardcoded number)

No knowledge of where `values` came from (ESP32, Wokwi, Intel Lab, synthetic)
and none of which energy source is active (placeholder/measured/estimated).
"""

from __future__ import annotations

from typing import Sequence

import numpy as np

from src.energy_model import EnergyModel
from src.mechanisms.base import TriggerOutput

# Which energy_data.json keys each mechanism pays, and how often:
#   "every" -> once per reading (sensed step, transmitted or not)
#   "tx"    -> only on transmitted readings
COMPUTE_COSTS = {
    "deadband": [("deadband_compute_uj", "every")],
    "kalman": [("kalman_predict_uj", "every"), ("kalman_update_uj", "tx")],
    "learned_model": [("ml_inference_uj", "every"), ("ml_update_uj", "tx")],
}


def reconstruction_mae(values: Sequence[float], reconstruction: Sequence[float]) -> float:
    values = np.asarray(values, dtype=float)
    reconstruction = np.asarray(reconstruction, dtype=float)
    if len(values) != len(reconstruction):
        raise ValueError("values and reconstruction must be the same length")
    if len(values) == 0:
        raise ValueError("values must be non-empty")
    return float(np.mean(np.abs(values - reconstruction)))


def energy_breakdown(n_readings: int, n_tx: int, energy_model: EnergyModel,
                     compute_spec: list[tuple[str, str]]) -> dict:
    """Every reading pays wake-up + sensing; transmitted readings also pay tx;
    compute is charged per `compute_spec`. Sleep current is reported, not summed
    (it's a rate, not a per-event cost)."""
    e_wake = n_readings * energy_model.cost("wake_up_uj")
    e_sense = n_readings * energy_model.cost("sensor_read_uj")
    e_tx = n_tx * energy_model.cost("tx_uj")
    e_compute = 0.0
    for key, when in compute_spec:
        e_compute += energy_model.cost(key) * (n_readings if when == "every" else n_tx)

    return {
        "n_readings": n_readings,
        "n_transmitted": n_tx,
        "trigger_rate": n_tx / n_readings if n_readings else 0.0,
        "energy_wake_uj": e_wake,
        "energy_sense_uj": e_sense,
        "energy_compute_uj": e_compute,
        "energy_tx_uj": e_tx,
        "energy_total_uj": e_wake + e_sense + e_compute + e_tx,
        "sleep_current_ua": energy_model.cost("sleep_current_ua"),
        "energy_source": energy_model.source,
    }


def run_harness(mechanism_name: str, values: Sequence[float], output: TriggerOutput,
                energy_model: EnergyModel) -> dict:
    if mechanism_name not in COMPUTE_COSTS:
        raise ValueError(f"Unknown mechanism_name '{mechanism_name}'. Options: {list(COMPUTE_COSTS)}")
    if len(output.triggers) != len(values):
        raise ValueError("mechanism output length does not match values length")

    mae = reconstruction_mae(values, output.reconstruction)
    energy = energy_breakdown(len(values), output.n_transmitted, energy_model,
                              COMPUTE_COSTS[mechanism_name])
    return {"mechanism": mechanism_name, "reconstruction_mae": mae, **energy}
