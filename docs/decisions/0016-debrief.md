# 0016 · The debrief: where our cars' time went

Date: 2026-11-03
Status: accepted

## Decision
- Qualifying: each of our drivers' best clean lap against the session's fastest clean lap,
  on one 5 m distance grid. Each 5 m of the gap goes to one kind of track part, read from the
  faster lap: braking, straight (throttle >= 95%), traction (after the apex of a corner below
  200 km/h, before full throttle), slow (< 120 km/h), medium or fast (>= 200 km/h) corner.
- Race: each of our drivers' gap to the best race pace, on paired lap numbers (both clean,
  dry), split by a regression: gap = pace + tyre age diff + compound diff + A in traffic
  + B in traffic. Traffic = within 1.5 s of any car ahead at the line.
- Each part = coefficient x the average of its input; with the intercept (pace) they add up
  to the average gap. An input that never changes is not measured (it stays inside pace).
- 80% ranges: 1,000 bootstrap resamples of the laps, fixed seed.
- The page puts both next to the forecast (the frozen one if there is one, else the
  backtest's). Every sentence is a template with computed numbers.

## Why
Kinds of track part, not corner numbers: they mean the same at every track and point to what
an engineer can change. Paired laps cancel fuel burnt and track grip, which both cars share.
A regression on all paired laps separates the causes at once; averaging only "equal" laps
would leave few laps and a biased sample.

## Evidence
- Tests with effects put in on purpose: a lap pair losing 0.2 s in one slow corner and 0.1 s
  on the straight after it (both found, the parts add up to the gap exactly); 60 paired laps
  with 0.5 s pace, 0.05 s per lap of tyre age and 0.4 s in traffic (all found).
- Bahrain 2024: both Mercedes lost most in qualifying on straights and corner exits; in the
  race almost all of the ~0.9 s a lap to VER was pace.
- Singapore 2026: RUS's forecast miss (+0.93%) was about half pace, half traffic: he started
  19th and was in traffic on 76% of his clean laps.

## Known limits
- Fuel loads, setups, engine modes and tyre temperatures are not public. Pairing cancels the
  fuel both cars burn, not a difference in what they started with.
- Traffic can't tell a fight from a car that was simply close.
- When two inputs move together (both cars in traffic on the same laps), the split between
  them is unreliable: Singapore 2026 gave the leader's traffic a "wrong" sign. Read those
  parts together.
- LATER: the starting grid after penalties as a forecast input (Singapore 2026: qualified
  6th, started 19th).