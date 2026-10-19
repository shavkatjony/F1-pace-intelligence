# 0004 · Distance grid

Date: 2026-10-__
Status: accepted

## Decision
Laps are compared on a distance grid, one row every grid_step_m (5 m) from the start line.
Distance = speed x time, added up. Start and end are interpolated to the exact line.
The second lap is stretched to the reference lap's length.

## Store or compute
(your Part 1 question 1: the row estimate, and why compute on demand for now)

## Why stretch only the second lap
(your Part 1 question 2)

## How well it lines up
(your 8a result: biggest corner gap in metres, and why it can't be 0)

## What it showed
(one line each from 8b and 8d)

### sample test results 
####  VER lap 20   official 95.160 s | on grid 95.160 s | clean
#### VER lap 35   official 96.018 s | on grid 96.018 s | clean
* Lap length (reference): 5360 m, 1073 grid points

* Gap at the line: +0.858 s (VER lap 35 vs VER lap 20)

* 
