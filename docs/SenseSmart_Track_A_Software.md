# SenseSmart — Software Track (Track A)
### For: Shriram, handling the software & ML side
### Companion to: `SenseSmart_Master_Project_Document.md` (the full project reference) and `SenseSmart_Track_B_Hardware.md` (your teammate's copy). This file is a focused, standalone copy of just your part.

**Read this if:** you're building the three trigger mechanisms in Python, running the comparison pipeline, and writing up results.

**Assumed starting knowledge:** Python and general programming — assumed known. Anything embedded/hardware-specific — assumed completely new, same as for your teammate, since none of it is actually part of your track.

---

## 0. What this project is, in two sentences

Sensor nodes waste battery by sensing/transmitting on a fixed timer instead of only when something's actually changed. This project compares three different ways of deciding "is this worth transmitting right now" — a simple rule, a classical formula (a Kalman filter), and a small on-device machine-learning model — and your specific job is to build and train all three in Python, build the comparison pipeline, and (once your teammate's measurements come back) produce the final results and the write-up.

---

## 1. Your status right now

- ✅ Nothing is blocking you. Start immediately, at Phase 0.
- Your teammate is handling the physical board and is waiting on hardware delivery — none of your phases depend on that.

---

## 2. Tools you'll need (all free)

| Tool | What it's for |
|---|---|
| **Python 3.10 or newer** | The language everything in your track is written in |
| **VS Code** | Code editor |
| **pip** + a **virtual environment** (`venv`) | Installing libraries, kept isolated from anything else on your machine |
| **`numpy`, `scipy`** | Math — needed for the Kalman filter |
| **`scikit-learn`** | The lightweight learned model (e.g. `SGDRegressor` for online learning) |
| **`pandas`** | Loading/handling the dataset |
| **`matplotlib`** | Plotting results |
| **`jupyter`** *(optional)* | Interactive notebooks, handy for exploring the dataset |
| **Git** + a **GitHub account** (free) | Version history + eventual portfolio link |

Your teammate's tools (PlatformIO, C/C++, the physical board) are not needed on your side at all — you never have to install or touch any of it.

---

## 3. Words you'll see, explained up front

| Term | Plain-English meaning |
|---|---|
| **Trigger mechanism** | The piece of logic that decides "should I sense/transmit right now, or wait?" |
| **Deadband / send-on-delta** | The simplest trigger: only report a value if it changed by more than a fixed amount since last time |
| **Kalman filter** | A classical (not AI/ML) formula that predicts the next value based on past values, and flags when reality diverges from the prediction |
| **On-device learned model** | A small machine-learning model, trained to predict when the next reading is actually needed |
| **E_total (total energy)** | ALL the energy used — sensing + "thinking" + transmitting + waking up + sleeping. Not just transmission count. |
| **Wake-up cost** | The energy burst a chip uses coming out of sleep — your teammate measures this; you just need to know it's part of the honest total |
| **Calibration pass** | Your teammate's short, one-time hardware measurement of "how much energy does operation X really cost" |
| **Placeholder constants** | Energy numbers borrowed from published papers, used temporarily so your pipeline can be built and tested before real measurements exist |

---

## 4. Your folder (your half of the project structure)

```
sensesmart/
├── README.md
├── requirements.txt          <- your Python library list
├── data/                     <- the public dataset(s), untouched
├── src/                      <- ALL YOUR CODE LIVES HERE
│   ├── mechanisms/
│   │   ├── deadband.py       <- Mechanism A
│   │   ├── kalman.py         <- Mechanism B
│   │   └── learned_model.py  <- Mechanism C
│   ├── harness.py            <- shared evaluation harness (takes an EnergyModel as input — never imports a specific energy source)
│   ├── energy_model.py       <- the pluggable energy backend (see Section 9) — this is what makes "INA219 or not" a one-line switch
│   └── energy_data.json      <- the actual numbers, in three labeled blocks: placeholder / measured / estimated
├── firmware/                 <- teammate's territory, not yours
├── notebooks/                <- optional exploration
├── results/                  <- plots, tables, csv
└── docs/                     <- this file and the master doc live here
```

---

## 5. Datasets

Pick 1–2 public, real-world time-series datasets with a slow-changing physical quantity — temperature/humidity is the safest choice. Candidates to start from:
- **Intel Berkeley Research Lab sensor dataset** (classic WSN dataset: temperature, humidity, light, voltage from 54 sensors).
- A **public weather-station dataset** (Kaggle/UCI).
- Any **UCI ML Repository** environmental time-series with natural, slow-changing dynamics.

**Decide this in Phase 0** — it blocks the Kalman filter's model and the ML model's feature design.

---

## 6. Evaluation metrics (what every experiment reports)

1. **Total energy (E_total)** per unit time — using placeholder numbers until your teammate's real ones arrive.
2. **Reconstruction/accuracy quality** — e.g. Mean Absolute Error between the true signal and what you'd reconstruct from only the triggered samples.
3. **Number of trigger events** — reported, never treated as "the win" by itself.
4. **Break-even point** — the headline result: where does each more-complex mechanism's own cost stop being worth it?

---

## 7. Your phases

### Phase 0 — Environment & Project Setup (target: 2–3 days)
- [ ] Install Python 3.10+, VS Code.
- [ ] Create the project folder (Section 4 above).
- [ ] Set up a virtual environment; `pip install` everything in Section 2.
- [ ] `git init`; first commit; (optional) push to GitHub.
- [ ] Finalize the exact dataset(s) (Section 5); download into `/data`.
- [ ] Write a 3–5 sentence problem statement in your own words.

**Done when:** structured repo exists, libraries installed, dataset sitting in `/data`.

**Next:** Phase 1.

---

### Phase 1 — Build Mechanisms A & B: Deadband + Kalman Filter (target: 3–5 days)
- [ ] Implement Mechanism A (deadband) in `src/mechanisms/deadband.py`.
- [ ] Implement Mechanism B (Kalman filter) in `src/mechanisms/kalman.py`, same input/output shape as A: it returns a `TriggerOutput` (which readings were sent + what the *receiver* believes the signal is at every step). Kalman and the learned model use **dual prediction**: node and receiver run the same predictor, both just *predict* between transmissions, and both *update* only when a reading is actually transmitted. The node transmits when the true reading is >= threshold away from the receiver's current prediction.
- [ ] Sanity-check, **on accuracy, not just trigger counts**: for every step where the node stayed silent, the receiver's value must be within the threshold of the truth. (A trigger-count-only check let a real bug through once: filters that tracked the signal internally looked "efficient" while the receiver drifted far from reality.)

**Done when:** both run on the dataset and produce sensible trigger decisions.

**Next:** Phase 2.

---

### Phase 2 — Build Mechanism C (Learned Model) + Write the Handoff Note (target: 4–6 days)
- [ ] Design a small model (e.g. `scikit-learn`'s `SGDRegressor`) predicting the next expected reading.
- [ ] Train/validate it on the dataset.
- [ ] Implement its **inference** step and its **update/learning** step as two separate functions — this separation matters later, don't merge them for convenience.
- [ ] Plug it into `src/mechanisms/learned_model.py`.
- [ ] **Write the Algorithm Handoff Note (Section 10 below) and send it to your teammate — and make sure they also have the operation-name list from Section 9, since that's the exact shape their Phase 5 numbers need to arrive in.** This is what unblocks their Phase 5 — don't let it slip to the last minute.

**Done when:** the learned model runs end-to-end, inference and update are clearly separate, and the handoff note has been sent.

**What NOT to do:** don't over-engineer this into a deep network — simple and finished beats fancy and late.

**Next:** Phase 3.

---

### Phase 3 — Dry-Run Comparative Study With Placeholder Numbers (target: 2–3 days)
- [ ] Build `src/energy_model.py` and `src/energy_data.json` **first** (Section 9 below) — this is the pluggable energy backend, and everything else in this phase depends on it existing before you wire the harness up.
- [ ] Build `src/harness.py`: runs any mechanism over the dataset, recording trigger events, reconstruction error, and total energy — by calling `energy_model.cost(operation_name)` for every operation, never a hardcoded number.
- [ ] Fill the `"placeholder"` block of `energy_data.json` with values from the literature survey — comment (in a sibling `energy_data_sources.md` or inline JSON comment-equivalent) which paper each number came from.
- [ ] Run all three mechanisms through the harness with `energy_source="placeholder"`; produce first draft plots/tables.
- [ ] Confirm zero errors and sensible-looking results (the free deadband mechanism should never show negative "thinking" cost).
- [ ] **Switch test:** manually fill a couple of dummy numbers into the `"estimated"` block and rerun with `energy_source="estimated"` — confirm nothing in `harness.py` or `mechanisms/` needed to change, only the source string. This proves the switch actually works before it matters.

**Done when:** a complete, bug-free pipeline run exists with full (placeholder-based) results, and the energy-source switch has been proven to work with dummy data.

**What NOT to do:** don't skip this to save time — a bug found here with fake numbers is cheap; the same bug found later with real numbers is expensive. Don't skip the switch test either — that's the thing protecting you from a last-minute rewrite in Phase 6.

---

**⏸ SYNC POINT — this is where you wait for your teammate's Phase 5 results (the real measured energy numbers). See "while you wait" below — don't sit idle.**

**While you wait, useful filler work (not required, but don't waste the gap):**
- Draft the paper's Introduction and Related Work sections (you already have the literature survey — this doesn't depend on final numbers).
- Polish the plotting/analysis code so swapping in real numbers later is a one-line change, not a rewrite.
- Write the Methodology section's description of your three mechanisms (also number-independent).

---

### Phase 6 — Final Comparative Study: Real Measured Numbers (target: 2–3 days)
- [ ] Drop your teammate's numbers straight into the `"measured"` block of `energy_data.json` (same operation-name keys as `"placeholder"` — they send it in that exact shape, see Section 9). **No code changes required** — this is the entire point of Phase 3's energy backend.
- [ ] Switch the run config to `energy_source="measured"` and re-run the full harness for all three mechanisms.
- [ ] **If your teammate's INA219 measurement didn't come through** (board/part trouble — see Track B's Phase 5 fallback) and only `"estimated"` (datasheet-derived) numbers exist: run with `energy_source="estimated"` instead — same one-line switch, no different pipeline. Say explicitly in the write-up which source was used; this is a legitimate, reportable outcome, not a failure.
- [ ] Compare: did the ranking change from the placeholder-based Phase 3 run? (Either answer is reportable.)
- [ ] Vary at least one condition (data volatility, or accuracy requirement) to find the actual break-even point.
- [ ] **Bonus (if time allows, not required):** run the comparison under *both* `"measured"` and `"estimated"` and show them side by side — a nice robustness note for the write-up ("the ranking holds whether we use measured or datasheet-estimated energy costs").

**Done when:** final, real (or clearly-labeled estimated) results exist, and you can state the break-even finding in one sentence.

---

### Phase 7 — Analysis & Writing (target: ~1 week)
- [ ] Write up: problem, method (including your teammate's calibration methodology — be specific, it's a selling point), results, honest limitations.
- [ ] State the result plainly, even if "the simple mechanism wins" — still a legitimate, publishable finding.
- [ ] Have someone else (or an AI reviewer) sanity-check every claim against the actual numbers.

**Done when:** a complete draft exists, every claim traceable to a specific number.

---

### Phase 8 — Submission Prep (optional, target: 2–4 days)
- [ ] Identify 1–2 realistic venues (a workshop, or a mid-tier journal — not a top-tier venue on this timeline).
- [ ] Format to the venue's requirements; submit.

---

## 9. The Pluggable Energy Backend — the "INA219 on/off" switch

**Why this exists:** your teammate's hardware measurement (INA219) might be late, flaky, or not happen at all in time. You should never be blocked on that, and you should never have to rewrite `harness.py` or any mechanism code depending on whether real measurements exist yet. The fix is one small abstraction, built once in Phase 3, used for the rest of the project.

**The design, in plain terms:** energy numbers never live inside the mechanism code or the harness. They live in one JSON file, grouped into three labeled blocks that all use the *exact same operation names*. Which block gets used is a single string you pass in — not a code change.

`src/energy_data.json`:
```json
{
  "placeholder": {
    "sleep_current_ua": 10.0,
    "wake_up_uj": 150.0,
    "sensor_read_uj": 2000.0,
    "tx_uj": 8000.0,
    "deadband_compute_uj": 0.0,
    "kalman_predict_uj": 5.0,
    "kalman_update_uj": 5.0,
    "ml_inference_uj": 20.0,
    "ml_update_uj": 40.0
  },
  "measured": { "...same keys, filled by your teammate from Phase 5...": null },
  "estimated": { "...same keys, filled by your teammate if INA219 isn't available...": null }
}
```

`src/energy_model.py`:
```python
import json
from dataclasses import dataclass

@dataclass
class EnergyModel:
    source: str
    values: dict

    def cost(self, operation: str) -> float:
        return self.values[operation]

def load_energy_model(source: str = "placeholder", path: str = "src/energy_data.json") -> EnergyModel:
    with open(path) as f:
        all_sources = json.load(f)
    if source not in all_sources:
        raise ValueError(f"Unknown energy source '{source}'. Options: {list(all_sources.keys())}")
    return EnergyModel(source=source, values=all_sources[source])
```

`harness.py` then takes an `EnergyModel` instance as a parameter — it calls `energy_model.cost("tx_uj")` etc., and never knows or cares whether those numbers are placeholder, measured, or estimated. Your run script picks the source with one argument:

```python
energy_model = load_energy_model(source="measured")   # or "placeholder" / "estimated"
results = run_harness(mechanism, dataset, energy_model)
```

**The operation-name list is the contract with your teammate.** The 9 keys above (`sleep_current_ua`, `wake_up_uj`, `sensor_read_uj`, `tx_uj`, `deadband_compute_uj`, `kalman_predict_uj`, `kalman_update_uj`, `ml_inference_uj`, `ml_update_uj`) are exactly what their Phase 5 (or Phase 5 fallback) must produce, in that shape — see Track B Section 6. If they send you a table instead of JSON, it takes you two minutes to paste it into this structure; it should never take you an hour of code changes.

**What this buys you:**
- If INA219 measurement succeeds → flip to `"measured"`, done.
- If INA219 fails/slips but your teammate still gets *some* numbers off the datasheet + multimeter → flip to `"estimated"`, done, and you say so explicitly in the write-up.
- If neither happens in time → you ship Phase 3's placeholder-based results, clearly labeled as such. Still a complete, honest pipeline — not a scramble.
- You can produce a "robustness" comparison (measured vs. estimated vs. placeholder) almost for free, which is a nice thing to show in the write-up.

---

## 10. The Algorithm Handoff Note — what to write for your teammate

Your teammate knows zero Python and doesn't need to — write this as plain math/pseudocode, not code. Keep it to 1–2 pages:

1. **The deadband rule** — the one comparison it makes (e.g. "if the new reading differs from the last sent one by more than X, send it").
2. **The Kalman filter** — constant-velocity model, state = [value, trend]; the predict formula (runs **every reading**), the update formula (runs **only when a reading is transmitted**), and the trigger rule: transmit when |reading - predicted value| >= threshold. State clearly that the receiver runs the identical filter (dual prediction), so only the node's cost is being measured. Include the **innovation gate**: in the update step the innovation (reading - prediction) is clipped to +-10 x threshold before use (one extra compare/clamp per update; protects against sensor glitches).
3. **The learned model** — what the inference step computes (predicts the next *change* from the window's recent differences; runs **every reading**) and what the update step does (one SGD step on a transmitted reading; runs **only on transmissions**). Include the **clipping**: window differences, the training target and the predicted change are all clamped to +-1.0 (a few compares per step; protects against sensor glitches). — also as plain pseudocode.
4. **Rough operation counts** — roughly how many additions/multiplications each step involves, so your teammate has a sense of scale before implementing it in C++.

Send this at the end of Phase 2 — it's the one thing your teammate's Phase 5 is waiting on.
