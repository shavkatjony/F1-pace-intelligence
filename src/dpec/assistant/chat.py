"""One conversation with a model, the same shape for every provider (decision 0017).

ask(text) sends the question; answer(outputs) sends tool results back. Both return a Turn:
the model's text and the tool calls it wants next. Each provider keeps its own history in its
own format, because Claude's history has to go back exactly as it came (thinking included).
"""

from dataclasses import dataclass, field
from typing import Protocol

from dpec.assistant.tools import Tool
from telemetry_core.config import Settings


class ProviderError(Exception):
    """The model can't be reached: no API key, Ollama not running, model not downloaded."""


@dataclass
class Call:
    id: str
    name: str
    args: dict


@dataclass
class Output:
    call: Call
    content: str  # the tool's JSON result
    ok: bool


@dataclass
class Turn:
    text: str
    calls: list[Call] = field(default_factory=list)
    stop: str = "end"  # end, tool (wants the calls run), limit (too long), declined
    tokens_in: int = 0
    tokens_out: int = 0
    cached_in: int = 0  # of tokens_in, read from the cache (cheaper)


class Chat(Protocol):
    provider: str
    model: str

    def ask(self, text: str) -> Turn: ...
    def answer(self, outputs: list[Output]) -> Turn: ...


class ScriptedChat:
    """A stand-in model for tests: plays back turns written in advance and keeps what it got."""

    provider, model = "scripted", "script"

    def __init__(self, turns: list[Turn]):
        self.turns = list(turns)
        self.received: list = []

    def ask(self, text: str) -> Turn:
        self.received.append(text)
        return self.turns.pop(0)

    def answer(self, outputs: list[Output]) -> Turn:
        self.received.append(outputs)
        return self.turns.pop(0)


def open_chat(s: Settings, system: str, tools: list[Tool], provider: str | None = None) -> Chat:
    """A new conversation with the provider in the settings (or the one asked for)."""
    a = s.assistant
    if (provider or a.provider) == "claude":
        from dpec.assistant.claude import ClaudeChat  # imported here: Ollama users need no key

        return ClaudeChat(a.claude_model, a.effort, system, tools)
    from dpec.assistant.ollama import OllamaChat

    return OllamaChat(a.ollama_model, a.ollama_url, system, tools)
