# SenseSmart — Hardware Track (Track B)
### For: the teammate handling hardware & firmware
### Companion to: `SenseSmart_Master_Project_Document.md` (the full project reference). This file is a focused, standalone copy of just your part — you shouldn't need to open the master document at all to do your job.

**Read this if:** you're setting up the physical board, wiring the sensor, and measuring real energy use.

**Assumed starting knowledge: zero.** This assumes no prior embedded-systems or hardware experience at all — every term is explained before it's used.

---

## 0. What this project is, in two sentences

Sensor nodes waste battery by sensing/transmitting on a fixed timer instead of only when something's actually changed. This project compares three different ways of deciding "is this worth transmitting right now" — a simple rule, a classical formula (a Kalman filter), and a small on-device machine-learning model — and your specific job is to measure, with real equipment, exactly how much electrical energy each one costs to run on a real low-power chip.

---

## 1. Your status right now

- ✅ Hardware has already been ordered (shopping list below, for reference) — nothing to buy right now.
- ⏳ Waiting on delivery — once it arrives, you start at **Phase 4** (Section 4 below).

---

## 2. What's in the box (hardware shopping list, for reference)

| Item | What it's for (plain language) |
|---|---|
| **ESP32 DevKit board** | The "brain" — a tiny low-power computer that runs the trigger logic and later gets its energy use measured |
| **Environmental sensor** (DHT22 or BME280) | The physical thing being measured — e.g. temperature |
| **INA219 current-sensing breakout board** | Measures how much electrical current — and therefore energy — the board is drawing at any moment |
| **Multimeter with a µA (microamp) range** | Measures the tiny current draw during "sleep mode" — the INA219 alone usually isn't precise enough at that scale |
| **Breadboard + jumper wires** | Connects everything without soldering — like electronic building blocks |
| **USB cable** | Powers and programs the board from a laptop |

---

## 3. Words you'll see, explained up front

| Term | Plain-English meaning |
|---|---|
| **MCU (microcontroller)** | The tiny, low-power computer chip on the board — much weaker than a laptop CPU on purpose, built to sip power, not for raw speed |
| **Dev board / devkit** | The ready-made small circuit board with the MCU plus USB/power already wired in |
| **Firmware** | The program that runs directly on the board itself (not on your laptop) |
| **Flashing** | Copying your program onto the board's memory so it can run it |
| **PlatformIO** | The tool (an extension inside VS Code) used to write, build, and upload C/C++ firmware to the board |
| **Arduino framework** | A set of ready-made C/C++ libraries (WiFi, sensors, sleep modes) used through PlatformIO, so firmware isn't written from the absolute lowest level |
| **Breadboard** | A reusable board full of holes for connecting components with wires — no soldering |
| **GPIO pin** | One of the small metal pins on the board that reads a sensor's signal or sends power/signals out |
| **I2C** | A simple way for two chips to talk to each other over two wires — this will come up in the sensor's wiring guide |
| **Datasheet** | The official reference document for a part — only small specific bits are needed, like the pin diagram |
| **Wake-up cost** | The burst of energy the chip uses coming out of sleep mode before it can do anything useful — easy to forget, often bigger than expected |
| **E_total (total energy)** | ALL the energy used — sensing + "thinking" + transmitting + waking up + going back to sleep. Not just how many times it transmitted. |

**Why C/C++ specifically (not a simpler beginner option like MicroPython):** C/C++ compiles down to native code with no extra runtime layer in the way. That matters a lot here specifically, because the numbers being measured are as small as millionths of a joule — anything with interpreter overhead sitting on top would make the measurements less trustworthy. If C/C++ is already familiar from coursework, this is the exact same language, just applied to a tiny chip instead of a laptop.

---

## 4. Your two phases

### Phase 4 — Hardware Bring-Up: First Contact With the Board (target: 2–4 days)
**Goal:** get the board talking to a laptop and reading a real sensor. Energy measurement is not part of this phase — that's Phase 5.

- [ ] Install the PlatformIO extension inside VS Code.
- [ ] Create a new PlatformIO project targeting the ESP32 board, using the Arduino-ESP32 framework.
- [ ] Connect the ESP32 via USB; confirm PlatformIO can detect and talk to it (build and upload a blank sketch as a first test).
- [ ] Blink the board's onboard LED on and off, in C++. This proves the whole toolchain works before anything more complex.
- [ ] Wire up the sensor (DHT22 or BME280) on the breadboard, following its datasheet's pin diagram.
- [ ] Write a few lines of C++, using the sensor's library, to read one real value and print it over serial (the laptop's console).

**Checkpoint / done when:** a live sensor value can be read from the board and seen printed on the laptop, reliably, more than once.

**Don't:** wire in the INA219 or start measuring energy yet — get plain sensing working first, in isolation.

---

**⏸ SYNC POINT — Phase 5 needs the "Algorithm Handoff Note" (Section 5 below) from the software side before the core measurement tasks can start. If it isn't ready when Phase 4 finishes, don't sit idle — see the tip at the end of Phase 5 below.**

---

### Phase 5 — Hardware Calibration: Measuring Real Energy Costs (target: 3–7 days)
**Goal:** get real, measured, microjoule-level numbers for every operation each of the three trigger mechanisms needs. This is the one phase whose entire purpose is measurement.

**The exact deliverable (read this before starting):** the software side's code reads your numbers from a fixed list of 9 named slots — not free-form notes. Whatever you send back must use exactly these names, so nothing needs to be rewritten on their end:

| Key | What to measure |
|---|---|
| `sleep_current_ua` | Current draw in deep-sleep mode (µA) |
| `wake_up_uj` | Energy of one wake-up-from-sleep event (µJ) |
| `sensor_read_uj` | Energy of one sensor read (µJ) |
| `tx_uj` | Energy of one wireless transmission (µJ) |
| `deadband_compute_uj` | Energy of one deadband comparison (should be ~0 — it's one subtraction) |
| `kalman_predict_uj` | Energy of one Kalman "predict" step (runs on **every reading**) |
| `kalman_update_uj` | Energy of one Kalman "update" step (runs **only when a reading is transmitted**) |
| `ml_inference_uj` | Energy of one learned-model inference (prediction) step (runs on **every reading**) |
| `ml_update_uj` | Energy of one learned-model update/learning step (runs **only when a reading is transmitted**) — **the single most important number in the whole project; nobody else has measured this (see Section 0)** |

Send these back as a simple table (spreadsheet, plain text, or — even better — filled directly into the `"measured"` block of `energy_data.json`, which the software side will share with you). Either format is fine; the names must match exactly.

- [ ] Wire in the INA219 current-sensing board.
- [ ] Measure sleep-mode current using the multimeter's µA range; sanity-check it against the ESP32's datasheet (if the number is wildly higher — sometimes 100–1000× — the board's onboard USB/regulator circuitry is probably being measured instead of the chip itself; a five-minute check, not a research problem).
- [ ] Measure active current for: one sensor reading, one wireless transmission, one wake-up event.
- [ ] Using the Algorithm Handoff Note, implement the Kalman filter's predict/update step in C++ and measure its per-cycle energy cost.
- [ ] Implement the learned model's inference step and its update/learning step **separately** in C++, and measure each one's energy cost separately. **Do not skip measuring the update step on its own.**
- [ ] Fill in all 9 keys above and send them back — this is what gets picked up by the software side's `"measured"` switch, with zero code changes on their side.

**Checkpoint / done when:** real, measured numbers exist for all 9 keys above — zero placeholder or guessed values remain.

**Don't:** chase lab-grade measurement precision. "Good enough, honestly reported" beats "perfect and three weeks late." Cap this phase at one week.

**If Phase 4 finishes before the Algorithm Handoff Note arrives:** don't wait idle — wire in the INA219 now and practice the measurement setup itself (e.g. measure the sleep current, and the blink-LED's energy cost as an arbitrary practice target). That way, once the real algorithm steps arrive, only the implementing-and-measuring is new, not the equipment itself.

### Fallback — if the INA219 doesn't work out (part delay, faulty unit, wiring/noise problems you can't resolve in time)

You are **not** blocked from delivering something useful. The software side built their pipeline to accept a second kind of number — labeled `"estimated"` instead of `"measured"` — using the exact same 9 keys above, just filled in a cheaper way:

- [ ] Get current-draw figures for active/modem-sleep/light-sleep/deep-sleep straight from the ESP32 datasheet (no INA219 needed — this is a published number, not a measurement you make).
- [ ] Time each operation (sensor read, one TX, one wake-up, each algorithm step) using the board's own clock (e.g. `micros()` printed over serial) — this needs nothing but the USB cable, already working since Phase 4.
- [ ] Multiply datasheet current × measured time × voltage to get an energy estimate (µJ) for each of the 9 keys — same units, same names, just labeled `"estimated"` instead of `"measured"` when you send it back.
- [ ] Say plainly which keys are `"estimated"` vs. `"measured"` if it ends up a mix (e.g. INA219 worked for active current but the sleep current came from the datasheet) — partial real measurement is still worth more than a full guess, and the software side's pipeline can run on a mixed set without any changes either.

This fallback is a backup plan, not the goal — try the real INA219 measurement first. But if it slips, this path still produces an honest, reportable result instead of a blocked project.

---

**⏸ SYNC POINT — once Phase 5 is done, send the finished numbers back (a simple table: operation name → measured µJ). That's the last thing needed from this track before the project can finish.**

---

## 5. The Algorithm Handoff Note — what to expect, and what it means

The software side will send a short (1–2 page), **code-free** spec covering:
1. **The deadband rule** — one comparison (e.g. "if the new reading differs from the last sent one by more than X, send it").
2. **The Kalman filter** — written as plain math/pseudocode (not Python): what values it tracks, the "predict" formula, the "update" formula, and the rule for when it decides to trigger.
3. **The learned model** — what its "inference" step computes (a simple formula) and what its "update" step does (how it adjusts itself when new data arrives), also as plain pseudocode.
4. Roughly how many basic math operations (additions, multiplications) each step involves — so there's a sense of what's being implemented before starting.

This gets translated into C++ directly — there's no need to read any Python or understand the software side's code to do this.

It will also point you back to the 9-key table in Phase 5 above (`sleep_current_ua`, `wake_up_uj`, `sensor_read_uj`, `tx_uj`, `deadband_compute_uj`, `kalman_predict_uj`, `kalman_update_uj`, `ml_inference_uj`, `ml_update_uj`) — that's the exact shape your measurements (real or fallback-estimated) need to come back in, so the software side's energy switch (their Section 9) works without them touching any code.
