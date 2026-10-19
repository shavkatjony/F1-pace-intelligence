# 0004 · Distance grid

Date: 2026-10-19
Status: accepted

## Decision
Laps are compared on a distance grid, one row every grid_step_m (5 m) from the start line.
Distance = speed x time, added up. Start and end are interpolated to the exact line,
so the grid's lap time equals the official lap time.
The second lap is stretched to the reference lap's length.

## Store or compute
All clean laps on a 5 m grid would be about 163,599 laps x ~1,070 rows = 175 million rows.
Today the only user is "compare two laps", which takes a fraction of a second.
So the grid is computed on demand and nothing is stored. If a model later needs
grids for many laps, it can store just those.

## Why stretch only the second lap
FastF1 doesn't give an official track length, and adding up speed x time drifts a
little (5,367 m vs 5,355 m). What matters is that the two laps match each other,
so the second lap is stretched to the first. The reference lap is left exactly as measured.

## How well it lines up
Same driver, two laps (Bahrain 2024 Q, VER 16 vs 13): every corner within 15 m.
It can't be 0: telemetry comes about 4 times a second, and at 120 km/h the car
moves 8 m between two samples. Rule: a corner gap of 20 m or less = lined up.

## What it showed
- VER, same Hard tyre, 3 laps old vs 18 laps old (Bahrain 2024 race, laps 20 vs 35):
  +0.858 s per lap.
  
