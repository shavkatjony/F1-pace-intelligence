"""The race engineer's exam (decision 0017): 50 questions whose answers the warehouse knows.

Each question's right answer is computed fresh by its checks, so the exam stays right when
new races arrive. A question passes when every one of its checks passes:
    sql:      the first value this query returns must be in the answer
    tool:     run a tool with `args` and take one `field` of its result (a.b.c for nested)
    says_any: at least one of these phrases must be in the answer (trap questions)
Numbers match within `tol` (default 0.01) and their signs are ignored: the questions check
direction with words (who was faster), not with + and -.
"""

import json
import re
from datetime import date
from decimal import Decimal
from pathlib import Path

import pandas as pd
import yaml

from dpec.assistant.engineer import ask
from dpec.assistant.tools import connect, run_tool
from telemetry_core.config import Settings

QUESTIONS = Path("evals/questions.yaml")
REPORTS = Path("reports/ai")
KINDS = ["lookup", "comparison", "forecast", "decision", "trap"]
PRICES = {  # US$ per million tokens (input, output): Anthropic's list prices on 2026-10-27
    "claude-opus-5-5": (4.00, 20.00),
    "claude-sonnet-5-5": (2.00, 10.00),
    "claude-haiku-5-5": (0.10, 0.50),
}
CACHED = 0.1  # a token read from the cache costs a tenth of a normal input token
NUMBER = re.compile(r"(\d+):(\d{2}\.\d+)|(\d+(?:\.\d+)?)\s*(%?)")


def load_questions(path: Path = QUESTIONS) -> list[dict]:
    return yaml.safe_load(Path(path).read_text())


def expected(s: Settings, check: dict):
    """The right answer for one check, computed now."""
    if "sql" in check:
        with connect(s) as con:
            row = con.execute(check["sql"]).fetchone()
        value = row[0] if row else None
        return float(value) if isinstance(value, Decimal) else value
    if "tool" in check:
        result = json.loads(run_tool(s, check["tool"], check.get("args", {}))[0])
        for part in check["field"].split("."):
            result = result[part]
        return result
    return check["says_any"]


def numbers_in(text: str) -> list[float]:
    """Every number in the text; a lap time like 1:31.447 also counts as 91.447 seconds, and
    a percentage like 75% also as 0.75."""
    found = []
    for m in NUMBER.finditer(text):
        if m.group(1):
            found.append(int(m.group(1)) * 60 + float(m.group(2)))
        else:
            x = float(m.group(3))
            found.append(x)
            if m.group(4):
                found.append(x / 100)
    return found


def check_passes(value, text: str, tol: float = 0.01) -> bool:
    """Is the right answer `value` in the model's answer `text`?"""
    if isinstance(value, list):  # a trap question: one of these phrases
        return any(phrase.lower() in text.lower() for phrase in value)
    if isinstance(value, bool) or not isinstance(value, int | float):  # a word: VER, Sakhir
        return re.search(rf"\b{re.escape(str(value))}\b", text, re.IGNORECASE) is not None
    if value == 0 and re.search(r"\b(no|none|zero)\b", text, re.IGNORECASE):
        return True
    return any(abs(abs(x) - abs(value)) <= tol for x in numbers_in(text))


def answer_key(s: Settings, questions: list[dict]) -> dict[str, list]:
    """Every question's right answers, computed once per exam."""
    return {q["id"]: [expected(s, check) for check in q["expect"]] for q in questions}


def grade(q: dict, values: list, text: str) -> tuple[bool, str]:
    misses = [
        f"wanted {value}"
        for check, value in zip(q["expect"], values, strict=True)
        if not check_passes(value, text, check.get("tol", 0.01))
    ]
    return not misses, "; ".join(misses)


def run_eval(
    s: Settings, provider: str | None = None, only: list[str] | None = None
) -> pd.DataFrame:
    questions = [q for q in load_questions() if not only or q["id"] in only]
    key = answer_key(s, questions)
    rows = []
    for q in questions:
        a = ask(q["question"], s, provider)
        passed, misses = grade(q, key[q["id"]], a.text)
        print(f"{q['id']} {'pass' if passed else 'FAIL'} {a.seconds:5.1f}s {misses}")
        rows.append(
            {
                "id": q["id"],
                "kind": q["kind"],
                "passed": passed,
                "misses": misses,
                "answer": a.text,
                "tools": " ".join(c["name"] for c in a.calls),
                "failed_calls": sum(not c["ok"] for c in a.calls),
                "tokens_in": a.tokens_in,
                "tokens_out": a.tokens_out,
                "cached_in": a.cached_in,
                "seconds": a.seconds,
                "provider": a.provider,
                "model": a.model,
            }
        )
    return pd.DataFrame(rows)


def cost_usd(results: pd.DataFrame) -> float | None:
    """What a run cost at list prices; None for a model with no price here (Ollama: free)."""
    price = PRICES.get(results["model"].iloc[0])
    if price is None:
        return None
    normal = results["tokens_in"] - results["cached_in"] + CACHED * results["cached_in"]
    return float((normal.sum() * price[0] + results["tokens_out"].sum() * price[1]) / 1e6)


def summary(results: pd.DataFrame) -> pd.DataFrame:
    """Pass rate per kind of question, and for all 50."""
    by_kind = results.groupby("kind")["passed"].agg(["count", "mean"]).reindex(KINDS)
    by_kind.loc["all"] = [len(results), results["passed"].mean()]
    return by_kind.rename(columns={"count": "questions", "mean": "passed"}).dropna()


def save(results: pd.DataFrame) -> Path:
    REPORTS.mkdir(parents=True, exist_ok=True)
    model = results["model"].iloc[0].replace(":", "-")
    path = REPORTS / f"eval-{results['provider'].iloc[0]}-{model}-{date.today()}.csv"
    results.to_csv(path, index=False)
    return path


def compare_runs(folder: Path = REPORTS) -> str:
    """Every saved run side by side, as a Markdown table (reports/ai/README.md)."""
    header = ["run", "all", *KINDS, "looked it up", "median s", "tokens", "cost $"]
    lines = ["| " + " | ".join(header) + " |", "|---" * len(header) + "|"]
    for path in sorted(folder.glob("eval-*.csv")):
        r = pd.read_csv(path, keep_default_na=False)
        rate = summary(r)["passed"]
        grounded = (r[r["kind"] != "trap"]["tools"] != "").mean()
        cost = cost_usd(r)
        cells = [path.stem.removeprefix("eval-")]
        cells += [f"{rate.get(k, float('nan')):.0%}" for k in ["all", *KINDS]]
        cells += [
            f"{grounded:.0%}",
            f"{r['seconds'].median():.0f}",
            f"{(r['tokens_in'] + r['tokens_out']).sum():,}",
            "free" if cost is None else f"{cost:.2f}",
        ]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)
