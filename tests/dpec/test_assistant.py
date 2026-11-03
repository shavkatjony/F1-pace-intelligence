"""Race engineer tests (step D2): the SQL guard, the tool loop, both providers' message formats
(against stand-in servers, so no key and no Ollama needed) and the exam's grader."""

import json
from collections import Counter
from pathlib import Path

import anthropic
import duckdb
import httpx
import httpx2
import pandas as pd
import pytest

from dpec.assistant.chat import Call, ProviderError, ScriptedChat, Turn
from dpec.assistant.claude import ClaudeChat
from dpec.assistant.engineer import ask
from dpec.assistant.evals import (
    check_passes,
    compare_runs,
    cost_usd,
    grade,
    load_questions,
    numbers_in,
    summary,
)
from dpec.assistant.ollama import OllamaChat
from dpec.assistant.tools import MAX_ROWS, TOOLS, check_sql, run_tool
from telemetry_core.config import load_settings


@pytest.fixture
def s(tmp_path):
    """Settings with a tiny warehouse: one table, 60 rows."""
    warehouse = tmp_path / "wh.duckdb"
    with duckdb.connect(str(warehouse)) as con:
        con.execute(
            "CREATE TABLE mart_weekends AS SELECT 2024 AS season, range + 1 AS round, "
            "'VER' AS winner FROM range(60)"
        )
    settings = load_settings("config/dpec.yaml")
    paths = settings.paths.model_copy(update={"warehouse": warehouse, "data": tmp_path})
    return settings.model_copy(update={"paths": paths})


def test_only_one_select_on_known_tables_is_allowed():
    con = duckdb.connect()
    con.execute("CREATE TABLE mart_weekends (season INT, winner TEXT)")
    assert check_sql(con, "SELECT winner FROM mart_weekends") is None
    assert check_sql(con, "WITH w AS (SELECT * FROM mart_weekends) SELECT * FROM w") is None
    assert "only SELECT" in check_sql(con, "DELETE FROM mart_weekends")
    assert "only SELECT" in check_sql(con, "PRAGMA version")
    assert check_sql(con, "SELECT 1; DROP TABLE mart_weekends") is not None
    assert "files" in check_sql(con, "SELECT * FROM read_csv('/etc/passwd')")
    assert "unknown" in check_sql(con, "SELECT * FROM '/etc/passwd'")
    assert "unknown" in check_sql(con, "SELECT * FROM secrets")


def test_sql_tool_returns_at_most_max_rows(s):
    text, ok = run_tool(s, "sql", {"query": "SELECT * FROM mart_weekends"})
    result = json.loads(text)
    assert ok
    assert len(result["rows"]) == MAX_ROWS
    assert result["truncated"]


def test_tool_problems_go_back_to_the_model_as_errors(s):
    for name, args in [
        ("nope", {}),
        ("sql", {}),  # missing argument
        ("sql", {"query": "DROP TABLE mart_weekends"}),
        ("forecast", {"season": 2024, "round_no": 1}),  # no forecasts saved
    ]:
        text, ok = run_tool(s, name, args)
        assert not ok
        assert "error" in json.loads(text)


def test_every_tool_has_a_valid_schema():
    for tool in TOOLS.values():
        schema = tool.schema()
        assert set(schema["required"]) <= set(schema["properties"])
        assert tool.description.endswith(".")


def sql_call(query: str) -> Turn:
    return Turn("", [Call("t1", "sql", {"query": query})], stop="tool", tokens_in=100)


def test_engineer_runs_the_tools_and_returns_the_final_answer(s):
    chat = ScriptedChat(
        [
            sql_call("SELECT winner FROM mart_weekends WHERE round = 1"),
            Turn("VER [sql].", tokens_in=150),
        ]
    )
    a = ask("Who won round 1?", s, chat=chat)
    assert a.text == "VER [sql]."
    assert a.calls == [{"name": "sql", "args": chat.received[1][0].call.args, "ok": True}]
    assert '"winner": "VER"' in chat.received[1][0].content  # the tool result went back
    assert a.tokens_in == 250


def test_engineer_stops_after_the_tool_call_limit(s):
    s = s.model_copy(update={"assistant": s.assistant.model_copy(update={"max_tool_calls": 2})})
    chat = ScriptedChat([sql_call("SELECT 1 FROM mart_weekends")] * 5)
    a = ask("Loop forever", s, chat=chat)
    assert len(a.calls) == 2
    assert a.text.startswith("I stopped")


def test_a_declined_question_says_so(s):
    a = ask("?", s, chat=ScriptedChat([Turn("", stop="declined")]))
    assert a.text == "The model declined to answer this question."


def claude_reply(content, stop):
    return {
        "id": "msg_1",
        "type": "message",
        "role": "assistant",
        "model": "claude-opus-5-5",
        "content": content,
        "stop_reason": stop,
        "stop_sequence": None,
        "usage": {"input_tokens": 1000, "output_tokens": 50, "cache_read_input_tokens": 800},
    }


def test_claude_gets_the_tools_and_its_own_turn_back_unchanged(s, monkeypatch):
    sent = []

    def server(request):
        sent.append((request.headers, json.loads(request.content)))
        if len(sent) == 1:
            query = {"query": "SELECT winner FROM mart_weekends WHERE round = 1"}
            content = [
                {"type": "thinking", "thinking": "", "signature": "abc"},
                {"type": "tool_use", "id": "toolu_1", "name": "sql", "input": query},
            ]
            return httpx2.Response(200, json=claude_reply(content, "tool_use"))
        return httpx2.Response(
            200, json=claude_reply([{"type": "text", "text": "VER"}], "end_turn")
        )

    client = anthropic.Anthropic(
        api_key="test",
        http_client=anthropic.DefaultHttpxClient(transport=httpx2.MockTransport(server)),
    )
    chat = ClaudeChat("claude-opus-5-5", "medium", "system", list(TOOLS.values()), client=client)
    a = ask("Who won round 1?", s, chat=chat)
    assert a.text == "VER"
    headers, first = sent[0]
    assert [t["name"] for t in first["tools"]] == list(TOOLS)
    assert first["fallbacks"] == "default"
    assert "server-side-fallback" in headers["anthropic-beta"]
    second = sent[1][1]["messages"]
    assert second[1]["content"][0] == {"type": "thinking", "thinking": "", "signature": "abc"}
    assert second[2]["content"][0]["tool_use_id"] == "toolu_1"
    assert a.cached_in == 1600

    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)  # no key: a clear message, no traceback
    with pytest.raises(ProviderError, match="no Claude API key"):
        ClaudeChat("claude-opus-5-5", "medium", "system", [])


def test_ollama_round_trip_and_a_clear_error_when_it_is_off(s):
    sent = []

    def server(request):
        sent.append(json.loads(request.content))
        if len(sent) == 1:
            call = {
                "function": {
                    "name": "sql",
                    "arguments": {"query": "SELECT 1 AS x FROM mart_weekends"},
                }
            }
            return httpx.Response(
                200, json={"message": {"role": "assistant", "content": "", "tool_calls": [call]}}
            )
        return httpx.Response(
            200, json={"message": {"role": "assistant", "content": "<think>…</think>Done."}}
        )

    client = httpx.Client(base_url="http://test", transport=httpx.MockTransport(server))
    a = ask(
        "?", s, chat=OllamaChat("qwen3:8b", "http://test", "system", list(TOOLS.values()), client)
    )
    assert a.text == "Done."
    assert sent[1]["messages"][-1]["role"] == "tool"

    def off(request):
        raise httpx.ConnectError("refused")

    down = httpx.Client(base_url="http://test", transport=httpx.MockTransport(off))
    with pytest.raises(ProviderError, match="isn't running"):
        OllamaChat("qwen3:8b", "http://test", "system", [], down).ask("?")


def test_numbers_are_read_like_a_person_would():
    assert numbers_in("1:31.447, then +0.42% and 75%") == [91.447, 0.42, 0.0042, 75.0, 0.75]


def test_check_rules():
    assert check_passes("VER", "VER won it")
    assert not check_passes("VER", "HAM never led")  # 'ver' inside 'never' doesn't count
    assert check_passes(89.179, "a 1:29.179 lap")
    assert check_passes(-0.2, "it got 0.2 s faster")  # signs are ignored
    assert not check_passes(0.548, "about 0.6%")
    assert check_passes(0, "No laps behind the safety car")
    assert check_passes(["not public"], "That's not public: teams don't publish fuel.")


def test_grade_needs_every_check():
    q = {"expect": [{"sql": "..."}, {"sql": "...", "tol": 0.005}]}
    assert grade(q, ["LEC", 0.014], "LEC was faster by 0.014 s")[0]
    assert not grade(q, ["LEC", 0.014], "LEC was faster by 0.1 s")[0]


def test_the_exam_has_50_questions_of_five_kinds():
    questions = load_questions()
    assert len({q["id"] for q in questions}) == len(questions) == 50
    kinds = Counter(q["kind"] for q in questions)
    assert kinds == {"lookup": 18, "comparison": 12, "forecast": 8, "decision": 7, "trap": 5}
    for q in questions:
        assert q["expect"] and all({"sql", "tool", "says_any"} & set(c) for c in q["expect"])


def test_summary_cost_and_comparison(tmp_path):
    runs = pd.DataFrame(
        {
            "id": ["L01", "T01"],
            "kind": ["lookup", "trap"],
            "passed": [True, False],
            "tools": ["sql", ""],
            "tokens_in": [3_000_000, 1_000_000],
            "cached_in": [2_000_000, 0],
            "tokens_out": [100_000, 50_000],
            "seconds": [4.0, 2.0],
            "provider": "claude",
            "model": "claude-opus-5-5",
        }
    )
    assert summary(runs).loc["all", "passed"] == 0.5
    # (1M + 0.1 x 2M + 1M) x $4 + 150k x $20 = $8.80 + $3.00
    assert cost_usd(runs) == pytest.approx(11.8)
    runs.to_csv(tmp_path / "eval-claude-claude-opus-5-5-2026-10-27.csv", index=False)
    table = compare_runs(Path(tmp_path))
    assert "| claude-claude-opus-5-5-2026-10-27 | 50% | 100% |" in table
