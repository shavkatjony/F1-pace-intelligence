# 0017 · The race engineer: one model, read-only tools, and an exam

Date: 2026-11-04
Status: accepted
Updated: 2026-11-08 (the first full exam run)
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
- One agent, not a router over several: the full exam found no kind of question that needed
  a second one. Add one only if a kind fails and the second agent fixes it on the same exam.

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
- Full exam, 8 November 2026, Claude (claude-opus-5-5): **50 of 50 passed**. Lookups 18 of 18,
  comparisons 12 of 12, forecasts 8 of 8, decisions 7 of 7, traps 5 of 5 refused ("not
  public", with the reason).
- Every answer that wasn't a trap called at least one tool: 118 tool calls in all, a median
  of 3 per question and at most 6 (the limit is 8). Most used: sql 61, tables 41, then
  forecast, tyre_decision, lap_split, race_gap, data_status and public_record.
- 18 questions had at least one tool call that returned an error; the error went back to the
  model, which corrected its call and still passed, as designed.
- Cost: $1.53 at list prices for the 50 questions (667,412 tokens, 419,675 of the input read
  from the prompt cache), a median of 7 s a question, about 6 minutes in all.
- First run, 3 November 2026: 3 questions (a lookup, a comparison, a trap), 3 of 3 passed,
  $0.06.
- Every question, answer, tool list, time and token count:
  reports/ai/eval-claude-claude-opus-5-5-2026-11-08.csv; the summary: reports/ai/README.md.
  The public copy shows the newest run in the race engineer's window.
- Tests (no key needed): the SQL guard refuses anything but one SELECT on known tables; the
  tool loop stops at the call limit; both providers' message formats work against stand-in
  servers; the grader reads numbers, words and refusals as described above.

## Known limits
- The grader reads every number in an answer: a small integer (stops, positions) can pass
  by appearing elsewhere in the sentence, and a number written in words fails.
- 50 questions are a sample, not a guarantee: a new kind of question can fail.
- One run is one sample: Claude's answers vary a little from run to run. Ollama at temperature
  0 is repeatable, but hasn't had a full exam run yet (`dpec eval-ai --provider ollama`).
- The key lives in the environment (ANTHROPIC_API_KEY), never in the project.
