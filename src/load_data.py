"""
Data loading for SenseSmart.

Two entry points:
  - load_intel_lab_data(raw_path, moteid)  -> loads+cleans the raw Intel Berkeley
    Lab text file (space-separated, no header) into the canonical schema.
  - load_clean_csv(path)                    -> loads an already-cleaned CSV
    (timestamp,temperature,humidity) — this is what every mechanism and the
    harness actually consume, regardless of which source produced it
    (physical ESP32, Wokwi, this dataset, or a synthetic generator).

The canonical schema is the contract referenced throughout the project docs:
    columns = timestamp (parseable datetime), temperature (float), humidity (float)
    sorted strictly ascending by timestamp, no NaNs.
"""

from __future__ import annotations

import pandas as pd

# Official Intel Berkeley Research Lab sensor dataset columns.
INTEL_LAB_COLUMNS = ["date", "time", "epoch", "moteid", "temperature", "humidity", "light", "voltage"]

CANONICAL_COLUMNS = ["timestamp", "temperature", "humidity"]


def despike(df: pd.DataFrame, column: str = "temperature", window: int = 11,
            k: float = 6.0, floor: float = 0.1) -> tuple[pd.DataFrame, int]:
    """Drop isolated glitch readings (Hampel filter).

    A reading is a glitch if it differs from the rolling median of its
    neighbours by more than k * (robust spread), where the robust spread is the
    rolling MAD scaled to a standard deviation and never allowed below `floor`
    (flat/quantised stretches have MAD ~ 0, which would otherwise flag everything).
    A genuine step change that persists for more than ~window/2 readings moves the
    median with it and is NOT removed; short spikes are.

    Returns (cleaned_df, number_of_rows_dropped).
    """
    s = df[column]
    med = s.rolling(window, center=True, min_periods=1).median()
    mad = (s - med).abs().rolling(window, center=True, min_periods=1).median()
    spread = (1.4826 * mad).clip(lower=floor)
    glitch = (s - med).abs() > k * spread
    return df[~glitch].reset_index(drop=True), int(glitch.sum())


def load_intel_lab_data(raw_path: str, moteid: int = 1,
                         temp_bounds: tuple[float, float] = (-10, 50),
                         humidity_bounds: tuple[float, float] = (0, 100),
                         remove_glitches: bool = False) -> pd.DataFrame:
    """Load and clean the raw Intel Lab text file for a single mote.

    Drops rows with physically implausible readings (a known artifact of this
    raw dataset — see docs/SenseSmart_Master_Project_Document.md Section 8)
    and rows with unparseable timestamps, then sorts chronologically.
    """
    df = pd.read_csv(raw_path, sep=r"\s+", names=INTEL_LAB_COLUMNS, header=None, engine="python")

    df["timestamp"] = pd.to_datetime(df["date"] + " " + df["time"], errors="coerce")
    df = df[df["moteid"] == moteid]
    df = df[df["temperature"].between(*temp_bounds) & df["humidity"].between(*humidity_bounds)]
    df = df.dropna(subset=["timestamp", "temperature", "humidity"]).sort_values("timestamp")

    out = df[CANONICAL_COLUMNS].reset_index(drop=True)
    if remove_glitches:
        out, n_dropped = despike(out)
        print(f"despike: removed {n_dropped} glitch reading(s) ({n_dropped / (len(out) + n_dropped):.3%})")
    return validate_canonical(out)


def load_clean_csv(path: str) -> pd.DataFrame:
    """Load a dataset already in the canonical schema (timestamp,temperature,humidity).

    Use this for: a cleaned Intel Lab export, a physical ESP32/Wokwi CSV log, or a
    synthetic-generator output — any source is fine as long as it's in this shape.
    """
    df = pd.read_csv(path, parse_dates=["timestamp"])
    df = df.sort_values("timestamp").reset_index(drop=True)
    return validate_canonical(df[CANONICAL_COLUMNS])


def validate_canonical(df: pd.DataFrame) -> pd.DataFrame:
    """Fail loudly if a dataset doesn't satisfy the canonical-schema contract."""
    missing = [c for c in CANONICAL_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Dataset is missing required column(s): {missing}")
    if df[CANONICAL_COLUMNS].isna().any().any():
        raise ValueError("Dataset contains NaNs after cleaning — fix the source or tighten filters.")
    if not df["timestamp"].is_monotonic_increasing:
        raise ValueError("Dataset is not sorted ascending by timestamp.")
    if len(df) < 10:
        raise ValueError(f"Dataset has only {len(df)} rows after cleaning — too small to be useful.")
    return df


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Clean the raw Intel Lab dataset into the canonical schema.")
    parser.add_argument("raw_path", help="Path to the raw Intel Lab text file (e.g. data/data.txt)")
    parser.add_argument("--moteid", type=int, default=1)
    parser.add_argument("--out", default="data/clean_mote.csv")
    parser.add_argument("--despike", action="store_true",
                        help="also remove isolated glitch readings (Hampel filter); off by default")
    args = parser.parse_args()

    clean = load_intel_lab_data(args.raw_path, moteid=args.moteid, remove_glitches=args.despike)
    clean.to_csv(args.out, index=False)
    print(clean.describe())
    print(f"\n{len(clean)} clean rows saved to {args.out}")
