"""The decision packet (step C4, decision 0014): one page per race, as it would have looked
before the race, and under it what really happened.

Every number is computed: the race pace forecast `dpec backtest` saved, the tyre wear and stop
plan of decisions.replay, and the reasons it could be wrong, each with its number. No sentence
comes from an AI. "No clear decision" is an allowed answer.
"""

import re
import unicodedata
from pathlib import Path

import pandas as pd

from dpec.decisions.plans import CLEAR, flip_wear
from dpec.decisions.replay import replay_all
from dpec.decisions.tyres import strategy_table
from telemetry_core.warehouse import query

THIN_PRACTICE = 15  # fewer dry long runs than that is thin evidence (sprint weekends: one FP)

OUR_RACE_SQL = """
SELECT r.driver_code, r.grid_position, r.finish_position,
    s.stint, s.compound, s.first_lap, s.last_lap
FROM core_results AS r
LEFT JOIN mart_stints AS s
    ON s.season = r.season AND s.round = r.round AND s.driver_code = r.driver_code
    AND s.session_type = 'R'
WHERE r.session_type = 'R' AND r.season = ? AND r.round = ?
    AND r.team_id IN (SELECT team_id FROM dim_teams WHERE lineage = ?)
ORDER BY r.finish_position NULLS LAST, r.driver_code, s.stint
"""


def our_lineage(warehouse: Path, adopted_team: str) -> str:
    """'Mercedes' -> 'mercedes': the team's id across its name changes (dim_teams)."""
    found = query(
        warehouse,
        "SELECT any_value(lineage) AS lineage FROM dim_teams WHERE lower(team_name) = lower(?)",
        [adopted_team],
    )
    return found["lineage"].iloc[0]


def runner_up(plans: pd.DataFrame, stops: int) -> int:
    """The other plan that came closest: best in the most replays, then the smallest loss."""
    others = plans[plans["stops"] != stops]
    order = others.sort_values(["p_best", "seconds_behind_best"], ascending=[False, True])
    return int(order["stops"].iloc[0])


def reasons(today: pd.Series, history: pd.DataFrame, d: pd.Series, other: int) -> list[str]:
    """What could make this packet wrong, computed, each with its number."""
    flip = flip_wear(int(today["race_laps"]), d["pit_loss_s"], d["stops"], other)
    side = "above" if other > d["stops"] else "below"
    out = [
        (
            f"If tyre wear is {side} {flip:.3f} s/lap (forecast {d['deg']:.3f}), "
            f"{stops_text(other)} would beat {stops_text(d['stops'])}. Watch the first "
            "stint's lap times."
        )
    ]
    if d["deg_low"] <= flip <= d["deg_high"]:
        out.append(f"That flip point is inside the 80% range of tyre wear: {wear_range(d)}.")
    runs = 0 if pd.isna(today["practice_long_runs"]) else int(today["practice_long_runs"])
    if runs < THIN_PRACTICE:
        out.append(
            f"Thin practice evidence: {runs} long runs on dry tyres (fewer than {THIN_PRACTICE})."
        )
    here = history[history["circuit"] == today["circuit"]]
    if here.empty:
        out.append("New circuit: tyre wear and pit loss come from the average of all circuits.")
    else:
        neutralised = (here["safety_car_laps"] + here["vsc_laps"]) > 0
        if neutralised.mean() >= 0.5:
            out.append(
                f"A safety car or VSC came out in {neutralised.sum()} of {len(here)} earlier "
                "races here: it makes a stop cheaper and can change the plan."
            )
    if not d["clear"]:
        out.append(
            f"The plans are close: the best one wins only {d['p_best']:.0%} of the replays "
            f"(a clear decision needs {CLEAR:.0%})."
        )
    return out


def make_packet(
    warehouse: Path,
    forecasts: Path,
    season: int,
    round_no: int,
    adopted_team: str,
    checkpoint: str = "after_quali",
) -> dict:
    """Everything one packet says, as plain values (to_markdown turns it into a page)."""
    replayed, plans = replay_all(warehouse, until=(season, round_no))
    if (season, round_no) not in plans:
        raise ValueError(
            f"no packet for {season} round {round_no}: replays start in 2023, and wet races "
            "are not forecast (decision 0011)"
        )
    d = replayed.iloc[-1]  # the replay stopped after this race
    table = strategy_table(warehouse)
    today = table[(table["season"] == season) & (table["round"] == round_no)].iloc[0]
    history = table[table["race_date"] < today["race_date"]]
    plan_table = plans[(season, round_no)]
    other = runner_up(plan_table, d["stops"])
    lineage = our_lineage(warehouse, adopted_team)

    pace = None
    if forecasts.exists():
        f = pd.read_parquet(forecasts)
        f = f[
            (f["forecaster"] == "shared_model")
            & (f["season"] == season)
            & (f["round"] == round_no)
            & (f["checkpoint"] == checkpoint)
        ].sort_values("predicted")
        top3 = f.head(3)["driver_code"].tolist()
        pace = f[(f["lineage"] == lineage) | f["driver_code"].isin(top3)]

    return {
        "season": season,
        "round": round_no,
        "circuit": today["circuit"],
        "race_date": today["race_date"],
        "checkpoint": checkpoint,
        "adopted_team": adopted_team,
        "lineage": lineage,
        "pace": pace,
        "today": today,
        "decided": d,
        "plans": plan_table,
        "runner_up": other,
        "reasons": reasons(today, history, d, other),
        "our_race": query(warehouse, OUR_RACE_SQL, [season, round_no, lineage]),
    }


def file_name(p: dict) -> str:
    """'2024-01-sakhir.md': season, round, circuit in plain letters."""
    plain = unicodedata.normalize("NFKD", p["circuit"]).encode("ascii", "ignore").decode()
    return f"{p['season']}-{p['round']:02d}-{re.sub(r'[^a-z0-9]+', '-', plain.lower()).strip('-')}.md"


def pct(v: float) -> str:
    return "-" if pd.isna(v) else f"{v:+.2f}%"


def chance(v: float) -> str:
    return "-" if pd.isna(v) else f"{v:.0%}"


def stops_text(n: int) -> str:
    return f"{n:.0f} stop" if n == 1 else f"{n:.0f} stops"


def wear_range(d: pd.Series) -> str:
    if pd.isna(d["deg_low"]):
        return "no range yet (fewer than 5 earlier races to learn its errors from)"
    return f"{d['deg_low']:.3f} to {d['deg_high']:.3f} s/lap"


def pace_section(p: dict) -> str:
    if p["pace"] is None or p["pace"].empty:
        return "No pace forecast saved for this race: run `uv run dpec backtest` first."
    rows = [
        "| driver | forecast gap | 80% range | best pace | top-3 pace | beats teammate |",
        "|---|---|---|---|---|---|",
    ]
    for r in p["pace"].itertuples():
        star = " ★" if r.lineage == p["lineage"] else ""
        rows.append(
            f"| {r.driver_code}{star} | {pct(r.predicted)} | {pct(r.low)} to {pct(r.high)} "
            f"| {chance(r.p_best)} | {chance(r.p_top3)} | {chance(r.p_beats_teammate)} |"
        )
    rows.append("")
    rows.append(
        "Gap = % behind the fastest car's race pace (median clean lap). The forecast top 3 "
        "and our cars (★). Chances come from 4,000 replays of the model's past errors."
    )
    return "\n".join(rows)


def tyre_section(p: dict) -> str:
    d, today = p["decided"], p["today"]
    if pd.isna(today["practice_deg_s_per_lap"]):
        practice = "No dry long runs in practice: the forecast is this circuit's race history."
    else:
        practice = (
            f"Practice long runs said {today['practice_deg_s_per_lap']:.3f} "
            f"({today['practice_long_runs']:.0f} runs); races wear tyres less than practice."
        )
    lines = [
        (
            f"- Tyre wear: **{d['deg']:.3f} s/lap** per lap of tyre age, 80% range "
            f"{wear_range(d)}. {practice}"
        ),
        f"- A pit stop here costs **{d['pit_loss_s']:.1f} s** (median of earlier races).",
        (
            f"- Useful life: after about **{d['useful_life']:.0f} laps** a set has lost as much "
            f"time as a pit stop costs (race: {today['race_laps']} laps)."
        ),
    ]
    return "\n".join(lines)


def plan_section(p: dict) -> str:
    d = p["decided"]
    rows = [
        "| stops | seconds lost vs the best plan | 80% range | best plan in |",
        "|---|---|---|---|",
    ]
    for r in p["plans"].itertuples():
        rows.append(
            f"| {r.stops} | {r.seconds_behind_best:.1f} | {r.low_s:.1f} to {r.high_s:.1f} "
            f"| {r.p_best:.0%} of replays |"
        )
    if d["clear"]:
        verdict = f"**Preferred: {stops_text(d['stops'])}** (best in {d['p_best']:.0%} of replays)."
    else:
        a, b = sorted([d["stops"], p["runner_up"]])
        verdict = f"**No clear decision: {a} or {b} stops.**"
    first, last, shift = d["window_first"], d["window_last"], d["shift"]
    window = f"First stop window for {stops_text(d['stops'])}: **laps {first}-{last}**."
    if shift:
        why = (
            f"Tyre wear alone says laps {first - shift}-{last - shift}; in earlier races real "
            f"first stops of this plan came {abs(shift)} laps "
            f"{'earlier' if shift < 0 else 'later'} (the undercut), so the window moves."
        )
    else:
        why = "From tyre wear alone (too few earlier first stops of this plan to move it)."
    return "\n".join([*rows, "", verdict, "", f"{window} {why}"])


def reveal_section(p: dict) -> str:
    d = p["decided"]
    if pd.isna(d["deg_low"]):
        inside = "no range to check"
    elif d["deg_low"] <= d["actual_deg"] <= d["deg_high"]:
        inside = "inside the 80% range"
    else:
        inside = "outside the 80% range"
    right = "right" if d["actual_stops"] == d["stops"] else "wrong"
    plan = stops_text(d["stops"])
    if d["green_first_stops"]:
        window = (
            f"- First stops of top-10 drivers on {plan} (green flag) inside the window: "
            f"{d['inside_window']} of {d['green_first_stops']}."
        )
    else:
        window = f"- No top-10 driver raced {plan} with a green-flag first stop: no window check."
    lines = [
        f"- Tyre wear: **{d['actual_deg']:.3f} s/lap** ({inside}).",
        (
            f"- The top 10 most often made **{stops_text(d['actual_stops'])}**; the packet's "
            f"most likely plan was {plan}: {right}."
        ),
        window,
    ]
    pace = p["pace"] if p["pace"] is not None else pd.DataFrame(columns=["driver_code"])
    for code, race in p["our_race"].groupby("driver_code", sort=False):
        first = race.iloc[0]
        finish = "-" if pd.isna(first["finish_position"]) else f"P{first['finish_position']:.0f}"
        grid = "-" if pd.isna(first["grid_position"]) else f"P{first['grid_position']:.0f}"
        tyres = " > ".join(
            f"{s.compound[0]} {s.first_lap:.0f}-{s.last_lap:.0f}"
            for s in race.dropna(subset=["stint"]).itertuples()
        )
        line = f"- {code} ★: grid {grid}, finished {finish}, tyres {tyres or '-'}"
        mine = pace[pace["driver_code"] == code]
        if len(mine):
            r = mine.iloc[0]
            inside = r["low"] <= r["actual"] <= r["high"]
            line += (
                f"; race pace {pct(r['actual'])} (forecast {pct(r['predicted'])}, "
                f"{'inside' if inside else 'outside'} the range)"
            )
        lines.append(line + ".")
    return "\n".join(lines)


def to_markdown(p: dict) -> str:
    """The packet as a page: before the race (sections 1-4), then the reveal (section 5)."""
    when = "practice and qualifying" if p["checkpoint"] == "after_quali" else "practice"
    made = pd.Timestamp(p["race_date"])
    intro = (
        f"Made as if before the race of {made:%d %b %Y}, from {when} of this weekend and "
        f"earlier races only. Our cars: {p['adopted_team']} (★)."
    )
    sections = [
        f"# Decision packet · {p['season']} round {p['round']} · {p['circuit']}",
        intro,
        "## 1. Race pace (shared model)\n\n" + pace_section(p),
        "## 2. Tyres\n\n" + tyre_section(p),
        "## 3. Plan\n\n" + plan_section(p),
        "## 4. What could make this wrong\n\n" + "\n".join(f"- {r}" for r in p["reasons"]),
        "## 5. After the race: what happened\n\n" + reveal_section(p),
    ]
    return "\n\n".join(sections) + "\n"
