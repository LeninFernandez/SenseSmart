"""
Shared output type for all three trigger mechanisms.

Every mechanism returns BOTH:
  - triggers:        which readings the node transmits
  - reconstruction:  what the RECEIVER believes the signal is at every step

Why both: the fair comparison is "how close is the receiver's picture of the
world to reality, for how many transmissions". Deadband's receiver just holds
the last value; Kalman's and the learned model's receivers run the same
predictor as the node (dual prediction, Jain et al. 2004) and extrapolate
between transmissions. Scoring all three with a hold-last-value receiver would
throw away exactly the thing the predictive mechanisms exist to provide.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass
class TriggerOutput:
    triggers: list[bool]
    reconstruction: list[float]

    def __post_init__(self):
        if len(self.triggers) != len(self.reconstruction):
            raise ValueError("triggers and reconstruction must be the same length")

    @property
    def n_transmitted(self) -> int:
        return int(sum(self.triggers))


def hold_reconstruction(values: Sequence[float], triggers: Sequence[bool]) -> list[float]:
    """Zero-order-hold receiver: repeat the last transmitted value."""
    out: list[float] = []
    last = values[0]
    for v, t in zip(values, triggers):
        if t:
            last = v
        out.append(last)
    return out
