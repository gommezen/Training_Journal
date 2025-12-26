# a lightweight training journal

The app combines:
- quick session logging
- explicit rest days
- daily reflection
- weekly and period-based summaries
- explicit perceived effort (RPE)
- derived training load and rhythm metrics

It is designed to support *thinking about training*.

---

## What this app is for

- Logging Karate, strength, running, rowing, cardio, and rest
- Recording perceived effort (RPE) alongside duration
- Reflecting on individual training days
- Reviewing training rhythm, volume, and continuity over time
- Comparing periods only when the data meaningfully allows it

---

## Core principles

- Effort is explicit, not inferred
    Intensity is recorded as RPE by the athlete, not guessed from session type.

- Derived metrics are computed, never stored
    Training load and summaries are calculated from raw data.

- Missing data is shown as missing
    Undefined comparisons are displayed as —, not silently filled in.

- Reflection comes before optimization
    The journal supports noticing patterns

---

## Running the app locally

### 1. Create and activate a virtual environment

python -m venv .venv

.venv\Scripts\activate

### 2. Install dependencies

pip install streamlit pandas plotly

### 3. Run the app

streamlit run app.py

---