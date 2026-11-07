"""The warehouse: one DuckDB file built from plain SQL files.

build() runs every .sql file of a folder in name order, one table per file, with dbt-style
{{name}} placeholders. run_checks() runs the data checks in sql/checks, undocumented_columns()
compares the tables with the data dictionary, and query() runs one read-only query.
"""

# ==============================================================================================
# The data engineering layer: from the raw Parquet files to the tables every other part reads.
# ==============================================================================================

import re
from pathlib import Path

import duckdb
import pandas as pd


def render(sql: str, params: dict) -> str:
    """Fill {{name}} placeholders, the same style dbt uses."""
    for name, value in params.items():
        placeholder = re.compile(r"\{\{\s*" + re.escape(name) + r"\s*\}\}")
        replacement = str(value)
        sql = placeholder.sub(lambda _, replacement=replacement: replacement, sql)
    if "{{" in sql:
        raise ValueError(f"unfilled placeholder in SQL: {sql[sql.index('{{') :][:40]}")
    return sql


def build(sql_dir: Path, warehouse: Path, params: dict) -> dict[str, int]:
    """Run every .sql file in sql_dir in name order. Returns {table: rows}."""
    files = sorted(Path(sql_dir).glob("*.sql"))
    if not files:
        raise FileNotFoundError(f"no .sql files in {sql_dir}")
    Path(warehouse).parent.mkdir(parents=True, exist_ok=True)
    counts = {}
    with duckdb.connect(str(warehouse)) as con:
        for path in files:
            con.execute(render(path.read_text(), params))
            table = path.stem.split("_", 1)[1]  # 01_core_sessions -> core_sessions
            counts[table] = con.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
    return counts

def run_checks(checks_dir: Path, warehouse: Path, params: dict) -> list[dict]:
    """Run every check in checks_dir. A check is a query that returns the rows breaking a rule,
    so an empty result means the check passed."""
    results = []
    with duckdb.connect(str(warehouse), read_only=True) as con:
        for path in sorted(Path(checks_dir).glob("*.sql")):
            bad = con.execute(render(path.read_text(), params)).df()
            results.append({"name": path.stem, "n_bad": len(bad), "sample": bad.head(5)})
    return results


def undocumented_columns(warehouse: Path, dictionary: Path) -> list[str]:
    """Columns in the warehouse that the data dictionary doesn't describe, as 'table.column'.
    The dictionary has a '## table_name' heading per table and a '| `column` |' row per column."""
    documented, table = set(), None
    for line in Path(dictionary).read_text().splitlines():
        if line.startswith("## "):
            table = line[3:].strip().strip("`")
        elif table and line.startswith("| `"):
            documented.add(f"{table}.{line.split('`')[1]}")
    with duckdb.connect(str(warehouse), read_only=True) as con:
        columns = con.execute(
            "SELECT table_name || '.' || column_name FROM information_schema.columns"
        ).fetchall()
    return sorted(c for (c,) in columns if c not in documented)


def query(warehouse: Path, sql: str, params: list | None = None) -> pd.DataFrame:
    """Run one read-only query and return the result as a table.
    Each ? in the SQL is filled from params, in order (safe: values never become SQL text)."""
    with duckdb.connect(str(warehouse), read_only=True) as con:
        return con.execute(sql, params or []).df()



# finally done with with 1000 mg  ㅜaurin
