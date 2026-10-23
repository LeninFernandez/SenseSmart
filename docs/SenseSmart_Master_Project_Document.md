# SenseSmart — Master Project Document
### A Hardware-Calibrated Comparison of Adaptive-Sampling "Trigger" Mechanisms for Energy-Constrained Embedded Sensing

**Status:** Approved scope, requirements + roadmap finalized, not yet started
**Owner:** Shriram (BCSE305L Embedded Systems course project, VIT Chennai) — first embedded-systems project
**Team:** 2 people, working in parallel on separate tracks — Shriram (software/ML, Track A) and a teammate (hardware/firmware, Track B). Each has their own standalone document (`SenseSmart_Track_A_Software.md`, `SenseSmart_Track_B_Hardware.md`) covering just their phases in full detail — this master document remains the single overall source of truth, but day-to-day work should use the track file, not this one.
**Document purpose:** This is the single source of truth for this project. Anyone — a teammate, a future you, or an AI assistant picking this up cold — should be able to read this document and know exactly what the project is, what's already decided, what's still open, and what to do next. If something in a future conversation contradicts this document, this document wins unless it is explicitly and deliberately updated.

**How to use this document:** Read top to bottom once. Then use Section 11 (Phases & Checkpoints) as your working checklist — do not skip ahead to a later phase until the current phase's checkpoint is checked off. Section 14 (Guardrails) lists specific temptations that will derail this project — read it before every planning conversation. **This is a first embedded-systems project, so every section assumes zero prior embedded knowledge and explains things in plain language on purpose — this is not an oversight, it's deliberate.**

---

## 0. One-Paragraph Summary

Modern embedded sensor nodes waste energy by sensing and transmitting on a fixed schedule instead of only when something meaningful has changed. Several "smarter" mechanisms exist to fix this — a simple threshold rule, a classical Kalman filter, or a small machine-learning model — but no one has ever put all of them on the same hardware, measured their *own* energy cost honestly (not assumed it away), and reported where each one stops being worth its cost. This project builds that comparison. The output is a small, rigorous benchmark — not a new algorithm — and a short report describing it (this is a course deliverable, not a publication target — see Decision Log, Section 13).

---

## 1. The Problem, and Why This Is a Real (Not Invented) Gap

Sensor nodes (temperature loggers, environmental monitors, wearables) usually sample and transmit data on a fixed timer. This is wasteful — most of the time nothing has changed, so the node burns energy sensing and radioing data nobody needs.

The fix is a **"trigger mechanism"** — a rule that decides *when* it's actually worth sensing/transmitting. Three broad families exist:

| Family | Example | How it decides |
|---|---|---|
| **Rule-based** | Send-on-delta / deadband | "Has the value changed by more than X? If not, skip it." Free to compute. |
| **Classical estimator** | Kalman filter | Predicts the next value mathematically; triggers when the prediction is wrong enough. Some compute cost. |
| **Learned model** | A small on-device ML model (e.g. an online-trained regressor) | Learns the pattern from data and predicts when the next reading is needed. More compute cost, but adapts to patterns rule-based methods can't capture. |

**The gap, backed by literature (see Section 17 for full references):**

- A 2023 paper (Giordano et al., ACM ENSsys) did a rigorous, full hardware energy audit of a *rule-based* controller, down to the microjoule, including sleep and wake-up cost.
- A 2023–2025 body of work (several papers found) applies Kalman-filter-based triggering, but **every one we found is simulation-only** — none reports a real, hardware-measured total energy number.
- A March 2026 paper (Hinostroza et al., *Sensors*) finally did put a **learned model** on real hardware with a proper energy breakdown — a genuine, recent, well-executed paper. But even they explicitly **assumed the model's own compute cost was negligible and did not measure it** — a stated assumption, not a result.
- Nobody has done all three side-by-side, on the same hardware, under the same accounting method, with the model's own cost actually measured rather than assumed.

**That missing side-by-side comparison — with every mechanism's own cost honestly measured — is what this project produces.**

This is deliberately **not** a "we invented a new AI technique" project. It's an evidence-generating benchmark. That is a legitimate and publishable contribution type, and it is much more achievable than inventing new algorithms.

---

## 2. Project Goal / Research Question

**Primary research question:**
> Across rule-based, classical-estimator, and learned-model trigger mechanisms for adaptive sensing, where does each mechanism's own energy cost stop being worth the sensing/transmission energy it saves — measured honestly on real hardware, not assumed?

**Secondary questions:**
1. How much energy does each mechanism's own "thinking" (its compute — including, for the learned model, the cost of updating/learning, not just making a prediction) actually cost, in real measured microjoules?
2. How does that cost compare, in scale, to the sensing/transmission energy it's trying to save?
3. Is there a pattern (e.g. sensor type, data volatility) that predicts which mechanism wins?

---

## 3. Scope

### ✅ In scope (the MVP — this is what we are building)
- **Three trigger mechanisms**, implemented and compared:
  1. Send-on-delta / deadband (the free baseline)
  2. A classical Kalman filter
  3. One lightweight, on-device-style learned model (e.g. an online-updating regressor — the same general idea as the March 2026 paper, but with its own cost actually measured)
- **One short, one-time hardware calibration pass** — just enough to measure real per-operation energy costs (see Section 7). This is *not* a long field deployment.
- **A software-based comparative study** — using the measured real-world costs as fixed constants, run all three mechanisms over 1–2 public datasets and compare energy vs. accuracy trade-offs.
- A short paper/report describing the method and results, honestly, including a null or "it depends" result if that's what the data shows.
- **Software-first execution order** (see Section 11): all three mechanisms and the full comparison pipeline are built and dry-run in software *before* any hardware work happens, so hardware shipping time never blocks progress.

### ❌ Out of scope (explicitly — do not add these without a deliberate scope-change decision)
- **Reinforcement learning** as a fourth trigger mechanism. It's a legitimate future extension, mentioned in the paper as future work, but not built now — RL tuning alone can consume the entire project timeline. (See Section 18 for the tiered decision framework on if/when to add this.)
- **A long real-world field deployment** (weeks of continuous operation in the wild). We only need the hardware for calibration, not for the whole study.
- **More than 1–2 datasets.** Depth of comparison matters more than breadth right now.
- **Designing new hardware** (custom PCB, novel sensor). Use whatever common MCU dev board is already available.
- **Chasing a top-tier ("Q1") journal or top-tier conference as a target.** Aim for a workshop or a solid mid-tier journal; see Section 17 note on publication realism.
- **Perfecting the ML model.** A simple, working learned model that's honestly measured beats a fancy one that eats the whole timeline.

---

## 4. Key Terms in Plain English

### General project terms
| Term | What it actually means |
|---|---|
| **Trigger mechanism** | The piece of logic that decides "should I sense/transmit right now, or wait?" |
| **Sensing** | Taking a measurement (e.g. reading a temperature sensor). |
| **Total energy (E_total)** | ALL the energy used — sensing + the trigger's own thinking + radio transmission + waking up + going back to sleep. Not just "how many times we transmitted." Counting only transmissions and calling it "energy saved" is the single most common mistake in this field — don't make it. |
| **Wake-up cost** | The burst of energy a chip uses coming out of sleep mode before it can do anything useful. Easy to forget, often bigger than expected. |
| **Calibration pass** | A short, one-time hardware experiment purely to measure "how much energy does operation X actually cost on real hardware" — not the main experiment itself. |
| **Deadband / send-on-delta** | The simplest trigger: only report a value if it changed by more than a fixed amount since last time. |
| **Kalman filter** | A classical (not AI/ML) mathematical technique that predicts the next value of something based on past values, and can flag when reality diverges from the prediction. |
| **On-device learned model** | A small machine-learning model that runs directly on the microcontroller (not in the cloud), possibly updating itself as new data arrives. |

### Embedded-systems terms (new to a first embedded project — read this before Phase 4)
| Term | What it actually means |
|---|---|
| **MCU (microcontroller)** | The tiny, low-power computer chip on a sensor node dev board. Much weaker than a laptop CPU on purpose — it's built for sipping power, not raw speed. |
| **Dev board / devkit** | A ready-made small circuit board with the MCU already wired up to USB, power regulation, etc. — so you don't have to build a chip's supporting circuitry yourself. |
| **Firmware** | The program that runs directly on the MCU (as opposed to a program running on your laptop). |
| **Flashing** | The (one-time, or repeated-when-updating) act of copying your program onto the MCU's memory so it can run it. |
| **IDE** | "Integrated Development Environment" — a program on your laptop for writing and uploading code to the board. This project uses VS Code with the PlatformIO extension (Section 6.4), not a separate dedicated app. |
| **PlatformIO** | A professional embedded-development toolchain that runs as an extension inside VS Code — lets you write, build, and upload C/C++ firmware without leaving the same editor already used for the Python side. |
| **Framework (Arduino framework)** | A set of ready-made C/C++ libraries (WiFi, sensor drivers, sleep functions, etc.) sitting on top of the raw chip, so firmware doesn't have to be written from the lowest level. We use the Arduino framework for the ESP32, accessed through PlatformIO — real C/C++, not the beginner Arduino IDE. |
| **Breadboard** | A reusable plastic board full of holes that let you connect electronic components together with wires, with no soldering. Standard for prototyping. |
| **GPIO pin** | "General Purpose Input/Output" — one of the small metal pins on the board that can read a sensor's signal or send power/signals out. |
| **I2C** | A common, simple way for two chips (e.g. the MCU and a sensor) to talk to each other over just two wires. You'll see "I2C" mentioned in sensor wiring guides. |
| **Datasheet** | The official reference document for an electronic part, listing exactly how to wire it and what it's capable of. Sounds intimidating, but you'll only need small specific bits of it (like the pin diagram). |

---

## 5. System Architecture

### 5.1 Conceptual pipeline (applies to all three mechanisms)

```
 Physical thing being measured (e.g. temperature)
        │
        ▼
   [ Sensor ] ── reads a value
        │
        ▼
 [ Trigger Mechanism ] ── decides: was this reading worth acting on?
        │              (this is the ONLY part that changes between
        │               the 3 versions we're comparing)
        ▼
   ┌─────────────┐
   │  Yes → Transmit / act, then sleep
   │  No  → Just go back to sleep
   └─────────────┘
```

All three versions of the project share everything *except* the box labeled "Trigger Mechanism." That's the whole point — it's a controlled comparison.

### 5.2 The three variants being compared

| Variant | What's inside the "Trigger Mechanism" box |
|---|---|
| **A — Baseline** | Deadband rule: `if |new_value - last_sent_value| > threshold: send` |
| **B — Classical** | Kalman filter predicts next value; triggers if prediction error exceeds a bound |
| **C — Learned** | A small on-device model (e.g. online-updating regressor) predicts when the next check-in is needed, and/or flags an unexpected reading |

### 5.3 The three-stage project structure (software → hardware → software)

To avoid hardware shipping time ever blocking progress, the project runs in three time-ordered stages, not two:

```
 STAGE 1: SOFTWARE                    STAGE 2: HARDWARE                    STAGE 3: SOFTWARE
 (Phases 1–3)                         (Phases 4–5)                         (Phases 6–7)
 ───────────────────────              ───────────────────────              ───────────────────────
 Build all 3 mechanisms   ──────▶     First contact with the   ──────▶    Swap the placeholder
 in plain Python                      ESP32 board; then                   numbers for the real
                                       measure real per-                   measured ones; get
 Run the full comparison               operation energy costs              final results and write
 pipeline once using                                                       up
 placeholder energy
 numbers from the
 literature (Section 17)

 ── No hardware needed ──             ── Hardware ordered in              ── No hardware needed ──
                                          Phase 0 should have
                                          arrived by now ──
```

**This is the direct answer to "can we do software first":** yes — Stage 1 (all three mechanisms, plus a full dry run of the comparison using placeholder numbers) needs zero hardware. Hardware is ordered in Phase 0 so it's not a bottleneck, but you don't have to touch it, wait for it, or think about it again until Stage 2.

---

## 6. Software Requirements

Everything below is free. No paid tools required.

### 6.1 Core environment (for Stages 1 and 3 — the software side)
| Tool | What it's for | Why this one |
|---|---|---|
| **Python 3.10 or newer** | The programming language the software side (mechanisms, harness, analysis) is written in — NOT the firmware, which is C/C++ (Section 6.4) | Already what you know; free; huge library ecosystem |
| **VS Code** | A code editor — where you'll write and run the Python files | Free, beginner-friendly, works the same on any OS |
| **pip** | Python's package installer — comes bundled with Python automatically | Used to install every library below with one command each |
| **A virtual environment** (Python's built-in `venv`) | A clean, isolated Python setup just for this project | Stops this project's libraries from clashing with anything else on your machine — good habit for every project going forward |

### 6.2 Python libraries (installed via `pip install`)
| Library | What it's for in this project |
|---|---|
| `numpy` | Numerical computing — needed for the Kalman filter's matrix math |
| `scipy` | Extra math/statistics helpers |
| `scikit-learn` | The lightweight learned model (e.g. `SGDRegressor` for online learning) |
| `pandas` | Loading and handling the dataset — think "spreadsheet in code" |
| `matplotlib` | Plotting the energy-vs-accuracy results |
| `jupyter` *(optional)* | Interactive notebooks — handy for exploring the dataset before writing final scripts |

### 6.3 Version control
| Tool | What it's for |
|---|---|
| **Git** | Tracks every change to your code over time — like an unlimited "save point" system, so you can always undo a mistake or see what changed and when |
| **GitHub account** (free) | An online backup of the project, and eventually something you can point recruiters to |

### 6.4 Embedded/firmware tools (needed later, in Stage 2 — listed now so nothing is a surprise)
| Tool | What it's for | Why this choice |
|---|---|---|
| **PlatformIO** (VS Code extension) | Lets you write, build, and upload C/C++ firmware to the ESP32 — a professional embedded toolchain, not the beginner Arduino IDE | Keeps everything in one editor (VS Code, already installed in Section 6.1) — this is the toolchain real embedded/firmware teams actually use |
| **Arduino-ESP32 framework** (used through PlatformIO) | Ready-made C/C++ libraries for WiFi, sensors, sleep modes, etc., so firmware isn't written from the absolute lowest level | Balances real C/C++ with a manageable learning curve; full ESP-IDF (Espressif's lower-level framework) is an optional later stretch, not required for the MVP |
| **C/C++** | The language the firmware itself is written in | See the reasoning below — this replaces the MicroPython choice from an earlier draft of this document |

**Why C/C++ instead of MicroPython (reversing the earlier draft of this document):** three reasons converged. (1) **Resume value** — Embedded C/C++ is the industry-standard language for firmware/embedded/IoT roles; MicroPython is a prototyping convenience, not something employers screen for. (2) **Fits existing knowledge and coursework** — the college syllabus already covers Embedded C, and C/C++ is already known, so this isn't a new language to learn, it directly reinforces what's already being taught. (3) **Measurement rigor for the paper specifically** — MicroPython is *interpreted*, adding real per-operation overhead on top of whatever the Kalman filter or learned model actually costs. Since this project's whole point is measuring tiny (microjoule-scale) per-operation costs honestly, that interpreter overhead could distort exactly the numbers the paper depends on. Compiled C/C++ avoids this confound — the measured cost is much more clearly the algorithm's own cost, not the language runtime's.

---

## 7. Hardware Requirements (Shopping List)

You do not need anything exotic, expensive, or requiring soldering. Total cost: roughly ₹1,200–2,000 (~$15–25). **Order all of this in Phase 0** — shipping is the real bottleneck, not the work itself, so don't wait until you "need" it.

| # | Item | What it's for (plain language) | Approx. cost (India) | Notes |
|---|---|---|---|---|
| 1 | **ESP32 DevKit board** (e.g. "ESP32-WROOM-32 DevKit V1") | The "brain" — a tiny low-power computer that runs our trigger logic and later gets its energy use measured | ₹350–550 | Pick one with a USB port built in — easiest to program |
| 2 | **Environmental sensor** — DHT22 *or* BME280 | The physical thing being measured, matching whichever dataset domain we pick (Section 9) | ₹150–400 | BME280 is more accurate and uses I2C (simpler wiring); DHT22 is cheaper and also fine |
| 3 | **INA219 current-sensing breakout board** | Measures how much electrical current — and therefore energy — the board is drawing at any moment | ₹150–250 | This is the key measuring instrument for Phase 5 |
| 4 | **Basic multimeter with a µA (microamp) range** | Needed specifically for measuring the tiny current draw during "sleep mode" — the INA219 alone usually isn't precise enough at that scale | ₹500–1,500 (skip if you already own one with this range) | Check any multimeter you already have for a µA range before buying a new one |
| 5 | **Breadboard + jumper wires** (basic kit) | Connects everything above without soldering — like electronic building blocks | ₹150–300 | Any generic "breadboard starter kit" works |
| 6 | **USB cable** matching your board (usually Micro-USB or USB-C) | Powers and programs the ESP32 from your laptop | Often included with the board — check before buying a separate one | |

**Where to buy:** Robu.in, Robokits, ElectronicsComp, or Amazon.in all commonly stock every part above.

**Optional, not required for the MVP:** a small battery pack, only useful for a "realistic battery-powered demo" flourish at the very end — skip unless there's spare time.

---

## 8. Datasets

Pick 1–2 public, real-world time-series datasets that a slow-changing physical quantity would plausibly come from — temperature, humidity, or similar environmental data is the safest choice (slow dynamics, easy to reason about "what counts as an event," widely available). Avoid a dataset that requires inventing your own definition of "ground truth event" — use one where change points are natural (e.g. real diurnal temperature cycles).

**A few well-known, easy-to-download candidates to start from** (finalize the exact one in Phase 0 — this list is to remove ambiguity, not to force a premature choice):
- The **Intel Berkeley Research Lab sensor dataset** (classic wireless-sensor-network dataset: temperature, humidity, light, and voltage from 54 sensors).
- A **public weather-station dataset** (widely available on Kaggle/UCI) — hourly or sub-hourly temperature/humidity readings.
- Any **UCI Machine Learning Repository** environmental time-series dataset with natural, slow-changing dynamics.

**Decision to make in Phase 0:** name the exact dataset(s) and download them into `/data`. Don't leave this open past Phase 0 — it blocks the Kalman filter's process model and the ML model's feature design in Phase 1–2.

---

## 9. Evaluation Metrics

For each of the 3 mechanisms, report:

1. **Total energy (E_total)** per unit time, using the measured constants from Phase 5 (placeholder constants from the literature in the Phase 3 dry run).
2. **Reconstruction/accuracy quality** — e.g. Mean Absolute Error between the true signal and what you'd reconstruct from only the samples/transmissions the mechanism chose to send.
3. **Number of trigger events** (sensing/transmission count) — reported, but never treated as "the win" by itself. Energy is the win metric; trigger count is a supporting detail.
4. **Break-even framing** — the actual headline result: at what point (what data volatility, what accuracy requirement) does each more-complex mechanism's own cost stop being worth it compared to the simpler one below it?

---

## 10. Project Folder Structure

A clean, predictable folder layout — so any file's purpose is obvious at a glance, and the project looks professional if you put it on GitHub.

```
sensesmart/
├── README.md                 <- one-paragraph project summary + how to run things
├── requirements.txt          <- exact list of Python libraries, for one-command install
├── data/                     <- the raw public dataset(s), untouched
├── src/                      <- all Python source code (the software side)
│   ├── mechanisms/
│   │   ├── deadband.py       <- Mechanism A
│   │   ├── kalman.py         <- Mechanism B
│   │   └── learned_model.py  <- Mechanism C
│   ├── harness.py            <- shared evaluation harness — runs any mechanism over a dataset, calls into energy_model.py for every energy number
│   ├── energy_model.py       <- the pluggable energy backend — one-line switch between placeholder/measured/estimated (Track A Section 9)
│   └── energy_data.json      <- the actual numbers, in three labeled blocks sharing the same 9 operation-name keys
├── firmware/                 <- C/C++ (PlatformIO) code that eventually runs ON the ESP32
│   └── platformio.ini        <- PlatformIO's project config (board type, framework) — created in Phase 4
├── notebooks/                <- exploratory Jupyter notebooks (optional, for messing around)
├── results/                  <- output plots, tables, csv results
└── docs/                     <- this master document and the literature survey live here
```

Git tracks this entire folder (except `data/` and `results/`, which are usually excluded from version control since they can be regenerated or re-downloaded — a `.gitignore` file handles this, and it's fine to set up when you get there, not something to worry about now).

---

## 11. End-to-End Workflow: Phases & Checkpoints

**Rule for using this section:** each phase has a checkpoint. Do not start the next phase until the current phase's checkpoint items are all checked. If you (or an AI helping you) are ever unsure "what do I do next," the answer is: find the first unchecked box below.

**Software-first ordering, on purpose:** Phases 1–3 are pure software and need zero hardware. Phases 4–5 are the only ones that touch physical parts. Phase 0 places the hardware order early specifically so it arrives *during* Phases 1–3, instead of making you wait for it before you can start anything.

---

### Phase 0 — Environment & Project Setup (target: 2–3 days)
**Goal:** a working, structured, empty project ready to fill in — and the hardware order placed so it's not a bottleneck later.

Tasks:
- [ ] Install Python 3.10+ if not already installed.
- [ ] Install VS Code.
- [ ] Create the project folder using the structure in Section 10.
- [ ] Set up a Python virtual environment inside the project folder.
- [ ] Create `requirements.txt` and `pip install` everything in Section 6.2.
- [ ] Initialize a git repository; make a first commit with just the empty folder structure.
- [ ] (Optional) Create a matching GitHub repository and push.
- [ ] Finalize the exact dataset(s) from Section 8; download into `/data`; write the dataset name/source into `README.md`.
- [ ] **Order every item in Section 7's hardware list now** — even though it won't be touched until Phase 4.
- [ ] Write a 3–5 sentence problem statement in your own words (becomes the paper's intro paragraph later).

**Checkpoint / definition of done:** empty-but-structured repo exists, all libraries installed and importable, dataset decided and sitting in `/data`, hardware order placed.

**What NOT to do:** don't wait to place the hardware order "until it's needed" — that's the single easiest way to accidentally block Phase 4 later.

**Next step after this phase:** Phase 1.

---

### Phase 1 — Build Trigger Mechanisms A & B: Deadband + Kalman Filter (software only, target: 3–5 days)
**Goal:** two working, comparable implementations of the two simplest mechanisms.

Tasks:
- [ ] Implement Mechanism A (deadband) as a small, standalone Python function in `src/mechanisms/deadband.py`.
- [ ] Implement Mechanism B (Kalman filter) in `src/mechanisms/kalman.py`, with the same input/output shape as A — each mechanism returns which readings were sent *and* what the receiver believes the signal is. Kalman (and later the learned model) use **dual prediction**: node and receiver run the same predictor, both predict between transmissions, both update only on a transmitted reading (Jain et al. 2004, Section 17).
- [ ] Write sanity tests that check **accuracy, not just trigger counts**: whenever the node stays silent, the receiver's value must be within the threshold of the truth. (Count-only tests once let through a design where the filter looked efficient while the receiver drifted far off — see the Decision Log.)

**Checkpoint / definition of done:** both mechanisms run on the chosen dataset and produce sensible-looking trigger decisions (not yet compared to each other formally — that's Phase 3).

**Next step after this phase:** Phase 2.

---

### Phase 2 — Build Trigger Mechanism C: the Lightweight Learned Model (software only, target: 4–6 days)
**Goal:** one working learned-model implementation, matching the same interface as A and B.

Tasks:
- [ ] Design a small model (e.g. `scikit-learn`'s `SGDRegressor` or similar) that predicts the next expected reading, following the same general idea as the March 2026 paper referenced in Section 1.
- [ ] Train/validate it on the chosen dataset.
- [ ] Implement its on-device-*style* update/learning logic separately from its inference logic — even in this software-only stage, keep these as two distinct functions/steps. (This separation matters later — see the guardrail in Section 14 about not folding update cost into inference cost.)
- [ ] Plug it into `src/mechanisms/learned_model.py` with the same input/output shape as A and B.

**Checkpoint / definition of done:** the learned model runs end-to-end on the dataset, with inference and update as two clearly separate, callable steps.

**What NOT to do:** don't over-engineer this into a deep network. A simple, working model that's finished on time beats a fancy one that isn't.

**Next step after this phase:** Phase 3.

---

### Phase 3 — Dry-Run Comparative Study Using Placeholder Energy Numbers (software only, target: 2–3 days)
**Goal:** get the *entire* analysis pipeline working end-to-end — using literature-derived placeholder numbers — before any hardware is even in hand. This catches bugs early and means Phase 6 later is just "swap the numbers," not "build the pipeline under time pressure."

**Design decision carried through Track A/B (see `SenseSmart_Track_A_Software.md` Section 9 and `SenseSmart_Track_B_Hardware.md` Phase 5 for full detail):** energy numbers are never hardcoded into the mechanisms or the harness. They live in one `energy_data.json` file with three labeled blocks — `"placeholder"`, `"measured"`, `"estimated"` — all sharing the same 9 operation-name keys. Which block is used is a single config string (`energy_source=...`), never a code change. This is what makes "did the INA219 measurement come through or not" a non-blocking, one-line switch instead of a rewrite under deadline pressure.

Tasks:
- [ ] Build `src/energy_model.py` + `src/energy_data.json` (the pluggable energy backend — see Track A Section 9) before the harness, since the harness depends on it.
- [ ] Build `src/harness.py`: one shared function that can run any of the three mechanisms over the dataset and record trigger events, reconstruction error, and total energy — by calling into the energy model, never a hardcoded constant.
- [ ] Fill the `"placeholder"` block of `energy_data.json` with values pulled from the literature survey (Section 17) — clearly comment which paper each number came from.
- [ ] Run all three mechanisms through the harness with `energy_source="placeholder"`; produce the first draft plots/tables (energy vs. accuracy, from Section 9).
- [ ] Confirm the whole pipeline runs with zero errors and produces results that at least *look* sensible (e.g. the free deadband mechanism should never show negative energy savings from "thinking").
- [ ] Prove the switch works: fill dummy numbers into `"estimated"`, rerun with that source, confirm no code outside the JSON file needed to change.

**Checkpoint / definition of done:** a complete, bug-free pipeline run exists, producing a full (placeholder-based) results table/plot for all three mechanisms.

**What NOT to do:** don't skip this "to save time" — finding a bug here, with fake numbers, is cheap. Finding the same bug in Phase 6, with real hardware numbers on the line, is expensive.

**Next step after this phase:** Phase 4. *(By now, the hardware ordered in Phase 0 should have arrived.)*

---

### Phase 4 — Hardware Bring-Up: First Contact With the Board (target: 2–4 days)
**Goal:** get the ESP32 talking to your computer and reading a real sensor. This is your first time touching embedded hardware in this project — go slow, and don't worry about energy measurement yet, that's Phase 5.

Tasks:
- [ ] Install the PlatformIO extension inside VS Code.
- [ ] Create a new PlatformIO project targeting the ESP32 board, using the Arduino-ESP32 framework.
- [ ] Connect the ESP32 via USB; confirm PlatformIO can detect and talk to it (build and upload a blank sketch as a first test).
- [ ] Run a simple test: blink the board's onboard LED on and off, in C++. This proves the whole toolchain (board + PlatformIO + Arduino framework) works, before anything more complex.
- [ ] Wire up the sensor (DHT22 or BME280) on the breadboard, following its datasheet's pin diagram.
- [ ] Write a few lines of C++, using the sensor's library, to read one real sensor value and print it over serial.

**Checkpoint / definition of done:** you can read a live sensor value from the ESP32 and see it printed on your laptop, reliably, more than once.

**What NOT to do:** don't try to wire in the INA219 or start measuring energy yet — that's a separate, later step (Phase 5). Get sensing working first, in isolation.

**Next step after this phase:** Phase 5.

---

### Phase 5 — Hardware Calibration: Measuring Real Energy Costs (target: 3–7 days)
**Goal:** get real, measured, microjoule-level numbers for every operation each mechanism needs. This is the *only* phase whose entire purpose is measurement.

Tasks:
- [ ] Wire in the INA219 current-sensing board.
- [ ] Measure sleep-mode current using the multimeter's µA range; sanity-check it against the ESP32's datasheet (if your number is wildly higher — sometimes 100–1000× — you're likely measuring the devkit's onboard USB/regulator circuitry, not the chip itself; this is a five-minute check, not a research problem).
- [ ] Measure active current for: one sensor reading, one wireless transmission, one wake-up event.
- [ ] Port the Kalman filter's predict/update step from `src/mechanisms/kalman.py` into C++ (`firmware/`), run it on the ESP32, and measure its per-cycle energy cost.
- [ ] Port the learned model's inference step and its update/learning step *separately* into C++, and measure each one's energy cost separately — do not skip measuring the update step on its own, even though it feels similar to inference. This separation is the project's single most specific, defensible contribution (see Section 1).
- [ ] Fill the `"measured"` block of `energy_data.json` with the 9 named values (`sleep_current_ua`, `wake_up_uj`, `sensor_read_uj`, `tx_uj`, `deadband_compute_uj`, `kalman_predict_uj`, `kalman_update_uj`, `ml_inference_uj`, `ml_update_uj` — see Track A Section 9 / Track B Phase 5) — this requires zero changes to `harness.py` or any mechanism code.

**Checkpoint / definition of done:** real, measured numbers exist for all 9 keys above — zero placeholder or guessed values remain in the `"measured"` block.

**Fallback if the INA219 measurement doesn't come through in time** (see Track B's "Fallback" subsection under Phase 5): fill the `"estimated"` block instead, using ESP32 datasheet current figures × on-device-timed durations. Same 9 keys, same file, zero pipeline changes — only the source label (`"estimated"` vs. `"measured"`) differs, and it's stated plainly wherever results are reported.

**What NOT to do:** don't chase lab-grade measurement precision. "Good enough, honestly reported" beats "perfect and three weeks late." Cap this phase at one week.

**Next step after this phase:** Phase 6.

---

### Phase 6 — Final Comparative Study: Real Measured Numbers (target: 2–3 days)
**Goal:** re-run the exact Phase 3 pipeline, now with real numbers instead of placeholders — this is fast, since the pipeline itself is already built and debugged.

Tasks:
- [ ] Switch the run config to `energy_source="measured"` (or `"estimated"` if that's what Phase 5 actually produced — see its fallback note) — no code changes beyond this one string, since `"measured"`/`"estimated"` should already be filled in `energy_data.json` at the end of Phase 5.
- [ ] Re-run the full harness over the dataset for all three mechanisms.
- [ ] Compare: did the ranking between mechanisms change from the placeholder-based Phase 3 run? (Either answer is an interesting, reportable finding.)
- [ ] Vary at least one condition (data volatility, or the accuracy requirement) to find the actual break-even point between mechanisms — this produces the headline result.

**Checkpoint / definition of done:** final, real results table/plots exist, and you can state the break-even finding in one sentence.

**Next step after this phase:** Phase 7.

---

### Phase 7 — Analysis & Writing (target: ~1 week)
**Goal:** turn results into a short, honest report/paper.

Tasks:
- [ ] Write up: problem, method (including the Phase 5 calibration methodology — be specific, this is a selling point), results, and an honest discussion of limitations (small dataset count, one hardware platform, etc.).
- [ ] State the result plainly, even if it's "the simple mechanism wins under most realistic conditions" — that's still a legitimate, useful, publishable finding (Section 1).
- [ ] Have someone else (or an AI reviewer) sanity-check every claim against the actual numbers before finalizing.

**Checkpoint / definition of done:** a complete draft report/paper exists, with every claim traceable to a specific number from Phase 3, 5, or 6.

**Next step after this phase:** Phase 8 (optional) or submit as the course deliverable.

---

### Phase 8 — Submission Prep (optional, target: 2–4 days)
**Goal:** if pursuing publication beyond the course requirement.

Tasks:
- [ ] Identify 1–2 realistic target venues (a relevant workshop, or a mid-tier journal — see Section 17's publication-realism note; do not target a top-tier venue on this timeline).
- [ ] Format to the venue's requirements.
- [ ] Submit.

**Checkpoint / definition of done:** submitted, or consciously decided not to pursue publication and closing the project as a completed course deliverable.

---

## 12. Timeline Overview

| Phase | Focus | Target duration | Touches hardware? |
|---|---|---|---|
| 0 | Environment setup + place hardware order | 2–3 days | No (ordering only) |
| 1 | Build Mechanisms A & B | 3–5 days | No |
| 2 | Build Mechanism C (learned model) | 4–6 days | No |
| 3 | Dry-run comparison (placeholder numbers) | 2–3 days | No |
| 4 | Hardware bring-up (first contact) | 2–4 days | **Yes** |
| 5 | Hardware calibration (real measurements) | 3–7 days | **Yes** |
| 6 | Final comparison (real numbers) | 2–3 days | No |
| 7 | Analysis & writing | ~1 week | No |
| 8 (optional) | Submission prep | 2–4 days | No |
| **Total (MVP, Phases 0–7)** | | **~3–4.5 weeks** | |

**The key efficiency point:** Phases 1–3 (roughly 9–14 days of software work) can proceed while the hardware ordered in Phase 0 is shipping. In most cases the hardware will already have arrived by the time Phase 4 starts — the hardware phases are no longer sitting on the critical path waiting for a delivery.

---

## 13. Decision Log (why we're here — don't re-litigate this without a reason)

1. **Rejected:** pure Kalman-filter-only project (the original SenseSmart framing). Reason: scored low on AI/ML depth (classical estimation, not ML) and high on hardware dependency (the whole contribution was a hardware energy audit) — the opposite of the stated project goals.
2. **Rejected:** "just swap the Kalman filter for an ML model and call it done." Reason: a March 2026 published paper (Hinostroza et al., *Sensors*) already did essentially this, on real hardware, with a full energy breakdown — pursuing that exact framing now means competing with a very recent paper doing the same thing.
3. **Chosen:** the cross-mechanism comparison (deadband vs. classical vs. learned), with each mechanism's own compute/learning cost actually measured rather than assumed — because no existing paper does this, it requires no invented algorithm, and it can be restructured into a mostly-software project (Section 5.3).
4. **Deferred, not rejected:** reinforcement learning as a fourth mechanism — genuine future work, explicitly excluded from the MVP timeline. See Section 18 for the tiered options to revisit this after the MVP, and what each tier costs in time.
5. **Chosen:** software-first phase ordering (Section 11) over the originally-drafted hardware-early ordering. Reason: hardware acquisition (ordering + shipping) is a fixed time cost that shouldn't block software progress — all three mechanisms and a full dry-run of the comparison pipeline can be built and debugged with zero hardware in hand, using placeholder energy numbers from the literature survey (Section 17).
6. **Reversed:** firmware language changed from MicroPython (the original draft's choice) to C/C++ via PlatformIO + the Arduino-ESP32 framework. Reason: the user already knows C/C++ and the college syllabus covers Embedded C, so it isn't a new language; C/C++ is the industry-standard, resume-recognized language for embedded/firmware roles (MicroPython is a prototyping convenience, not a hiring signal); and, specific to this paper's rigor, compiled C/C++ avoids the interpreter overhead that MicroPython would add on top of the microjoule-scale per-operation costs the project is trying to measure honestly.
7. **Chosen:** split execution into two parallel, standalone tracks (Track A: software/ML, Track B: hardware/firmware) across the 2-person team, instead of one person running all 9 phases sequentially. Reason: hardware was ordered but is still shipping, so Track A (Phases 0–3) runs independently on one teammate's machine while the other waits for delivery; the two tracks meet at explicit sync points (end of Phase 2 → Algorithm Handoff Note; end of Phase 5 → measured energy numbers) rather than needing constant coordination.
8. **Fixed (Oct 2026, after first real-data run):** the first Kalman / learned-model implementation compared each reading to the filter's own one-step prediction while the evaluation rebuilt the signal by holding the last sent value. The trigger rule and the receiver model didn't match, so those mechanisms looked cheap but the receiver drifted far from reality (MAE up to ~2.8 vs deadband's 0.65). Replaced with dual prediction; update cost is now charged only on transmitted readings. Lesson recorded: always test accuracy per transmission, never trigger counts alone.
9. **Hardened (Oct 2026, second real-data review):** simulation showed sensor-glitch readings (present in the raw Intel data) break the predictive mechanisms: unprotected, the learned model diverged and transmitted ~90% of readings, and the Kalman filter spent more transmissions than deadband. Added input clipping (learned model) and an innovation gate (Kalman), made the receiver show the exact transmitted reading on transmit steps for all mechanisms (Kalman was being charged for showing its filtered estimate), and added an optional `--despike` data-cleaning step plus a matched-accuracy comparison. Real-data conclusions about Kalman should be drawn only after running with and without `--despike`.

---

## 14. Guardrails — Read This Before Any Planning Conversation

These are specific, likely temptations. If a future conversation (with an AI or a teammate) suggests one of these, treat it as a deliberate scope-change decision, not a default — update this document if you do it.

- **Don't add a 4th mechanism (especially RL) "since we're already comparing three."** That's how a 3–4 week project becomes a 3-month one.
- **Don't chase a long field deployment "to make it more realistic."** The hardware step is a short calibration pass, not the main experiment. If you find yourself running the sensor node for more than a few days, you've drifted back into the hardware-heavy version of this project we deliberately moved away from.
- **Don't perfect the ML model.** A working, simple, honestly-measured model beats a fancy one that isn't finished by Phase 2's checkpoint.
- **Don't skip measuring the learned model's on-device *update/learning* cost separately from its inference cost.** This is the single most specific, defensible new contribution of the whole project — it's easy to accidentally fold it into "inference cost" and lose the point.
- **Don't target a top-tier ("Q1") venue as the plan.** Aim realistically (Section 17). Overshooting the target doesn't make the work better; it just creates a mismatch between effort and expectation.
- **Don't let this become a hardware-instrumentation project.** If Phase 5 is taking longer than a week, stop optimizing measurement precision and move to Phase 6 with the numbers you have, clearly caveated.
- **Don't wait to order hardware until Phase 4 "when it's needed."** Order it in Phase 0. Shipping time is the actual bottleneck, and it runs in the background for free while you do Phases 1–3.
- **Don't skip the Phase 3 dry run.** Debugging the pipeline with fake numbers is cheap; debugging it in Phase 6 with real numbers and less schedule slack is expensive.

---

## 15. Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Hardware shipping takes longer than expected | Order in Phase 0, not later. Phases 1–3 (9–14 days of pure software work) give the shipment plenty of time to arrive in the background. If it's still delayed, use the literature-derived placeholder constants from Phase 3 as provisional final numbers, clearly caveated. |
| Hardware calibration (Phase 5) takes longer than expected (measurement noise, board quirks) | Cap it at 1 week; use "good enough, clearly caveated" numbers rather than chasing precision. |
| Learned model doesn't train well on chosen dataset | Keep the model simple (a small regressor, not a deep network) — simplicity was already the right choice for this scope, not a fallback. |
| Results show "the simple mechanism just wins, always" | This is a valid, reportable, useful result (explicitly a legitimate contribution type — see Section 1). Do not chase a "more interesting" result by tuning until one mechanism artificially wins. |
| Time pressure from other coursework/commitments | The MVP scope in this document is already trimmed for exactly this reason. If time gets tighter still, cut Section 8's second dataset before cutting anything else. |
| First-time embedded mistakes (wrong wiring, bricked flash, etc.) in Phases 4–5 | Budget slack is already built into Phase 4's 2–4 day estimate specifically because this is a first embedded project — this is expected, not a sign anything's wrong. |

---

## 16. Immediate Next Action

**Go to Phase 0: install Python, create the project folder from Section 10, and place the hardware order from Section 7 — all three can happen the same day, and none of them depend on each other.**

---

## 17. References (validated during scoping — DOIs checked)

- Giordano, M., Cortesi, S., Mekikis, P.-V., Crabolu, M., Bellusci, G., & Magno, M. (2023). Energy-Aware Adaptive Sampling for Self-Sustainability in Resource-Constrained IoT Devices. *ACM ENSsys '23*. DOI: 10.1145/3628353.3628545. (Best Paper Award; workshop paper, not a journal article — full hardware energy-audit methodology template.)
- Daupayev, N., Engel, C., & Hirsch, S. (2025). Two-to-One Trigger Mechanism for Event-Based Environmental Sensing. *Sensors*, 25(13), 4107. DOI: 10.3390/s25134107.
- Yang, C., Li, G., Gao, G., & Shi, Q. (2023). Distributed Consensus Kalman Filter Design with Dual Energy-Saving Strategy. *Sensors*, 23(6), 3261. DOI: 10.3390/s23063261. (Simulation-only.)
- Turkmanović, H., Popović, I., & Rajović, V. (2024). Toward Energy Efficient Battery State of Charge Estimation on Embedded Platforms. *Electronics*, 13(21), 4256. DOI: 10.3390/electronics13214256.
- Jain, A., Chang, E. Y., & Wang, Y.-F. (2004). Adaptive Stream Resource Management Using Kalman Filters. *ACM SIGMOD 2004*. DOI: 10.1145/1007568.1007573. (The 20+ year old ancestor of "estimator error triggers sampling" — different domain, same core idea.)
- Heo, S., Mayer, P., & Magno, M. (2022). Predictive Energy-Aware Adaptive Sampling with Deep Reinforcement Learning. *IEEE ICECS 2022*. DOI: 10.1109/ICECS202256217.2022.9971120.
- Demirel, B. U., Chen, L., & Al Faruque, M. A. (2023). Data-driven Energy-efficient Adaptive Sampling Using Deep Reinforcement Learning. *ACM Transactions on Computing for Healthcare*, 4(3), Art. 19. DOI: 10.1145/3598301.
- Hinostroza, A., Tarrillo, J., & Nuñez, M. (2026). Smart Energy Management in Agricultural Wireless Sensor Nodes Using TinyML-Based Adaptive Sampling. *Sensors*, 26(7), 2014. DOI: 10.3390/s26072014. (The key recent paper — does the "naive ML" version already, but explicitly does not measure the model's own compute cost.)

**Publication-realism note:** based on the papers above, the realistic venue tier for this project's results is a workshop (comparable to ENSsys) or a Q2/Q3 journal (comparable to *Sensors*, IEEE Access, or the Journal of Sensor and Actuator Networks) — not a top-tier ("Q1") venue on this timeline. This is a moderate-to-good outcome for an undergraduate project executed well, not a limitation to be embarrassed about.

**A full systematic literature validation (checking IEEE Xplore/ACM DL/Scopus directly, confirming journal quartiles, and building a complete evidence matrix) has not yet been run — everything above came from targeted web searches during scoping. Running that full validation is the recommended action before or during Phase 0, and is exactly the kind of task suited to a dedicated deep-research pass.**

---

## 18. Post-MVP Novelty Extension Options (decide after Phase 6, based on time remaining)

**Purpose:** once the MVP comparison (Section 3) is working and you can see how much time is actually left in your semester, decide whether to add a genuine technical contribution on top of the comparison — or ship the comparison as-is. This section holds the options so the decision doesn't need to be re-derived from scratch later.

**The honest calibration:** "novel ML algorithm" (a new architecture, a new RL method) is not realistic on this timeline and isn't needed — the project's strength is rigorous comparative measurement, not invention. What IS realistic and genuinely strengthens the paper:

1. **Energy-aware training objective** — train the learned trigger model against a loss that penalizes its own compute cost alongside prediction error, instead of training for accuracy alone and measuring energy afterward. Nobody in the literature survey (Section 17) does this. Small change (loss function), real contribution.
2. **Compression/quantization Pareto frontier** — prune/quantize the learned model specifically to shrink its own on-device footprint, and report the accuracy-vs-energy trade-off as you compress it. Also not done by anyone surveyed. Software-only work.

Both plug directly into the existing gap argument (Section 1) — they don't require inventing anything, just extending the measurement/training already planned.

**What does NOT move the needle on its own:** adding RL just to have a 4th mechanism. Deep-RL-based adaptive sampling already exists (Heo/Mayer/Magno 2022; Demirel et al. 2023 — Section 17). Adding another one without the energy-aware/compression treatment on top just repeats prior work. If RL is added, it should get the same treatment as the ML model above, not be a bare 4th line in the results table.

**What actually increases publication odds — there's no single lever, so don't look for one:** more than one dataset/domain, an ablation showing the energy-aware objective actually helps (vs. training for accuracy alone), statistical significance across repeated runs (not one lucky seed), and honestly reporting where the fancier mechanism *loses*. All of that matters more than any specific hyperparameter choice.

**Decision tiers:**

| Tier | Adds | Time cost vs. MVP (Section 12) |
|---|---|---|
| **A — Minimal novelty add** | Energy-aware training objective + compression/quantization Pareto frontier, applied to the existing 3-mechanism comparison | +3–5 days |
| **B — Moderate** | Tier A + a lightweight RL policy (tabular Q-learning or small policy-gradient — not deep) as a 4th arm | +1–2 weeks |
| **C — Ambitious** | Tier A + a full deep-RL implementation, benchmarked against Heo/Mayer/Magno- or Demirel-style baselines | +3 weeks or more — requires resetting the timeline in Section 12, not just extending it |

**When to decide:** re-open this section right after Phase 6 (Final Comparative Study) — that's when you'll know both (a) how the base 3-mechanism comparison actually looks, and (b) how much semester time is genuinely left. Don't decide earlier than that on guesswork, and don't decide later — Tier A needs to happen before Phase 7 (Analysis & Writing) starts, since it changes what Phase 7 is writing about.

**Guardrail carried over from Section 14:** whichever tier is chosen, it's a deliberate scope-change decision, not a default — update Section 3 (Scope) and Section 12 (Timeline) to reflect it once decided, so this document stays the single source of truth.

---

## 19. Appendix — Hardware/Simulation Fallback Plan (Safety Net, Independent Track)

**Status of this section: contingency reference only.** This is not the active plan. The team is proceeding with the real ESP32 + DHT22 and the Python software/ML track described in Sections 5–11. This appendix exists purely as insurance in case a piece of that plan breaks (a sensor fails, a board dies, time runs out before the INA219 arrives) — it is deliberately kept **separate** from the main phase checklist so it never gets mistaken for the current task list.

**Origin:** compiled by a teammate (AI-assisted research pass), covering ESP32/DHT22 simulators, synthetic-data approaches, and community (Reddit/forum) discussion of their limits. Kept here verbatim in substance, not because it overrides Sections 5–11, but so it isn't lost if it's needed later.

### 19.1 Why this exists
The real project has three separable problems — firmware correctness, algorithm comparison, and energy measurement — and no single tool covers all three well. If one piece stalls (e.g. the physical board misbehaves, or the INA219 arrives late), the rest of the project shouldn't be blocked. This appendix is the "what to reach for instead" list for each piece, not a redesign of the project.

### 19.2 Tool options surveyed, ranked by usefulness (not by how impressive they sound)

| # | Tool | What it's good for | Caveat |
|---|---|---|---|
| 1 | **Wokwi** (free, browser-based) | Simulates ESP32 + DHT22 firmware; lets you fake sensor values and watch the Serial Monitor. Best for testing firmware logic before/without the real board. | Not a validated energy-measurement instrument — community (Reddit) discussion specifically flags limits in its analog simulation. **Never use its virtual readings as evidence of real power savings.** |
| 2 | **Python + NumPy + pandas + Matplotlib** (local) | Generate synthetic temperature/humidity traces, inject noise/step-changes, run all three trigger mechanisms on identical input, compute reconstruction error and trigger counts. This is the actual backbone of the real Section 5–11 plan too, not just a fallback. | None — this is core infrastructure either way. |
| 3 | **The real ESP32 + DHT22 you already own** | Primary path. Read the sensor, timestamp readings, stream CSV over USB serial to the laptop for real traces. | DHT22 needs ~2s between reads — don't try to poll it faster. |
| 4 | **8gwifi Arduino Simulator** (browser, QEMU-backed) | A second firmware-test environment if Wokwi specifically breaks on something. | Not more proven than Wokwi — treat as a backup-to-the-backup, not a default. |
| 5 | **Espressif QEMU / ESP-EMU** | Advanced firmware debugging, later. | Missing I²C support on the documented targets — a poor fit for a DHT22 (I²C-adjacent) circuit experiment. Not a first choice. |
| — | Proteus / SimulIDE | Considered and **not recommended** as a primary environment. | Downloadable ESP32 symbols/footprints don't necessarily come with a working firmware simulation model — community discussion backs this up. |

### 19.3 The architectural principle behind the fallback (useful even if nothing fails)
Split the project into three layers so the trigger algorithms never know or care where their input came from:

- **Input layer:** physical DHT22 → Wokwi's virtual DHT22 → synthetic generator → a recorded dataset (all interchangeable)
- **Shared experiment engine:** the three mechanisms (deadband, Kalman, learned model) — identical code regardless of input source
- **Evaluation layer:** reconstruction error, trigger count, energy estimate, plots, report

This is already consistent with Section 5.1's conceptual pipeline — it's the same idea stated from the "what if a piece breaks" angle.

### 19.4 Synthetic-data fallback, if real/Wokwi sensor data isn't available
Three scenario types, each with a hidden "true" signal plus a noisy observation, fed to every mechanism in strict chronological order (no look-ahead):
- **Scenario A — Stable:** slow drift, small noise. Tests whether a mechanism avoids pointless transmissions when nothing is happening.
- **Scenario B — Sudden changes:** sharp steps. Tests detection speed/delay.
- **Scenario C — Noisy but slowly-changing:** tests whether filtering suppresses noise-driven false triggers without losing real signal.

Evaluate the same three metrics as the real plan (Section 9): transmission count, reconstruction MAE, estimated energy (explicitly labeled as *estimated*, from a documented cost model, until calibrated against real INA219 measurements) — never silently presented as measured.

### 19.5 Explicit verdict (carried over from the source material)
Don't treat this as "physical vs. simulated" as an either/or choice — if the real hardware works, you get a genuine demonstration; if a sensor or board fails, the software experiment still produces a complete, honest comparison; if INA219 readings turn out too noisy to resolve small energy differences, the algorithm comparison can still be presented with energy figures clearly labeled as estimated rather than measured. **This fallback protects progress on the comparison — it does not substitute for real hardware evidence when the project's actual claim is about real-world energy savings** (see Section 1's gap statement, which is specifically about measured-not-assumed energy).

### 19.6 When to actually use this appendix
Only pull from this section if something in the live plan (Sections 5–11) breaks — a dead sensor, a bricked board, a late part, or a time crunch before Phase 4/5. Otherwise, ignore it and keep working the phase checklist in Section 11.
