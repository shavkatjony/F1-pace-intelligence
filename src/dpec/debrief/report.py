"""The debrief (step D1, decision 0016): after a race, where our cars' time went.

1. Qualifying: each of our drivers' best lap against the fastest lap, split by part of the track.
2. Race: each one's gap to the best race pace, split into pace, tyres and traffic.
3. The forecast: what was frozen (or, for a past race, what the backtest said) next to what
   happened, and the biggest part of the gap that wasn't pace.
Every sentence is a template filled with computed numbers, like the decision packet.
"""

from pathlib import Path

import duckdb
import pandas as pd

from dpec.debrief.attribution import attribute, paired_laps
from dpec.debrief.segments import lap_gap
from dpec.decisions.packet import our_lineage
from dpec.forecasting.targets import forecast_table
from dpec.record.ledger import LEDGER, Forecast, event_folder, read
from telemetry_core.warehouse import query

BEST_LAPS_SQL = """
SELECT l.driver_code, l.lap_number, l.lap_time_s, coalesce(t.lineage, l.team) AS lineage
FROM core_laps AS l
LEFT JOIN dim_teams AS t ON t.team_name = l.team
WHERE l.session_key = ? AND l.is_clean
QUALIFY row_number() OVER (PARTITION BY l.driver_code ORDER BY l.lap_time_s) = 1
ORDER BY l.lap_time_s
"""

PART_NAMES = {
    "pace": "pace on equal tyres in clean air",
    "tyre_age": "older tyres",
    "tyre_compound": "harder tyres",
    "a_traffic": "traffic (his)",
    "b_traffic": "traffic (the leader's)",
}


def key(season: int, round_no: int, session: str) -> str:
    return f"{season}_{round_no:02d}_{session}"


def quali_part(warehouse: Path, raw: Path, season: int, round_no: int, lineage: str) -> list:
    """Each of our drivers' best qualifying lap against the fastest one."""
    best = query(warehouse, BEST_LAPS_SQL, [key(season, round_no, "Q")])
    if best.empty:
        return []
    ref = best.iloc[0]
    out = []
    for r in best[best["lineage"] == lineage].itertuples():
        item = {"driver": r.driver_code, "ref": ref["driver_code"], "gap_s": None}
        if r.driver_code != ref["driver_code"]:
            try:
                split, official, _ = lap_gap(
                    warehouse,
                    raw,
                    key(season, round_no, "Q"),
                    (ref["driver_code"], int(ref["lap_number"])),
                    (r.driver_code, int(r.lap_number)),
                )
                item.update(gap_s=official, split=split)
            except (ValueError, duckdb.IOException):
                item["problem"] = "no telemetry saved for this qualifying session"
        out.append(item)
    return out


def race_part(warehouse: Path, season: int, round_no: int, lineage: str) -> tuple[str, list]:
    """The best race pace's driver, and each of our drivers' race gap to him, split."""
    table = forecast_table(warehouse)
    race = table[(table["season"] == season) & (table["round"] == round_no)]
    if race.empty:
        return "", []
    leader = race.sort_values("race_pace_gap_pct")["driver_code"].iloc[0]
    out = []
    for r in race[race["lineage"] == lineage].itertuples():
        item = {"driver": r.driver_code, "actual_gap_pct": r.race_pace_gap_pct}
        if r.driver_code != leader:
            laps = paired_laps(warehouse, key(season, round_no, "R"), r.driver_code, leader)
            item["laps"] = len(laps)
            try:
                item["parts"] = attribute(laps)
                item["mean_gap_s"] = laps["gap_s"].mean()
                item["traffic_share"] = laps["a_in_traffic"].mean()
            except ValueError as problem:
                item["problem"] = str(problem)
        out.append(item)
    return leader, out


def frozen_or_backtest(data: Path, season: int, round_no: int) -> tuple[str, pd.DataFrame]:
    """The after-quali forecast: the frozen one in ledger/ if there is one (a live weekend),
    otherwise the backtest's (a past weekend). Columns driver_code, predicted, low, high."""
    folders = sorted((LEDGER / str(season)).glob(f"{round_no:02d}-*"))
    frozen = folders[0] / "after_quali.json" if folders else None
    if frozen and frozen.exists():
        f = read(frozen)
        assert isinstance(f, Forecast)
        rows = [(d.driver_code, d.predicted_gap_pct, d.low_pct, d.high_pct) for d in f.drivers]
        return "frozen before the race", pd.DataFrame(
            rows, columns=["driver_code", "predicted", "low", "high"]
        )
    saved = data / "forecasts" / "backtest.parquet"
    if saved.exists():
        bt = pd.read_parquet(saved)
        bt = bt[
            (bt["forecaster"] == "shared_model")
            & (bt["season"] == season)
            & (bt["round"] == round_no)
            & (bt["checkpoint"] == "after_quali")
        ]
        return "the backtest's (made from earlier races only)", bt[
            ["driver_code", "predicted", "low", "high"]
        ]
    return "", pd.DataFrame(columns=["driver_code", "predicted", "low", "high"])


def make_debrief(
    warehouse: Path, raw: Path, data: Path, season: int, round_no: int, adopted_team: str
) -> dict:
    lineage = our_lineage(warehouse, adopted_team)
    circuit = query(
        warehouse,
        "SELECT any_value(circuit) AS circuit FROM core_sessions WHERE season = ? AND round = ?",
        [season, round_no],
    )["circuit"].iloc[0]
    if circuit is None:
        raise ValueError(f"nothing saved for {season} round {round_no}")
    leader, race = race_part(warehouse, season, round_no, lineage)
    source, forecast = frozen_or_backtest(data, season, round_no)
    return {
        "season": season,
        "round": round_no,
        "circuit": circuit,
        "team": adopted_team,
        "quali": quali_part(warehouse, raw, season, round_no, lineage),
        "leader": leader,
        "race": race,
        "forecast_source": source,
        "forecast": forecast.set_index("driver_code"),
    }


def file_name(d: dict) -> str:
    return (
        event_folder(Path(""), d["season"], d["round"], d["circuit"]).as_posix().replace("/", "-")
        + ".md"
    )


def signed(v: float, unit: str = "s") -> str:
    return f"{v:+.3f} {unit}"


def quali_text(item: dict) -> list[str]:
    if item["gap_s"] is None and "problem" not in item:
        return [f"- {item['driver']} ★ set the fastest lap."]
    if "problem" in item:
        return [f"- {item['driver']} ★: {item['problem']}."]
    split = item["split"].set_index("kind")
    lost = split[split["seconds"] > 0].sort_values("seconds", ascending=False)
    gained = split[split["seconds"] < 0].sort_values("seconds")
    lines = [
        f"- **{item['driver']} ★ was {item['gap_s']:.3f} s slower than {item['ref']}.**",
        "",
        "  | part of the track | share of the lap | time lost (+) or gained (-) |",
        "  |---|---|---|",
    ]
    for kind, r in split.iterrows():
        lines.append(f"  | {kind} | {r['share_of_lap']:.0%} | {signed(r['seconds'])} |")
    lines.append("")
    if len(lost):
        lines.append(
            f"  Most lost: {lost.index[0]} ({signed(lost['seconds'].iloc[0])})"
            + (
                f"; most gained: {gained.index[0]} ({signed(gained['seconds'].iloc[0])})."
                if len(gained)
                else "."
            )
        )
    return lines


def race_text(item: dict, leader: str) -> list[str]:
    if "parts" not in item:
        why = item.get("problem", "he had the best race pace")
        return [f"- {item['driver']} ★: {why}."]
    parts = item["parts"].set_index("part")
    lines = [
        (
            f"- **{item['driver']} ★ was {item['mean_gap_s']:.3f} s a lap slower than {leader}** "
            f"on {item['laps']} laps where both were clean (in traffic on "
            f"{item['traffic_share']:.0%} of them)."
        ),
        "",
        "  | part | seconds per lap | 80% range |",
        "  |---|---|---|",
    ]
    for part, r in parts.iterrows():
        if pd.isna(r["seconds_per_lap"]):
            lines.append(f"  | {PART_NAMES[part]} | never different: inside pace | - |")
        else:
            lines.append(
                f"  | {PART_NAMES[part]} | {r['seconds_per_lap']:+.3f} | "
                f"{r['low']:+.3f} to {r['high']:+.3f} |"
            )
    return lines


def forecast_text(d: dict) -> list[str]:
    if d["forecast"].empty:
        return ["No forecast for this race (2022, a wet race, or no backtest yet)."]
    lines = [f"Forecast after qualifying, {d['forecast_source']}:", ""]
    for item in d["race"]:
        code = item["driver"]
        if code not in d["forecast"].index:
            continue
        f = d["forecast"].loc[code]
        actual = item["actual_gap_pct"]
        inside = (
            "no range"
            if pd.isna(f["low"])
            else (
                "inside the 80% range"
                if f["low"] <= actual <= f["high"]
                else "outside the 80% range"
            )
        )
        line = (
            f"- {code} ★: forecast {f['predicted']:+.2f}%, race {actual:+.2f}% "
            f"({actual - f['predicted']:+.2f}% against the forecast, {inside})."
        )
        if "parts" in item:
            others = item["parts"].set_index("part").drop(index="pace")["seconds_per_lap"].dropna()
            biggest = others.idxmax() if len(others) else None
            if biggest and others[biggest] > 0:
                line += (
                    f" The biggest part of his gap that wasn't pace: {PART_NAMES[biggest]}, "
                    f"{others[biggest]:+.3f} s a lap."
                )
        lines.append(line)
    return lines


LIMITS = """## 4. What this can't see

- Fuel loads, setups, engine modes and tyre temperatures are not public. Pairing the same lap
  numbers cancels the fuel both cars burn, not a difference in the fuel they started with.
- 'Traffic' = within 1.5 s of any car at the line; it can't tell a fight from a car that was
  simply close.
- On few laps, or when tyre age and compound change together, the parts' ranges are wide:
  read the ranges, not only the numbers."""


def to_markdown(d: dict) -> str:
    sections = [
        f"# Debrief · {d['season']} round {d['round']} · {d['circuit']}",
        (
            f"Where our cars' time went ({d['team']}, ★). Every number is measured; nothing "
            "here is written by an AI."
        ),
        "## 1. Qualifying: best lap against the fastest lap\n\n"
        + "\n".join(line for item in d["quali"] for line in quali_text(item) + [""]),
        f"## 2. Race: the gap to the best race pace ({d['leader'] or '-'})\n\n"
        + "\n".join(line for item in d["race"] for line in race_text(item, d["leader"]) + [""]),
        "## 3. Against the forecast\n\n" + "\n".join(forecast_text(d)),
        LIMITS,
    ]
    return "\n\n".join(sections) + "\n"
