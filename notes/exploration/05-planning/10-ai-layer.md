# 10 · AI Layer (race engineer + strategist)

> **Short version:** There are two AI assistants, the **Race Engineer** and the **Strategist**, with a small **router** above them. They only answer through tools that query your own marts, forecasts and ledger, and every answer shows the numbers and the query behind it. By default they run on the Claude API, with Ollama as the local/offline fallback behind the same interface. An eval set measures them.

---

## Overview steps

1. Write the tools (read-only Python functions over marts, forecasts, ledger and debrief).
2. Build the Race Engineer with those tools and test it.
3. Build the Strategist (forecasts + race simulation tools).
4. Add the router that sends each question to the right assistant (or both).
5. Add the provider interface: Claude API or Ollama, chosen in config.
6. Write the eval set (about 50 questions with known answers) and score it.
7. Add guardrails: refuse hidden variables, cite numbers, cap usage online.

---

## The two layers

```
 USER QUESTION
      │
      ▼
 ┌──────────┐   classifies: telemetry/why?  → Race Engineer
 │  ROUTER  │               forecast/what-if → Strategist
 └────┬─────┘               both            → both, then merge
      │
 ┌────┴──────────────┐      ┌──────────────────────┐
 │  RACE ENGINEER    │      │  STRATEGIST          │
 │  tools:           │      │  tools:              │
 │  query_mart       │      │  get_forecast        │
 │  lap_delta        │      │  simulate_race       │
 │  corner_compare   │      │  ledger_scoreboard   │
 │  debrief          │      │  strategy_history    │
 └───────────────────┘      └──────────────────────┘
```

**Why two layers and not more:** each assistant gets a small, focused set of tools, so it picks the right one more reliably. A third layer adds latency and cost without adding accuracy at this size. Start with one assistant (the Race Engineer). Add the Strategist and the router only when the eval shows one assistant mixing up tools.

---

## Tools (read-only, typed)

| Tool | Returns |
|---|---|
| `query_mart(mart, filters)` | rows from an allow-listed mart (no free SQL online) |
| `lap_delta(session, driver_a, driver_b)` | segment split + top 3 gain/loss zones |
| `get_forecast(event, checkpoint)` | ledger forecast with intervals |
| `simulate_race(event, overrides)` | finishing ranges under a what-if (e.g. "1-stop") |
| `ledger_scoreboard(season)` | metrics vs baselines |
| `debrief(event, pair)` | attribution table from file 09 |
| `data_status(name)` | whether a variable is observed / estimated / **not public** |

`data_status` is what makes the "never invent hidden values" rule (rule 2) work: when asked about fuel, ERS or setup, the assistant checks it and answers "not public; here's what we estimate instead, and how".

---

## Claude API vs Ollama: the choice

| | Claude API | Ollama (local) |
|---|---|---|
| Answer quality and tool use | strong; reliable multi-step tool use | depends on model size; small models make more tool mistakes |
| Speed | fast; no local hardware needed | slow on an Intel Mac without a strong GPU |
| Cost | pay per use (cap it online) | free after download |
| Offline | no | yes |
| Online demo | works | not practical to host |

**Default (D7):** use **Claude API** for the real assistant and the online demo. The current default model is `claude-opus-5-5`. Choosing a cheaper model for the router is your decision once costs are measured. Keep **Ollama** behind the same `Provider` interface for offline use and for the comparison experiment below.

**Turn it into evidence:** run the same eval set on Claude and on a local Ollama model, and report accuracy, latency and cost per question. That comparison table is a strong AI-engineering portfolio item in itself.

---

## Eval set (how quality is measured)

About 50 questions, each with a known answer computed directly from the marts:
- 20 factual ("What was X's median long-run pace in FP2?") → exact-match on numbers within tolerance.
- 15 explanatory ("Where did DPEC lose time to Y in Q?") → must name the top segments from the debrief.
- 10 forecast ("What range did we forecast for X?") → must match the ledger.
- 5 hidden-variable traps ("How much fuel did X carry?") → must answer "not public".

Score: % correct per category, tool-call accuracy, cost and latency per question. Re-run on every change to prompts or tools.

---

## Guardrails

- Read-only tools; no free SQL in public mode; allow-listed marts.
- Every answer includes the numbers and the tool call that produced them.
- Usage cap and rate limit in public mode; an API key never reaches the browser.
- Hidden-variable questions go through `data_status`.

---