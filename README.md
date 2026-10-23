# SenseSmart — Software Track

This is the complete, tested software pipeline for SenseSmart's Phases 0–3
(and ready for Phase 6 the moment real/estimated energy numbers come in
from the hardware side). Everything below has already been run and
verified — see "What was tested" at the bottom.

## What's in here

```
sensesmart/
├── run_experiment.py          <- the one script you actually run
├── requirements.txt
├── src/
│   ├── load_data.py           <- Intel Lab raw-file loader/cleaner (+ optional --despike) + generic CSV loader
│   ├── analysis.py            <- matched-accuracy comparison vs deadband
│   ├── harness.py             <- shared evaluation harness (MAE + energy, mechanism-agnostic)
│   ├── energy_model.py        <- the pluggable energy backend (the INA219 on/off switch)
│   ├── energy_data.json       <- placeholder / measured / estimated energy values
│   └── mechanisms/
│       ├── deadband.py        <- Mechanism A
│       ├── kalman.py          <- Mechanism B
│       └── learned_model.py   <- Mechanism C
├── tests/
│   ├── make_synthetic_data.py <- synthetic data generator — TEST FIXTURE ONLY, not for real results
│   └── test_mechanisms.py     <- 55 tests, all passing (unit + integration + error-bound + robustness)
├── data/                      <- EMPTY on purpose — put your real dataset here (see below)
├── results/                   <- EMPTY on purpose — run_experiment.py fills this in
└── docs/                      <- the master doc, literature survey, and both track docs
```

## What YOU need to do (the only manual step)

1. Drop your raw Intel Lab data file into `data/` (e.g. `data/data.txt`).
2. Clean it into the canonical schema:
   ```
   python src/load_data.py data/data.txt --moteid 1 --out data/clean_mote1.csv
   ```
   (If your raw file already has different mote IDs with better coverage, try
   `--moteid 2`, `3`, etc. — same idea as before: eyeball the row count and
   the `describe()` output for sanity.)
3. Run the full comparison:
   ```
   python run_experiment.py --data data/clean_mote1.csv --energy-source placeholder
   ```
4. Check `results/comparison.csv` and `results/energy_vs_accuracy.png`.

That's it — that's Phase 3, done, with real data instead of the synthetic
fixture this was tested against.

## Switching energy sources later (Phase 6)

Once your teammate's hardware numbers come back (real INA219 measurements,
or the datasheet-estimated fallback — see `docs/SenseSmart_Track_B_Hardware.md`),
fill in the `"measured"` (or `"estimated"`) block of `src/energy_data.json`
with the 9 keys listed there, then just re-run:

```
python run_experiment.py --data data/clean_mote1.csv --energy-source measured
```

No code changes. That's the entire point of `energy_model.py` — this was
tested end-to-end (see below) by swapping in dummy "measured" values and
confirming the output changes with zero code edits.

## Running the tests yourself

```
pip install -r requirements.txt
pytest tests/ -v
```

Should show `55 passed`.

## How the three mechanisms work (read this before interpreting results)

All three return a `TriggerOutput`: which readings the node transmits, AND
what the *receiver* believes the signal is at every step. Accuracy (MAE) is
measured between the truth and the receiver's belief.

- **Deadband:** transmit when a reading is >= threshold from the last sent value. Receiver holds the last value.
- **Kalman / Learned model (dual prediction):** node and receiver run the *same* predictor. Between transmissions both just predict (the receiver's belief is the extrapolation). The node transmits when the true reading is >= threshold from that prediction; on a transmission both sides update. Kalman is a constant-velocity filter; the learned model is an online SGD regressor predicting the next change.
- **Energy accounting:** every reading pays wake-up + sensing. Transmitted readings also pay tx. Kalman/learned pay their *predict/inference* cost on every reading but their *update* cost only on transmitted readings. Sensing + wake-up are an identical floor for all three mechanisms, so at very low trigger rates the energy curves bunch together — that is the model working, not a bug.

## Sensor glitches (spikes) — read this, it changes how you interpret results

The raw Intel Lab data contains glitch readings (e.g. a 49.9 C reading in an indoor lab).
Simulation showed that a handful of glitches badly hurt the predictive mechanisms if
they are not defended against:

- **Learned model, unprotected:** a few +20 C glitches made online SGD diverge, after which
  it transmitted ~85-98% of ALL readings. Fixed: window differences, training target and
  predicted delta are clipped to +-`max_delta` (default 1.0).
- **Kalman, unprotected:** one glitch corrupted the trend estimate and triggered a burst of
  corrective transmissions (15 glitches cost 1025 transmissions vs deadband's 604). Fixed: an
  innovation gate (`--kalman-gate`, default 10 x threshold) limits how far one reading can move
  the filter: 480 transmissions with the gate. Cost: after a genuine large step on an
  artificially flat signal convergence takes a burst of ~40 transmissions; inside a realistic
  signal a persistent 3 C step cost 209 vs 203 ungated (deadband: 278).
- **Scoring fix:** on a transmitted step the receiver shows the exact transmitted reading for
  ALL mechanisms. Before, Kalman showed its filtered estimate there and was charged for it.

To see how much glitches matter on YOUR data, run the benchmark twice:

```
python src\load_data.py data\data.txt --moteid 1 --out data\clean_mote1.csv
python src\load_data.py data\data.txt --moteid 1 --despike --out data\clean_mote1_despiked.csv
python run_experiment.py --data data\clean_mote1.csv --out results\raw.csv --plot results\raw.png
python run_experiment.py --data data\clean_mote1_despiked.csv --out results\despiked.csv --plot results\despiked.png
```

`--despike` prints how many readings it removed. Quick glitch check on the cleaned file:
`python -c "import pandas as pd; d=pd.read_csv('data/clean_mote1.csv'); print((d.temperature>32).sum(), d.temperature.nlargest(8).round(1).tolist())"`

## How to read the results

`run_experiment.py` prints, after the table, a comparison **at equal reconstruction error**
(also saved to `results/matched_vs_deadband.csv`). Ratio < 1 means better than deadband.
That is the number to quote, not comparisons at equal threshold (the same threshold gives
different errors for different mechanisms).

Because sensing + wake-up cost the same for every mechanism, energy ratios sit close to 1.0
(best case so far ~0.89) while the *transmission* ratios are larger. With placeholder numbers
this is expected; the real picture needs your teammate's measurements.

## What was tested

- **55 tests, all passing.** The ones that matter most are the *error-bound*
  tests: for every step where the node stays silent, the receiver's value must
  be within the threshold of the truth, for all three mechanisms at several
  thresholds. A trend test confirms the Kalman filter really does go quiet on
  a steady ramp where deadband must keep sending.
- **A bug that the first version of this package shipped with, found on your
  real-data run and fixed.** The first Kalman and learned-model code compared
  each reading to the filter's own one-step prediction (which tracks the
  signal), while the evaluation rebuilt the signal by holding the last sent
  value. Those two assumptions don't match, so the predictive mechanisms
  looked efficient while the receiver drifted far from reality (e.g. Kalman
  MAE 0.66 vs deadband 0.039 at the same threshold, on your data). The old
  tests only counted triggers, so they passed. The error-bound tests above
  would have failed it (verified: the old logic violated the bound on 5,317 of
  6,000 silent steps).
- **An earlier divergence bug** in the learned model (raw-value SGD blowing up
  into the billions) is covered by a regression test.
- **The energy-source switch** (placeholder / measured / estimated) is tested,
  and fails with a clear error if a block still has null values.
- **Not verified by me:** results on your real Intel Lab data. Everything above
  was run on synthetic data shaped like it (smooth daily cycle + slow drift +
  small noise). Your run is the real check.

## What to look at when you run it on real data

1. `results/comparison.csv` — within each mechanism, trigger_rate should fall
   and reconstruction_mae should rise as the threshold loosens.
2. At the same threshold, no mechanism should have a MAE far above the
   threshold itself (MAE should stay <= threshold). If one does, treat it as a bug.
3. Whether Kalman / learned beat deadband on your data is an empirical result.
   On smooth signals they should send less for the same error; on jumpy or very
   noisy data deadband can win. Either outcome is reportable.
