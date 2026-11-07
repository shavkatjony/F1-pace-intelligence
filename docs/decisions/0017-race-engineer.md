# 0017 · The race engineer: one model, read-only tools, and an exam

Date: 2026-11-04
Status: accepted
Builds on: [0007](0007-marts.md) marts, [0011](0011-target-and-fair-test.md) target and fair test, [0014](0014-decision-packet.md) decision packet, [0015](0015-public-record.md) public record, [0016](0016-debrief.md) debrief

## Decision
- One race engineer: a language model with eight read-only tools (tables, sql, lap_split,
  race_gap, forecast, tyre_decision, public_record, data_status). It never answers from
  memory: every number must come from a tool result and names the tool in brackets.
  Fuel, ERS, setups, tyre temperatures and pressures, active aero and radio: "not public".
- The sql tool: SELECT or WITH only, one statement, known tables only, no file readers,
  a read-only connection, 10 s timeout, 50 rows, 20,000 characters.
- Provider: Claude (claude-opus-5-5, effort medium, prompt caching, server-side fallback)
  by default; Ollama (qwen3:8b) for free offline use. Same tools, same loop, same exam.
- At most 8 tool calls per question. Live questions only run on the local app, because each
  one costs money; the public copy shows the answers from the newest exam run instead.
- One agent, not a router over several: add a second agent only if a kind of question fails
  on the exam and the second agent fixes it on the same exam.

## Why
A model that doesn't know a number invents a plausible one. Tools over the warehouse make
every answer checkable and keep it current as races arrive. One agent with good tools is
simpler, cheaper and easier to test than several agents.

## The exam
50 questions in evals/questions.yaml: 18 lookups, 12 comparisons, 8 forecasts, 7 decisions,
5 traps (must refuse). Each right answer is computed from the warehouse when the exam runs.
A question passes when every check passes: numbers within a tolerance (default 0.01; lap
times as m:ss.sss also read as seconds; percentages also as fractions), words as whole words,
traps by a refusal phrase.

## Evidence


## Known limits
- The grader reads every number in an answer: a small integer (stops, positions) can pass
  by appearing elsewhere in the sentence, and a number written in words fails.
- 50 questions are a sample, not a guarantee: a new kind of question can fail.
- Claude's answers vary a little from run to run; Ollama at temperature 0 is repeatable.
- The key lives in the environment (ANTHROPIC_API_KEY), never in the project.
