"""
The pluggable energy backend — the "use INA219 measurements or not" switch.

Energy numbers never live inside harness.py or any mechanism. They live in
energy_data.json, in three labeled blocks that all share the same operation
keys (see ENERGY_KEYS below). Which block is used is one string
(`energy_source=...`) — never a code change.

    "placeholder" -> literature-derived values, used for Phase 3's dry run
    "measured"    -> real INA219 measurements from the hardware teammate (Phase 5/6)
    "estimated"   -> datasheet-current x on-device-timed-duration fallback,
                     used if the INA219 measurement doesn't come through in time
"""

from __future__ import annotations

import json
from pathlib import Path
from dataclasses import dataclass, field

ENERGY_KEYS = [
    "sleep_current_ua",
    "wake_up_uj",
    "sensor_read_uj",
    "tx_uj",
    "deadband_compute_uj",
    "kalman_predict_uj",
    "kalman_update_uj",
    "ml_inference_uj",
    "ml_update_uj",
]


@dataclass
class EnergyModel:
    source: str
    values: dict = field(default_factory=dict)

    def cost(self, operation: str) -> float:
        if operation not in self.values:
            raise KeyError(
                f"Unknown energy operation '{operation}'. Known keys: {ENERGY_KEYS}"
            )
        value = self.values[operation]
        if value is None:
            raise ValueError(
                f"Energy value for '{operation}' is null in the '{self.source}' block of "
                f"energy_data.json — fill it in before running with this source."
            )
        return float(value)


DEFAULT_ENERGY_DATA = Path(__file__).resolve().parent / "energy_data.json"


def load_energy_model(source: str = "placeholder", path=None) -> EnergyModel:
    if path is None:
        path = DEFAULT_ENERGY_DATA  # works from any working directory
    with open(path, encoding="utf-8") as f:
        all_sources = json.load(f)

    if source not in all_sources:
        raise ValueError(f"Unknown energy source '{source}'. Options: {list(all_sources.keys())}")

    values = all_sources[source]
    missing = [k for k in ENERGY_KEYS if k not in values]
    if missing:
        raise ValueError(f"energy_data.json['{source}'] is missing key(s): {missing}")

    return EnergyModel(source=source, values=values)
