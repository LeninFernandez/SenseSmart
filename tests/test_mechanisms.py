"""
Unit + integration tests for SenseSmart's software track.

Run with: pytest tests/ -v

The most important tests are the ERROR-BOUND ones: a mechanism that doesn't
transmit must still leave the receiver within `threshold` of the truth. An
earlier version of this project only tested trigger COUNTS, which let a design
flaw through (predictive mechanisms triggered rarely but the receiver drifted
far from reality). Counting transmissions without checking accuracy proves
nothing.
"""

import json
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.energy_model import EnergyModel, load_energy_model, ENERGY_KEYS
from src.harness import reconstruction_mae, run_harness, energy_breakdown, COMPUTE_COSTS
from src.load_data import validate_canonical, CANONICAL_COLUMNS
from src.mechanisms.base import TriggerOutput
from src.mechanisms.deadband import deadband_trigger
from src.mechanisms.kalman import kalman_trigger
from src.mechanisms.learned_model import learned_model_trigger
from tests.make_synthetic_data import make_synthetic_dataset

ROOT = Path(__file__).resolve().parent.parent


def realistic_series(n=6000, seed=0):
    """Smooth diurnal-ish drift + slow weather wander + small sensor noise."""
    rng = np.random.default_rng(seed)
    t = np.arange(n)
    weather = np.cumsum(rng.normal(0, 0.004, n))
    return list(22 + 2.5 * np.sin(2 * np.pi * t / 2880) + weather + rng.normal(0, 0.04, n))


MECHANISMS = {
    "deadband": lambda v, thr: deadband_trigger(v, threshold=thr),
    "kalman": lambda v, thr: kalman_trigger(v, process_var=1e-6, measurement_var=0.01,
                                            innovation_threshold=thr),
    "learned_model": lambda v, thr: learned_model_trigger(v, threshold=thr, window_size=5),
}


# ---------- Shared contract, all mechanisms ----------

@pytest.mark.parametrize("name", MECHANISMS)
def test_first_reading_always_sent(name):
    out = MECHANISMS[name]([5.0, 5.0, 5.0, 5.0, 5.0, 5.0, 5.0], 1.0)
    assert out.triggers[0] is True


@pytest.mark.parametrize("name", MECHANISMS)
def test_output_shapes_match_input(name):
    v = realistic_series(300)
    out = MECHANISMS[name](v, 0.1)
    assert isinstance(out, TriggerOutput)
    assert len(out.triggers) == len(v) == len(out.reconstruction)


@pytest.mark.parametrize("name", MECHANISMS)
@pytest.mark.parametrize("thr", [0.05, 0.2, 0.8])
def test_receiver_error_bounded_by_threshold_on_untransmitted_steps(name, thr):
    """THE key invariant. If the node stays silent, the receiver's picture must
    be within `thr` of the truth — that is the entire promise of event-triggering."""
    v = realistic_series()
    out = MECHANISMS[name](v, thr)
    for x, rec, sent in zip(v, out.reconstruction, out.triggers):
        if not sent:
            assert abs(x - rec) < thr + 1e-9


@pytest.mark.parametrize("name", MECHANISMS)
def test_looser_threshold_never_sends_more(name):
    v = realistic_series()
    tight = MECHANISMS[name](v, 0.05).n_transmitted
    loose = MECHANISMS[name](v, 0.5).n_transmitted
    assert loose <= tight


@pytest.mark.parametrize("name", MECHANISMS)
def test_mae_no_worse_than_threshold(name):
    v = realistic_series()
    thr = 0.3
    out = MECHANISMS[name](v, thr)
    assert reconstruction_mae(v, out.reconstruction) <= thr


# ---------- Mechanism A: deadband ----------

def test_deadband_flat_signal_triggers_once():
    assert deadband_trigger([5.0] * 20, threshold=0.5).n_transmitted == 1


def test_deadband_rejects_negative_threshold():
    with pytest.raises(ValueError):
        deadband_trigger([1, 2, 3], threshold=-1)


def test_deadband_receiver_holds_last_sent_value():
    out = deadband_trigger([1.0, 1.1, 1.2, 3.0, 3.1], threshold=1.0)
    assert out.reconstruction == [1.0, 1.0, 1.0, 3.0, 3.0]


# ---------- Mechanism B: Kalman ----------

def test_kalman_flat_signal_triggers_rarely():
    assert kalman_trigger([5.0] * 100, 1e-6, 0.01, 0.5).n_transmitted <= 2


def test_kalman_extrapolates_a_trend_with_few_transmissions():
    """The reason a predictive mechanism exists: on a steady ramp deadband must
    keep sending, but a trend-aware filter learns the slope and goes quiet."""
    v = list(np.linspace(20, 30, 2000))  # clean ramp, slope 0.005/step
    deadband_tx = deadband_trigger(v, 0.1).n_transmitted
    kalman_tx = kalman_trigger(v, 1e-6, 0.01, 0.1).n_transmitted
    assert kalman_tx < deadband_tx / 3


def test_kalman_rejects_invalid_params():
    with pytest.raises(ValueError):
        kalman_trigger([1, 2, 3], process_var=0.1, measurement_var=0, innovation_threshold=0.1)


# ---------- Mechanism C: learned model ----------

def test_learned_model_warms_up_then_runs():
    out = learned_model_trigger(realistic_series(200), threshold=0.3, window_size=5)
    assert all(out.triggers[:5])


def test_learned_model_short_series_is_all_warmup():
    out = learned_model_trigger([1.0, 2.0, 3.0], threshold=0.1, window_size=5)
    assert out.triggers == [True, True, True]


def test_learned_model_stays_numerically_stable():
    """Regression: an earlier version predicted raw absolute values and its SGD
    diverged into the billions within ~20 readings."""
    v = realistic_series(5000)
    out = learned_model_trigger(v, threshold=0.05, window_size=5)
    assert np.all(np.isfinite(out.reconstruction))
    assert max(abs(r - x) for r, x in zip(out.reconstruction, v)) < 1.0


def test_learned_model_rejects_bad_params():
    with pytest.raises(ValueError):
        learned_model_trigger([1, 2, 3], threshold=-0.1)
    with pytest.raises(ValueError):
        learned_model_trigger([1, 2, 3], threshold=0.1, window_size=1)


# ---------- Harness / energy accounting ----------

def test_reconstruction_mae_zero_when_perfect():
    assert reconstruction_mae([1.0, 2.0, 3.0], [1.0, 2.0, 3.0]) == 0.0


def test_reconstruction_mae_rejects_mismatched_lengths():
    with pytest.raises(ValueError):
        reconstruction_mae([1, 2, 3], [1, 2])


def test_update_cost_charged_only_on_transmissions():
    model = EnergyModel(source="placeholder",
                        values={**{k: 0.0 for k in ENERGY_KEYS},
                                "kalman_predict_uj": 1.0, "kalman_update_uj": 100.0})
    e = energy_breakdown(n_readings=1000, n_tx=10, energy_model=model,
                         compute_spec=COMPUTE_COSTS["kalman"])
    assert e["energy_compute_uj"] == 1000 * 1.0 + 10 * 100.0


def test_energy_total_is_sum_of_parts():
    model = load_energy_model("placeholder", str(ROOT / "src" / "energy_data.json"))
    v = realistic_series(1000)
    r = run_harness("kalman", v, MECHANISMS["kalman"](v, 0.1), model)
    parts = r["energy_wake_uj"] + r["energy_sense_uj"] + r["energy_compute_uj"] + r["energy_tx_uj"]
    assert r["energy_total_uj"] == pytest.approx(parts)


def test_run_harness_rejects_unknown_mechanism():
    model = load_energy_model("placeholder", str(ROOT / "src" / "energy_data.json"))
    v = realistic_series(100)
    with pytest.raises(ValueError):
        run_harness("nonsense", v, MECHANISMS["deadband"](v, 0.1), model)


# ---------- Energy backend (the INA219 on/off switch) ----------

def test_placeholder_block_has_every_key():
    model = load_energy_model("placeholder", str(ROOT / "src" / "energy_data.json"))
    for key in ENERGY_KEYS:
        assert model.cost(key) >= 0


def test_energy_model_raises_on_null_value():
    model = EnergyModel(source="measured", values={k: None for k in ENERGY_KEYS})
    with pytest.raises(ValueError):
        model.cost("tx_uj")


def test_energy_source_switch_changes_numbers_without_code_change(tmp_path):
    data = {"placeholder": {k: 1.0 for k in ENERGY_KEYS},
            "measured": {k: None for k in ENERGY_KEYS},
            "estimated": {k: 2.0 for k in ENERGY_KEYS}}
    path = tmp_path / "energy_data.json"
    path.write_text(json.dumps(data))
    assert load_energy_model("placeholder", str(path)).cost("tx_uj") == 1.0
    assert load_energy_model("estimated", str(path)).cost("tx_uj") == 2.0


# ---------- Data loading ----------

def test_synthetic_dataset_passes_canonical_validation():
    df = make_synthetic_dataset(n=500)
    assert list(validate_canonical(df[CANONICAL_COLUMNS]).columns) == CANONICAL_COLUMNS


def test_validate_canonical_rejects_missing_column():
    import pandas as pd
    bad = pd.DataFrame({"timestamp": pd.date_range("2026-01-01", periods=20),
                        "temperature": range(20)})
    with pytest.raises(ValueError):
        validate_canonical(bad)


# ---------- Receiver shows the transmitted value on transmit steps ----------

@pytest.mark.parametrize("name", MECHANISMS)
def test_receiver_shows_exact_reading_on_transmitted_steps(name):
    """On a transmitted step the receiver HAS the true reading, so all three
    mechanisms must show it (an asymmetry here once penalised Kalman unfairly)."""
    v = realistic_series(2000)
    out = MECHANISMS[name](v, 0.1)
    for x, rec, sent in zip(v, out.reconstruction, out.triggers):
        if sent:
            assert rec == pytest.approx(x)


# ---------- Robustness to sensor glitches ----------

def glitchy_series(n=4000, n_glitches=12, seed=7):
    rng = np.random.default_rng(seed)
    v = np.array(realistic_series(n))
    idx = rng.choice(np.arange(50, n - 5), n_glitches, replace=False)
    v[idx] += rng.uniform(8, 25, n_glitches)
    return list(v)


def test_learned_model_survives_glitch_readings():
    """Regression: without clipping, a handful of +20 degree glitches made online SGD
    diverge and the mechanism transmitted ~90% of ALL readings afterwards."""
    v = glitchy_series()
    learned = learned_model_trigger(v, threshold=0.1).n_transmitted
    deadband = deadband_trigger(v, 0.1).n_transmitted
    assert learned < 2 * deadband


def test_kalman_survives_glitch_readings():
    v = glitchy_series()
    kalman = kalman_trigger(v, 1e-6, 0.01, 0.1).n_transmitted
    deadband = deadband_trigger(v, 0.1).n_transmitted
    assert kalman < 1.3 * deadband


def test_kalman_gate_still_tracks_a_genuine_persistent_step():
    """The glitch gate must not cripple tracking of a REAL step change: a persistent
    +3 degree step inside a realistic signal should cost no more than deadband."""
    v = list(np.array(realistic_series(3000)) + np.r_[np.zeros(1000), np.full(2000, 3.0)])
    kalman = kalman_trigger(v, 1e-6, 0.01, 0.1).n_transmitted
    deadband = deadband_trigger(v, 0.1).n_transmitted
    assert kalman <= 1.2 * deadband


def test_kalman_rejects_bad_gate():
    with pytest.raises(ValueError):
        kalman_trigger([1, 2, 3], 1e-6, 0.01, 0.1, innovation_gate=0)


def test_learned_model_rejects_bad_max_delta():
    with pytest.raises(ValueError):
        learned_model_trigger([1, 2, 3], threshold=0.1, max_delta=0)


# ---------- Loader (previously untested) ----------

def _write_intel_file(path, rows):
    path.write_text("\n".join(" ".join(str(c) for c in r) for r in rows) + "\n")


def _intel_rows(n, mote=1, start_epoch=1):
    return [("2004-03-01", f"00:{i // 60:02d}:{i % 60:02d}.000000", start_epoch + i, mote,
             20.0 + 0.01 * i, 40.0, 10.0, 2.7) for i in range(n)]


def test_intel_loader_drops_garbage_other_motes_and_sorts(tmp_path):
    from src.load_data import load_intel_lab_data
    rows = _intel_rows(30)
    rows.append(("2004-03-01", "00:45:00.000000", 99, 1, 122.153, -3.91901, 11.04, 2.03397))  # glitch row
    rows += _intel_rows(30, mote=2)                                                          # other mote
    rows.reverse()                                                                           # unsorted input
    raw = tmp_path / "raw.txt"
    _write_intel_file(raw, rows)

    df = load_intel_lab_data(str(raw), moteid=1)
    assert len(df) == 30
    assert df["timestamp"].is_monotonic_increasing
    assert df["temperature"].between(-10, 50).all()
    assert list(df.columns) == CANONICAL_COLUMNS


def test_despike_removes_short_glitch_but_keeps_persistent_step():
    import pandas as pd
    from src.load_data import despike
    rng = np.random.default_rng(1)
    base = np.r_[np.full(300, 22.0), np.full(200, 25.0), np.full(300, 22.0)] + rng.normal(0, 0.03, 800)

    _, dropped_clean = despike(pd.DataFrame({"temperature": base}))
    assert dropped_clean == 0  # a persistent 3-degree step is real signal

    glitchy = base.copy()
    glitchy[100:102] += 8.0
    cleaned, dropped = despike(pd.DataFrame({"temperature": glitchy}))
    assert dropped == 2
    assert cleaned["temperature"].max() < 26


# ---------- Matched-accuracy analysis ----------

def test_matched_accuracy_ratio_is_one_for_identical_curve():
    import pandas as pd
    from src.analysis import matched_accuracy_vs_deadband
    db = pd.DataFrame({"mechanism": "deadband", "run_label": [f"d{i}" for i in range(4)],
                       "reconstruction_mae": [0.02, 0.04, 0.08, 0.16],
                       "trigger_rate": [0.2, 0.1, 0.05, 0.025],
                       "energy_total_uj": [130e6, 107e6, 92e6, 85e6]})
    other = db.assign(mechanism="kalman", run_label=lambda d: "k" + d["run_label"])
    out = matched_accuracy_vs_deadband(pd.concat([db, other], ignore_index=True))
    assert len(out) == 4
    assert out["tx_ratio"].between(0.99, 1.01).all()
    assert out["energy_ratio"].between(0.99, 1.01).all()


def test_matched_accuracy_detects_a_better_mechanism_and_skips_out_of_range():
    import pandas as pd
    from src.analysis import matched_accuracy_vs_deadband
    db = pd.DataFrame({"mechanism": "deadband", "run_label": ["a", "b", "c"],
                       "reconstruction_mae": [0.02, 0.04, 0.08],
                       "trigger_rate": [0.2, 0.1, 0.05], "energy_total_uj": [3.0, 2.0, 1.5]})
    better = pd.DataFrame({"mechanism": "kalman", "run_label": ["in", "out"],
                           "reconstruction_mae": [0.04, 0.5],       # 0.5 is outside deadband's range
                           "trigger_rate": [0.05, 0.001], "energy_total_uj": [1.9, 1.0]})
    out = matched_accuracy_vs_deadband(pd.concat([db, better], ignore_index=True))
    assert list(out["run_label"]) == ["in"]
    assert out["tx_ratio"].iloc[0] == pytest.approx(0.5, rel=0.02)


def test_default_energy_file_loads_from_any_working_directory(tmp_path, monkeypatch):
    """Default energy JSON must resolve relative to the package, not the cwd."""
    monkeypatch.chdir(tmp_path)
    model = load_energy_model("placeholder")
    assert model.cost("tx_uj") > 0


def test_energy_json_is_read_as_utf8(tmp_path):
    """The shipped JSON contains non-ASCII (em dashes in notes); Windows default
    encoding is cp1252, so the loader must pin utf-8."""
    import json
    src = ROOT / "src" / "energy_data.json"
    data = json.loads(src.read_text(encoding="utf-8"))
    p = tmp_path / "e.json"
    p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    assert load_energy_model("placeholder", str(p)).cost("tx_uj") > 0

def test_matched_accuracy_handles_zero_mae_without_warning():
    import warnings
    import pandas as pd
    from src.analysis import matched_accuracy_vs_deadband

    db = pd.DataFrame({
        "mechanism": ["deadband"] * 3,
        "run_label": ["d0", "d1", "d2"],
        "reconstruction_mae": [0.0, 0.0, 0.1],
        "trigger_rate": [1.0, 0.5, 0.1],
        "energy_total_uj": [100.0, 80.0, 20.0],
    })

    other = pd.DataFrame({
        "mechanism": ["kalman"],
        "run_label": ["k0"],
        "reconstruction_mae": [0.0],
        "trigger_rate": [0.25],
        "energy_total_uj": [40.0],
    })

    with warnings.catch_warnings():
        warnings.simplefilter("error", RuntimeWarning)
        out = matched_accuracy_vs_deadband(
            pd.concat([db, other], ignore_index=True)
        )

    assert len(out) == 1
    assert out.iloc[0]["mae"] == 0.0
    assert out.iloc[0]["tx_ratio"] == pytest.approx(0.5)
    assert out.iloc[0]["energy_ratio"] == pytest.approx(0.5)