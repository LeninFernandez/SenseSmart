"""
Mechanism A: deadband / send-on-delta.

The free baseline. Only transmit a reading if it has moved at least
`threshold` away from the last value actually sent. The receiver simply holds
the last transmitted value.

Interface contract shared by all three mechanisms:
    trigger(values, **params) -> TriggerOutput(triggers, reconstruction)
`values` must be in chronological order; no look-ahead.
"""

from __future__ import annotations

from typing import Sequence

from src.mechanisms.base import TriggerOutput, hold_reconstruction


def deadband_trigger(values: Sequence[float], threshold: float) -> TriggerOutput:
    if threshold < 0:
        raise ValueError("threshold must be >= 0")

    triggers: list[bool] = []
    last_sent = None

    for v in values:
        if last_sent is None or abs(v - last_sent) >= threshold:
            triggers.append(True)
            last_sent = v
        else:
            triggers.append(False)

    return TriggerOutput(triggers, hold_reconstruction(values, triggers))
