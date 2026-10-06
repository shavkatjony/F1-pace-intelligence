# DPEC — F1 Race-Weekend Performance & Decision Engine

> **Forecast race performance from real F1 telemetry, quantify uncertainty, and turn practice data into evidence-based race decisions.**

**Status:** 🚧 Planning / Development not started yet

DPEC is a personal **Data Science, ML, Analytics, and AI Engineering** project built around a practical F1 problem:

> **After each practice session, what can we reliably infer about qualifying and race performance — and what should that imply for the race?**

It is designed around **messy public telemetry**, incomplete information, forecasting under uncertainty, reproducible evaluation, and decision support.

---

## What DPEC Does

```text
Real F1 Data
     ↓
Data Quality & Alignment
     ↓
Analytics
     ↓
Performance Forecast
     ↓
Uncertainty
     ↓
Tyre / Stint Scenarios
     ↓
Decision Support
     ↓
Race
     ↓
Forecast vs Reality
     ↓
Debrief
```


## Example Questions

### Performance

> What is our expected race pace after FP2?

> Which cars appear strongest over long runs?

> How certain is that ranking?

### Tyres

> How quickly is the medium tyre degrading?

> How many competitive laps may remain in this stint?

> When does degradation appear to increase sharply?

### Strategy

> What pit window is currently supported by the evidence?

> What changes if degradation is 20% worse than expected?

> Are an early and late pit actually distinguishable given current uncertainty?

### Debrief

> Why was our race-pace forecast wrong?

> How much of the gap came from tyres, track evolution, traffic, or car/driver performance?

### AI

> Why is confidence in the race forecast low?

> What evidence supports the current strategy scenario?

> Which assumptions could invalidate the recommendation?

---


---


## Technical Focus

The project is intended to demonstrate:

**Python · SQL · Statistics · Time Series · ML · Data Engineering · Forecasting · Uncertainty · Model Evaluation · APIs · Testing · AI Tool Use**

Planned stack:

```text
Python
DuckDB
Parquet
dbt
FastAPI
pytest
GitHub Actions
MLflow
FastF1
Jolpica
```

---

## Modelling

The forecasting system will be evaluated with:

- simple baselines first
- walk-forward validation
- race-weekend/time-based splits
- uncertainty intervals
- calibration checks
- cross-circuit evaluation
- in-season updating

No random lap-level splitting that causes future information leakage.

---

## Public-Data Constraint

DPEC only uses information that is actually available.

Hidden variables such as exact:

- fuel load
- engine mode
- ERS state
- setup details
- private tyre measurements

are **not presented as observed data**.

Where their effects are estimated, they are explicitly labelled as **estimated**.

---



## Project Philosophy

> **The goal is not to build the biggest F1 dashboard.**

The goal is to build a small, reproducible engineering system that can answer a difficult question, make a prediction before the answer is known, and prove afterward whether it worked.

---

## Current Status

🚧 **Planning**

The architecture, scope, modelling direction, evaluation methodology, and decision-support design are currently being defined.

The project will be built incrementally, with each stage producing a testable result before moving to the next stage.

---

## Author

**Shavkatjon Yuldashev**

Personal research project focused on:

**Data Science · ML · Analytics · AI Engineering · Motorsport**
