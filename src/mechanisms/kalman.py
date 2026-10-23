"""
Mechanism B: classical Kalman filter, dual-prediction scheme.

Node and receiver run the SAME constant-velocity Kalman filter (state =
[value, trend]). Between transmissions neither side has a measurement, so
both just run the predict step and the receiver's picture of the signal is
the extrapolated estimate. The node transmits only when the true reading
differs from the receiver's current prediction by >= innovation_threshold;
on a transmission BOTH sides run the update step with that reading, so they
stay in lock-step.

Per-step work (this is what the hardware teammate measures and what the
harness charges for):
    predict : every reading (node and receiver both)
    update  : only on transmitted readings

Same interface contract as deadband.py:
    trigger(values, **params) -> TriggerOutput(triggers, reconstruction)
"""

from __future__ import annotations

from typing import Sequence

import numpy as np

from src.mechanisms.base import TriggerOutput


def kalman_trigger(
    values: Sequence[float],
    process_var: float,
    measurement_var: float,
    innovation_threshold: float,
    innovation_gate: float | None = 10.0,
) -> TriggerOutput:
    """
    process_var (q): acceleration noise — how much the trend may change per step^2
    measurement_var (r): assumed sensor noise variance
    innovation_threshold: transmit when |reading - receiver's prediction| >= this
    innovation_gate: robustness against sensor glitches. The innovation used in the UPDATE
        step is clipped to +-(innovation_gate * innovation_threshold), so one wild reading
        (a 20 degree spike) cannot wreck the trend estimate and cause a burst of
        corrective transmissions. Measured on simulated data (threshold 0.1): ungated,
        15 glitches cost 1025 transmissions (deadband: 604); gate=10 costs 480; a
        persistent 3-degree step embedded in a realistic signal costs 209 vs 203
        ungated. Caveat: on an artificially FLAT signal a big step takes a burst of
        ~40 transmissions to converge, because the gate rate-limits state changes.
        None disables the gate.
    """
    if process_var < 0 or measurement_var <= 0 or innovation_threshold < 0:
        raise ValueError("process_var/innovation_threshold must be >= 0, measurement_var must be > 0")
    if innovation_gate is not None and innovation_gate <= 0:
        raise ValueError("innovation_gate must be > 0 (or None to disable)")

    F = np.array([[1.0, 1.0], [0.0, 1.0]])
    Q = process_var * np.array([[0.25, 0.5], [0.5, 1.0]])
    H = np.array([[1.0, 0.0]])
    R = measurement_var

    triggers: list[bool] = []
    recon: list[float] = []
    x = None  # state [value, trend]
    P = None

    for v in values:
        if x is None:
            x = np.array([v, 0.0])
            P = np.diag([measurement_var, 1.0])
            triggers.append(True)  # first reading must always be sent
            recon.append(float(v))
            continue

        # Predict (both node and receiver, every step)
        x = F @ x
        P = F @ P @ F.T + Q

        if abs(v - x[0]) >= innovation_threshold:
            # Update (both sides, only when a reading is actually transmitted)
            S = float((H @ P @ H.T)[0, 0] + R)
            K = (P @ H.T / S).ravel()
            innovation = v - x[0]
            if innovation_gate is not None:
                limit = max(innovation_gate * innovation_threshold, 1e-12)
                innovation = float(np.clip(innovation, -limit, limit))
            x = x + K * innovation
            P = (np.eye(2) - np.outer(K, H.ravel())) @ P
            triggers.append(True)
            # The receiver was SENT this exact reading, so that is what it shows for
            # this step (same as deadband and the learned model). The filtered state x
            # is internal and only drives the predictions for the following steps.
            recon.append(float(v))
        else:
            triggers.append(False)
            recon.append(float(x[0]))

    return TriggerOutput(triggers, recon)
