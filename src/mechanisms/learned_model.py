"""
Mechanism C: lightweight on-device learned model (online SGD regressor),
dual-prediction scheme.

Node and receiver run the same small model. It predicts the next reading from
the RECEIVER-SIDE history (the reconstruction both ends share — never from raw
readings the receiver hasn't seen). The node transmits when the true reading
differs from that prediction by >= threshold; on a transmission both ends
learn from it (the update step), otherwise nobody learns.

Per-step work (what the hardware teammate measures separately):
    inference : every reading
    update    : only on transmitted readings

Inference and update are deliberately separate methods — do not merge them.

Robustness: window differences, the training target and the predicted delta are all
clipped to +-max_delta (default 1.0 signal-units per reading). Without this a single
sensor-glitch reading (a +20 degree spike) put huge values into the SGD update, the
weights diverged, and the mechanism then transmitted ~90% of all readings. Clipping
bounds any one reading's influence and changes nothing on well-behaved data.

The model predicts the next DELTA (next - last) from the window's consecutive
differences rather than absolute values. Raw temperatures (~20-40, not centred
at zero) make plain online SGD diverge within tens of steps; deltas are small
and near zero-centred, which keeps it stable without a separate scaler.

Same interface contract as the other mechanisms:
    trigger(values, **params) -> TriggerOutput(triggers, reconstruction)
"""

from __future__ import annotations

from typing import Sequence

import numpy as np
from sklearn.linear_model import SGDRegressor

from src.mechanisms.base import TriggerOutput


class LearnedModelTrigger:
    """Thin wrapper around SGDRegressor exposing separate infer()/update() steps."""

    def __init__(self, window_size: int = 5, max_delta: float = 1.0, **sgd_kwargs):
        if window_size < 2:
            raise ValueError("window_size must be >= 2 (need at least one difference)")
        if max_delta <= 0:
            raise ValueError("max_delta must be > 0")
        self.window_size = window_size
        self.max_delta = max_delta
        defaults = dict(max_iter=1, tol=None, warm_start=True, learning_rate="constant",
                        eta0=0.005, alpha=1e-3, random_state=0)
        defaults.update(sgd_kwargs)
        self.model = SGDRegressor(**defaults)
        self.fitted = False

    def _clip(self, a):
        return np.clip(a, -self.max_delta, self.max_delta)

    def _features(self, window: Sequence[float]) -> np.ndarray:
        # Clipped so one glitch reading can't inject a huge feature (which makes
        # online SGD diverge and never recover).
        return self._clip(np.diff(np.asarray(window, dtype=float))).reshape(1, -1)

    def infer(self, window: Sequence[float]) -> float:
        """Inference step ONLY — no learning happens here."""
        last = float(window[-1])
        if not self.fitted:
            return last  # persistence until the model has seen data
        return last + float(self._clip(self.model.predict(self._features(window))[0]))

    def update(self, window: Sequence[float], actual_value: float) -> None:
        """Update/learning step ONLY — adjusts the model using a transmitted reading."""
        y = np.array([float(self._clip(actual_value - float(window[-1])))], dtype=float)
        self.model.partial_fit(self._features(window), y)
        self.fitted = True


def learned_model_trigger(
    values: Sequence[float],
    threshold: float,
    window_size: int = 5,
    max_delta: float = 1.0,
    **sgd_kwargs,
) -> TriggerOutput:
    if threshold < 0:
        raise ValueError("threshold must be >= 0")
    if window_size < 2:
        raise ValueError("window_size must be >= 2 (need at least one difference)")

    model = LearnedModelTrigger(window_size=window_size, max_delta=max_delta, **sgd_kwargs)
    triggers: list[bool] = []
    recon: list[float] = []  # receiver-side history, shared by node and receiver

    for v in values:
        if len(recon) < window_size:
            # Warm-up: send everything until there is a full window to predict from.
            triggers.append(True)
            recon.append(float(v))
            continue

        window = recon[-window_size:]
        pred = model.infer(window)

        if abs(v - pred) >= threshold:
            triggers.append(True)
            model.update(window, v)  # learn only from transmitted readings
            recon.append(float(v))
        else:
            triggers.append(False)
            recon.append(pred)

    return TriggerOutput(triggers, recon)
