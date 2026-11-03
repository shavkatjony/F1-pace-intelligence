"""The race engineer's tools (step D2): small read-only functions the model can call.

The model never touches the warehouse itself. It asks for a tool by name with arguments,
run_tool() runs it here and hands back JSON. Every number in an answer has to come from one
of these results: the system prompt says so, and the eval checks the numbers.
"""

import json
import re
import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

import duckdb
import pandas as pd

from dpec.api.routes.record import weekend_row
from dpec.debrief.attribution import attribute, paired_laps
from dpec.debrief.report import BEST_LAPS_SQL, PART_NAMES
from dpec.debrief.segments import lap_gap
from dpec.decisions.packet import our_lineage
from dpec.record.ledger import LEDGER, Forecast, read
from telemetry_core.config import Settings
from telemetry_core.warehouse import query

MAX_ROWS = 50  # rows the sql tool returns at most: the model reads every one
TIMEOUT_S = 10  # a query running longer than that is stopped
MAX_TEXT = 20_000  # characters of one tool result the model gets at most

TABLES = {  # what one row is; the model calls `tables` to see these
    "mart_weekends": "one race weekend: winner, pole, race laps, safety cars, wet or dry",
    "mart_driver_session_pace": "one driver in one session: clean laps, best and median lap, "
    "gap to the best (%)",
    "mart_weekend_signals": "one driver at one weekend: practice, qualifying and race pace "
    "gaps (%), grid, finish, points",
    "mart_long_runs": "one practice long run: tyre, laps, median lap, tyre wear per lap",
    "mart_stints": "one stint of one driver in one session: tyre, laps, wear per lap",
    "mart_race_strategy": "one race: practice and race tyre wear, pit loss, stops",
    "mart_session_weather": "one session: air and track temperature, humidity, rain",
    "mart_track_evolution": "one session: how much faster the track got",
    "mart_standings": "one driver after one round: points, wins, championship position",
    "core_results": "one driver in one session: official classification, grid, points, team",
    "core_laps": "one lap: time, sectors, tyre, speed trap, is_clean",
    "core_sessions": "one session: name, type, start time, circuit",
    "dim_drivers": "one driver in one season: name, car numbers, teams",
    "dim_teams": "one team name: its lineage (the same team across renames)",
    "forecasts": "one forecaster's race pace forecast for one driver at one weekend and "
    "checkpoint (walk-forward backtest, 2023 on): predicted, low, high (80% range), actual "
    "(all in % behind the best race pace), p_best, p_top3, p_beats_teammate",
    "decisions": "one past dry race's replayed tyre and stop decision: deg (wear forecast, "
    "s/lap), stops, p_best, clear, window_first/window_last (first stop laps), useful_life, "
    "pit_loss_s, and what happened: actual_deg, actual_stops, inside_window",
}
SAVED = {"forecasts": "backtest.parquet", "decisions": "decisions.parquet"}  # in data/forecasts
FILE_READERS = re.compile(r"\b(read_\w+|\w+_scan|glob|sniff_csv)\s*\(", re.IGNORECASE)

SEASON = {"type": "integer", "description": "year, e.g. 2024"}
ROUND = {"type": "integer", "description": "round number within the season (1 = first race)"}
DRIVER = {"type": "string", "description": "three-letter driver code, e.g. VER"}
SESSION = {"type": "string", "description": "Q (default), SQ, FP1, FP2, FP3, S or R"}
CHECKPOINT = {
    "type": "string",
    "enum": ["after_practice", "after_quali"],
    "description": "when the forecast was made (default after_quali)",
}


@dataclass
class Tool:
    name: str
    description: str
    run: Callable[..., dict]
    params: dict = field(default_factory=dict)  # JSON Schema of each argument
    required: list[str] = field(default_factory=list)

    def schema(self) -> dict:
        return {
            "type": "object",
            "properties": self.params,
            "required": self.required,
            "additionalProperties": False,
        }


def records(table: pd.DataFrame) -> list[dict]:
    """Rows as JSON-ready dicts, numbers rounded to 4 decimals (fewer tokens, same meaning)."""
    return json.loads(table.round(4).to_json(orient="records", date_format="iso"))


def connect(s: Settings) -> duckdb.DuckDBPyConnection:
    """A read-only connection with the saved forecasts as two more tables, if they exist."""
    con = duckdb.connect(str(s.paths.warehouse), read_only=True)
    for name, file in SAVED.items():
        path = s.paths.data / "forecasts" / file
        if path.exists():
            con.register(name, pd.read_parquet(path))
    return con


def check_sql(con: duckdb.DuckDBPyConnection, sql: str) -> str | None:
    """Why this query isn't allowed, or None if it is. Allowed: one SELECT (or WITH ... SELECT)
    statement that reads only the tables in TABLES and no files."""
    if not sql.lstrip().upper().startswith(("SELECT", "WITH")):
        return "only SELECT (or WITH ... SELECT) is allowed"
    if FILE_READERS.search(sql):
        return "reading files is not allowed: use the tables"
    try:
        if len(con.extract_statements(sql)) != 1:
            return "send exactly one statement"
        unknown = con.get_table_names(sql) - set(TABLES)
    except duckdb.Error as error:
        return f"not valid SQL: {error}"
    if unknown:
        return f"unknown table(s) {sorted(unknown)}: call `tables` to see the ones you can use"
    return None


def run_sql(s: Settings, query: str) -> dict:
    with connect(s) as con:
        problem = check_sql(con, query)
        if problem:
            return {"error": problem}
        timer = threading.Timer(TIMEOUT_S, con.interrupt)
        timer.start()
        try:
            sql = query.strip().rstrip(";")
            table = con.execute(f"SELECT * FROM (\n{sql}\n) LIMIT {MAX_ROWS + 1}").df()
        except duckdb.Error as error:
            return {"error": str(error).splitlines()[0][:300]}
        finally:
            timer.cancel()
    return {"rows": records(table.head(MAX_ROWS)), "truncated": len(table) > MAX_ROWS}


def dictionary_section(dictionary: Path, table: str) -> str:
    """The data dictionary's part for one table: its heading line to the next one."""
    text = dictionary.read_text() if dictionary.exists() else ""
    found = re.search(
        rf"^## `?{re.escape(table)}`?\n(.*?)(?=^## |\Z)", text, re.MULTILINE | re.DOTALL
    )
    return found.group(1).strip() if found else ""


def tables(s: Settings, table: str | None = None) -> dict:
    with connect(s) as con:
        columns = dict(
            con.execute(
                """
                SELECT table_name, string_agg(column_name, ', ' ORDER BY ordinal_position)
                FROM information_schema.columns GROUP BY table_name
                """
            ).fetchall()
        )
    if table is None:
        return {
            name: {"one_row_is": meaning, "columns": columns[name]}
            for name, meaning in TABLES.items()
            if name in columns
        }
    if table not in TABLES or table not in columns:
        return {"error": f"no table {table!r}: call `tables` with no argument for the list"}
    meaning = dictionary_section(s.paths.dictionary, table) or TABLES[table]
    return {"table": table, "columns": columns[table], "dictionary": meaning}


def key(season: int, round_no: int, session: str) -> str:
    return f"{season}_{round_no:02d}_{session}"


def lap_split(s: Settings, season: int, round_no: int, a: str, b: str, session: str = "Q") -> dict:
    """A's best clean lap of the session against B's, split by part of the track."""
    a, b = a.upper(), b.upper()
    best = query(s.paths.warehouse, BEST_LAPS_SQL, [key(season, round_no, session)])
    laps = dict(zip(best["driver_code"], best["lap_number"], strict=True))
    missing = [d for d in (a, b) if d not in laps]
    if missing:
        return {"error": f"no clean lap for {missing} in {key(season, round_no, session)}"}
    try:
        split, official, _ = lap_gap(
            s.paths.warehouse,
            s.paths.raw,
            key(season, round_no, session),
            (b, int(laps[b])),
            (a, int(laps[a])),
        )
    except (ValueError, duckdb.IOException):
        return {"error": f"no telemetry saved for {key(season, round_no, session)}"}
    worst = split.sort_values("seconds").iloc[-1]
    return {
        "lap_gap_s": round(official, 3),
        "meaning": f"seconds {a} loses to {b} (+) or gains (-) in each kind of section",
        "parts": records(split),
        "biggest_loss": {"kind": worst["kind"], "seconds": round(float(worst["seconds"]), 3)},
    }


def race_gap(s: Settings, season: int, round_no: int, a: str, b: str) -> dict:
    """A's race gap to B per lap, split into pace, tyres and traffic, with 80% ranges."""
    laps = paired_laps(s.paths.warehouse, key(season, round_no, "R"), a, b)
    parts = attribute(laps).set_index("part")  # ValueError if too few laps: becomes an error
    not_pace = parts.drop("pace")["seconds_per_lap"].abs().dropna()
    return {
        "laps_compared": len(laps),
        "mean_gap_s_per_lap": round(float(laps["gap_s"].mean()), 3),
        "a_in_traffic_share": round(float(laps["a_in_traffic"].mean()), 3),
        "parts": {p: {"what": PART_NAMES[p], **records(parts.loc[[p]])[0]} for p in parts.index},
        "biggest_part_not_pace": PART_NAMES[not_pace.idxmax()] if len(not_pace) else None,
        "note": "a part of null was never different between the two (it's inside pace); "
        "these are associations, not proven causes",
    }


def ledger_file(season: int, round_no: int, name: str) -> Path | None:
    folders = sorted((LEDGER / str(season)).glob(f"{round_no:02d}-*"))
    path = folders[0] / name if folders else None
    return path if path and path.exists() else None


def forecast(s: Settings, season: int, round_no: int, checkpoint: str = "after_quali") -> dict:
    """The race pace forecast for one weekend: the frozen one if there is one, else the
    backtest's."""
    lineage = our_lineage(s.paths.warehouse, s.adopted_team)
    frozen = ledger_file(season, round_no, f"{checkpoint}.json")
    if frozen:
        f = read(frozen)
        assert isinstance(f, Forecast)
        drivers = [d.model_dump(exclude={"baselines"}) for d in f.drivers]
        return {"source": "frozen in the public record before the session", "drivers": drivers}
    path = s.paths.data / "forecasts" / "backtest.parquet"
    if not path.exists():
        return {"error": "no forecasts saved: run `uv run dpec backtest`"}
    bt = pd.read_parquet(path)
    rows = bt[
        (bt["forecaster"] == "shared_model")
        & (bt["season"] == season)
        & (bt["round"] == round_no)
        & (bt["checkpoint"] == checkpoint)
    ].sort_values("predicted")
    if rows.empty:
        return {
            "error": f"no forecast for {season} round {round_no} (forecasts start in 2023; "
            "wet races are not forecast)"
        }
    rows = rows.assign(ours=rows["lineage"] == lineage)
    columns = ["driver_code", "ours", "predicted", "low", "high", "actual"]
    columns += ["p_best", "p_top3", "p_beats_teammate"]
    return {
        "source": "walk-forward backtest (made from earlier races only)",
        "units": "% behind the best race pace; low-high = 80% range",
        "drivers": records(rows[columns]),
    }


def tyre_decision(s: Settings, season: int, round_no: int) -> dict:
    frozen = ledger_file(season, round_no, "after_quali.json")
    if frozen:
        f = read(frozen)
        assert isinstance(f, Forecast)
        if f.decision:
            return {"source": "frozen in the public record", **f.decision.model_dump()}
    path = s.paths.data / "forecasts" / "decisions.parquet"
    if not path.exists():
        return {"error": "no decisions saved: run `uv run dpec replay`"}
    d = pd.read_parquet(path)
    row = d[(d["season"] == season) & (d["round"] == round_no)]
    if row.empty:
        return {"error": f"no decision for {season} round {round_no} (dry races from 2023 only)"}
    return {"source": "replay (made from earlier races only)", **records(row)[0]}


def public_record(s: Settings) -> dict:
    rows = [r for r in map(weekend_row, sorted(LEDGER.glob("*/*"))) if r]
    return {"weekends": rows, "note": None if rows else "nothing frozen yet"}


def data_status(s: Settings) -> dict:
    found = query(
        s.paths.warehouse,
        """
        SELECT min(season) AS first_season, max(season) AS last_season,
            count(DISTINCT season * 100 + round) AS weekends, count(*) AS sessions,
            max(session_date_utc) AS latest_session_utc,
            arg_max(event_name, session_date_utc) AS latest_event
        FROM core_sessions
        """,
    )
    no_race = query(
        s.paths.warehouse,
        """
        SELECT season, round, any_value(event_name) AS event_name FROM core_sessions
        GROUP BY season, round HAVING NOT bool_or(session_type = 'R')
        """,
    )
    return {**records(found)[0], "weekends_without_race": records(no_race)}


TOOLS = {
    t.name: t
    for t in [
        Tool(
            "tables",
            "List the tables `sql` can read, with what one row is and their columns. "
            "With `table`: that table's columns explained (units, rules).",
            tables,
            {"table": {"type": "string", "description": "one table name"}},
        ),
        Tool(
            "sql",
            f"Run one read-only DuckDB SELECT on the tables `tables` lists. At most {MAX_ROWS} "
            "rows come back. Session keys look like 2024_01_Q (season, round, session type: "
            "FP1 FP2 FP3 SQ S Q R).",
            run_sql,
            {"query": {"type": "string", "description": "one SELECT statement"}},
            ["query"],
        ),
        Tool(
            "lap_split",
            "Driver A's best clean lap of a session against driver B's, split by part of the "
            "track (straights, braking, slow/medium/fast corners, traction). Needs telemetry.",
            lap_split,
            {"season": SEASON, "round_no": ROUND, "a": DRIVER, "b": DRIVER, "session": SESSION},
            ["season", "round_no", "a", "b"],
        ),
        Tool(
            "race_gap",
            "Driver A's race lap time gap to driver B, lap by lap, split into pace on equal "
            "tyres in clean air, tyre age, tyre compound and traffic, with 80% ranges.",
            race_gap,
            {"season": SEASON, "round_no": ROUND, "a": DRIVER, "b": DRIVER},
            ["season", "round_no", "a", "b"],
        ),
        Tool(
            "forecast",
            "The race pace forecast for one weekend, every driver: predicted gap, 80% range, "
            "chances, and the actual gap once the race is over. Our cars have ours=true.",
            forecast,
            {"season": SEASON, "round_no": ROUND, "checkpoint": CHECKPOINT},
            ["season", "round_no"],
        ),
        Tool(
            "tyre_decision",
            "The tyre and stop decision for one race: wear forecast, stops, how clear the call "
            "was, first stop window, and what happened.",
            tyre_decision,
            {"season": SEASON, "round_no": ROUND},
            ["season", "round_no"],
        ),
        Tool(
            "public_record",
            "Every weekend frozen in the public record (ledger/): when it was frozen, the "
            "call, and its score once the race is over.",
            public_record,
        ),
        Tool(
            "data_status",
            "What the warehouse holds: seasons, weekends, sessions, the latest session saved, "
            "and weekends whose race isn't saved yet.",
            data_status,
        ),
    ]
}


def run_tool(s: Settings, name: str, args: dict) -> tuple[str, bool]:
    """Run one tool call; return (JSON text for the model, did it work). A failure goes back
    to the model as an error message, so it can say what's missing instead of guessing."""
    tool = TOOLS.get(name)
    if tool is None:
        result = {"error": f"no tool called {name!r}"}
    else:
        try:
            result = tool.run(s, **args)
        except TypeError as error:  # missing or unknown arguments
            result = {"error": f"wrong arguments for {name}: {error}"}
        except Exception as error:  # noqa: BLE001 (any failure is reported, not raised)
            result = {"error": f"{type(error).__name__}: {str(error)[:300]}"}
    text = json.dumps(result, default=str)
    if len(text) > MAX_TEXT:
        text = text[:MAX_TEXT] + " ... (cut: ask for less)"
    return text, "error" not in result
