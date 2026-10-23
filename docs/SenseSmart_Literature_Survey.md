# SenseSmart — Literature Survey & Research Gap Justification
### For mentor review — permission-to-proceed document

**Coverage:** 2021–2026 (past 5 years) · **Papers:** 13 (12 fully DOI-verified + 1 flagged) · **Purpose:** show, paper by paper, that no existing published work combines all three requirements our project targets — and therefore that the gap is real, not assumed.

---

## How to read the table

- **Mechanism** = what kind of "should I sense/transmit now?" logic the paper studies.
- **Real HW?** = tested on physical hardware (not simulation only).
- **Full E_total?** = energy accounting includes sensing + compute + radio + sleep + wake-up (not just transmission count).
- **Model cost isolated?** = the paper separately measures what its own trigger mechanism's compute (or learning) costs, rather than assuming it's negligible.
- **Y** = yes, confirmed · **N** = no / not done · **Partial** = done for part of the system only · **NR** = not reported at the depth checked · **N/A** = doesn't apply to this paper's design

**The gap becomes visible by scanning down the last three columns — no row has Y / Y / Y for a KF, ML, or RL-based mechanism.** The two closest papers (rows 7 and 13) each satisfy two of the three and explicitly miss the third — for two different reasons. That's not a coincidence; it's the gap.

---

## Literature Survey Table (2021–2026)

| # | Paper (Authors, Year) | Venue (Type) | DOI | Mechanism | Real HW? | Full E_total? | Model cost isolated? | Key Limitation |
|---|---|---|---|---|---|---|---|---|
| 1 | Heo, Mayer & Magno, 2022 | IEEE ICECS (Conference) | 10.1109/ICECS202256217.2022.9971120 | Deep RL (actor-critic) | N (trace-driven from harvested-energy recordings) | NR | N | RL policy's own energy cost not isolated; not a live on-device deployment |
| 2 | Giordano, Cortesi, Mekikis, Crabolu, Bellusci & Magno, 2023 | ACM ENSsys'23 (Workshop) | 10.1145/3628353.3628545 | Rule-based FSM (AIMD, battery-feedback only) | Y (NRF52833 "EcoTrack" node) | Y (full component breakdown) | Y (~2.7 µJ/day) | The *only* fully rigorous audit found — but deliberately uses the simplest possible mechanism, not KF/ML/RL |
| 3 | Stricker, Lian, Jiang, Jones & Thiele, 2023 | ACM Trans. Cyber-Physical Systems (Journal) | 10.1145/3597311 | Self-triggered MPC (control-theoretic) | N (simulation: double-integrator + room-climate case study) | N | N | Simulation only; no real hardware energy numbers |
| 4 | Yang, Li, Gao & Shi, 2023 | Sensors (Journal, MDPI) | 10.3390/s23063261 | Classical KF (distributed consensus) | N (simulation, Lyapunov-stability proof) | N | N | Effectiveness shown only in simulation |
| 5 | Li & Hao, 2023 | Sensors (Journal, MDPI) | 10.3390/s23042202 | Classical KF (event-triggered) | NR (accuracy/threshold analysis framing; no hardware deployment described) | N | N | Focused on estimation-accuracy-vs-communication-rate trade-off, not measured energy |
| 6 | Demirel, Chen & Al Faruque, 2023 | ACM Trans. Computing for Healthcare (Journal) | 10.1145/3598301 | Deep RL | Partial (compatible with ≥128 KB RAM devices; compute/memory-cost framing) | N (reports 7.3× computational efficiency, not measured joules) | Partial (efficiency claimed, not isolated in µJ) | Single application domain (ECG); efficiency shown as a computational ratio, not a real power-rail measurement |
| 7 | Turkmanović, Popović & Rajović, 2024 | Electronics (Journal, MDPI) | 10.3390/electronics13214256 | Classical KF (EKF, two model orders) vs. Coulomb-counting | Y (STM32H7) | Partial (MCU compute cost only — sensor/radio/sleep out of scope) | Y (estimator's own cost measured) | Missing piece: full node E_total, not just the estimator |
| 8 | Fay, Corcoran & Diamond, 2024 | Sensors (Journal, MDPI) | 10.3390/s24010162 | TinyML binary event classifier | Y (real-time MCU detection) | Partial (94.8–99.8% transmission reduction reported; not a joule-level breakdown) | N (compares to generic "AI/ML platforms," not its own measured µJ cost) | Power savings reported as % transmission avoided, not measured total energy |
| 9 | Lee, Oh & Pak, 2024 | Energies (Journal, MDPI) | 10.3390/en17225651 | Hybrid KF + FIR filter, event-triggered transmission | Partial (real photovoltaic sensor data; not clearly a live power-measured embedded node) | N (transmission-rate reduction, not joules) | N | Real dataset, but no measured node energy or filter compute cost |
| 10 | [Authors per J. Franklin Inst. record], 2024/2025 | J. of the Franklin Institute (Journal, Elsevier) | *Not independently confirmed this pass — Vol. 362, Issue 3 (2025), Art. 107509* | Cubature KF (cooperative, dynamic event-triggered) | N (stochastic-stability/simulation framing) | N | N | Simulation only; energy mentioned as motivation, not measured — **flagged: verify DOI before citing as strong evidence** |
| 11 | Daupayev, Engel & Hirsch, 2025 | Sensors (Journal, MDPI) | 10.3390/s25134107 | Pure threshold (two-to-one cross-sensor gating) | Y (PIC16LF19156, custom multivariate sensor) | Partial (sensing energy addressed directly; MCU/radio/sleep NR at reviewed depth) | N/A (no estimator/ML — free logic) | No estimator cost to isolate; not shown as a full breakdown |
| 12 | Mackenzie, Michiels & Hughes, 2025 | IEEE DCOSS-IoT (Conference, short paper) | 10.1109/DCOSS-IoT65416.2025.00045 | N/A — about the measurement instrument, not a trigger policy | Y (hardware + software co-design) | N/A | N/A | Important methodology reference for measuring correctly — not a competing trigger-comparison result |
| 13 | Hinostroza, Tarrillo & Nuñez, 2026 | Sensors (Journal, MDPI) | 10.3390/s26072014 | Lightweight on-device ML (online SGD regressor) | Y (ESP32, 60-day real farm deployment) | Y (6-stage breakdown: boot, sample, radio-init, TX, sleep-init, sleep) | **N — explicitly assumed negligible, not measured** | The closest paper to "done already" — but the one thing it skips is exactly our target measurement |

---

## What this collectively shows

- **9 of 13** entries are genuine peer-reviewed **journal** articles (Sensors, Electronics, Energies, ACM ToCH, ACM TCPS, J. Franklin Institute); the remaining 4 are conference/workshop papers, included because they're the most directly relevant methodology or novelty-threat sources, not counted as "journal evidence."
- **Every KF-based paper found (rows 3, 4, 5, 9, 10) is simulation-only or lacks a real measured energy number.** This is a pattern across five independent papers, not one paper's limitation.
- **Every ML/RL-based paper found (rows 1, 6, 13) either isn't on live hardware, reports efficiency as a computational ratio rather than measured joules, or explicitly assumes its own cost is negligible instead of measuring it.**
- **Row 7 (Turkmanović) and row 13 (Hinostroza) are the two closest papers to closing this gap — and each is missing a different, specific piece:** Turkmanović measures the estimator's own cost but not the full node; Hinostroza measures the full node but not the model's own cost. No paper does both at once, for any mechanism more complex than a free threshold rule.
- **Row 2 (Giordano) is the one paper that does everything rigorously — for the cheapest possible mechanism.** That it exists, and that nothing comparable exists for a costlier (KF/ML/RL) mechanism, is itself evidence that the harder version of this measurement hasn't been done.

---

## Research Gap Statement (for permission request)

> Across 13 papers published 2022–2026 studying trigger mechanisms for adaptive/event-based sensing — spanning classical Kalman-filter variants, deep reinforcement learning, and lightweight on-device machine learning — no paper measures, on real embedded hardware, the full sense-compute-transmit-sleep energy cost of a KF-, ML-, or RL-based trigger *while also isolating what that mechanism's own compute (including any on-device learning/adaptation) costs*, rather than assuming it is negligible. The two most advanced papers found (Turkmanović et al., 2024; Hinostroza et al., 2026) each satisfy two of these three requirements but not all three, for different reasons. This project proposes to close that gap: benchmarking a rule-based baseline, a classical Kalman filter, and a lightweight learned model against each other on the same hardware, under one consistent energy-accounting method, with each mechanism's own cost — including the learned model's on-device update step — measured rather than assumed.

---

## Verification methodology (for transparency)

- Each entry was checked individually against its publisher record (MDPI, ACM Digital Library, IEEE Xplore, ScienceDirect, or PubMed/DBLP) — title, authors, year, venue, and DOI were confirmed to match before inclusion.
- Row 10 is flagged rather than silently included: its existence, journal, volume, issue, and article number are confirmed, but the exact DOI string was not directly located this pass. It is kept in the table for completeness but should not be cited as strong evidence until the DOI is confirmed.
- **This was a targeted verification pass (web search against publisher sites), not a full systematic database search** (Scopus/Web of Science/IEEE Xplore direct query). It's sufficient to justify requesting permission to proceed, but a full systematic search is the appropriate next step once permission is granted, both to catch anything missed and to pull formal journal-quartile/impact-factor data for the eventual paper's related-work section.
- Journal quartile/impact-factor figures are intentionally **not** stated in this table — they weren't independently verified this pass, and asserting a number without checking it would be worse than leaving it blank.

---

## Foundational context (outside the 5-year window — background only, not counted toward the 13)

| Paper | Year | Why it matters |
|---|---|---|
| Jain, Chang & Wang, "Adaptive Stream Resource Management Using Kalman Filters," ACM SIGMOD | 2004 | DOI 10.1145/1007568.1007573 (verified). Shows the core idea — "estimator error drives adaptive resource use" — is 20+ years old in a different domain (databases, not embedded energy). Important novelty-threat context, not evidence for or against the current gap. |
