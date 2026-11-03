"""The race engineer (step D2, decision 0017): one model, eight read-only tools, strict rules.

ask() is the whole loop: send the question, run the tools the model asks for, send their
results back, and repeat until the model answers in words (or hits the tool call limit).
"""

import time
from dataclasses import dataclass, field

from dpec.assistant.chat import Chat, Output, open_chat
from dpec.assistant.tools import TOOLS, run_tool
from telemetry_core.config import Settings

SYSTEM = """You are the race engineer on Team {team}'s pit wall. Team {team} runs the two \
{adopted} cars ("our cars"). You answer questions about Formula 1 sessions from {first} to \
{last} for engineers in a hurry.

Rules:
1. Every number you give comes from a tool result in this conversation. Never use numbers \
you remember from elsewhere. If the tools can't answer, say what is missing in one sentence.
2. Some things no public data shows: fuel loads, battery and ERS use, car setups (wings, \
ride height), tyre temperatures and pressures, active aero modes, and the content of team \
radio. If asked for one, answer "not public" with one sentence on why, and don't estimate it.
3. Forecasts are estimates: always give the 80% range with the number, e.g. \
"+0.42% (80% range -0.10 to +0.95)".
4. After each number, name the tool it came from in brackets, e.g. [sql] or [forecast].
5. Lead with the answer. At most five sentences, or a small table.

Units: lap times in seconds with 3 decimals; race pace gaps in % behind the best race pace \
with 2 decimals; tyre wear in seconds per lap. Drivers are three-letter codes (VER, HAM). \
Rounds are numbered within a season. When unsure which table holds something, call \
`tables` first."""


@dataclass
class Answer:
    question: str
    text: str
    provider: str
    model: str
    calls: list[dict] = field(default_factory=list)  # name, args, ok: what it looked up
    tokens_in: int = 0
    tokens_out: int = 0
    cached_in: int = 0
    seconds: float = 0.0


def system_prompt(s: Settings) -> str:
    return SYSTEM.format(
        team=s.team_name, adopted=s.adopted_team, first=min(s.seasons), last=max(s.seasons)
    )


def ask(
    question: str, s: Settings, provider: str | None = None, chat: Chat | None = None
) -> Answer:
    """One question, answered with the tools. chat: a ready conversation (tests pass one)."""
    start = time.perf_counter()
    chat = chat or open_chat(s, system_prompt(s), list(TOOLS.values()), provider)
    answer = Answer(question, "", chat.provider, chat.model)
    turn = chat.ask(question)
    while True:
        answer.tokens_in += turn.tokens_in
        answer.tokens_out += turn.tokens_out
        answer.cached_in += turn.cached_in
        if turn.stop != "tool" or not turn.calls:
            break
        if len(answer.calls) + len(turn.calls) > s.assistant.max_tool_calls:
            turn.text = (
                f"I stopped: this needs more than {s.assistant.max_tool_calls} tool calls. "
                "Try a narrower question."
            )
            break
        outputs = []
        for call in turn.calls:
            content, ok = run_tool(s, call.name, call.args)
            outputs.append(Output(call, content, ok))
            answer.calls.append({"name": call.name, "args": call.args, "ok": ok})
        turn = chat.answer(outputs)
    if turn.stop == "declined":
        turn.text = "The model declined to answer this question."
    elif turn.stop == "limit":
        turn.text += "\n(cut off: the answer got too long)"
    answer.text = turn.text.strip()
    answer.seconds = round(time.perf_counter() - start, 1)
    return answer
