"""The race engineer on Claude, through Anthropic's Python SDK.

Needs an API key in the environment variable ANTHROPIC_API_KEY (Lesson 19, Part 2). The key
never goes in config/ or git: the SDK reads it from the environment by itself.
"""

import os

import anthropic

from dpec.assistant.chat import Call, Output, ProviderError, Turn
from dpec.assistant.tools import Tool

# Models that can hand a declined request to another model on Anthropic's side ("fallbacks").
FALLBACK_MODELS = {"claude-opus-5-5", "claude-opus-5", "claude-fable-5-1", "claude-sonnet-5-5"}
STOPS = {"tool_use": "tool", "max_tokens": "limit", "refusal": "declined"}


class ClaudeChat:
    provider = "claude"

    def __init__(
        self,
        model: str,
        effort: str,
        system: str,
        tools: list[Tool],
        client: anthropic.Anthropic | None = None,
    ):
        if client is None and not os.environ.get("ANTHROPIC_API_KEY"):
            raise ProviderError(
                "no Claude API key: run `export ANTHROPIC_API_KEY=...` first (Lesson 19, Part 2)"
            )
        self.client = client or anthropic.Anthropic()  # reads ANTHROPIC_API_KEY
        self.model, self.effort, self.system = model, effort, system
        self.tools = [
            {"name": t.name, "description": t.description, "input_schema": t.schema()}
            for t in tools
        ]
        self.messages: list[dict] = []

    def ask(self, text: str) -> Turn:
        self.messages.append({"role": "user", "content": text})
        return self._send()

    def answer(self, outputs: list[Output]) -> Turn:
        results = [
            {
                "type": "tool_result",
                "tool_use_id": o.call.id,
                "content": o.content,
                "is_error": not o.ok,
            }
            for o in outputs
        ]
        self.messages.append({"role": "user", "content": results})  # all results in one message
        return self._send()

    def _send(self) -> Turn:
        extra = {}
        if self.model in FALLBACK_MODELS:  # if this model declines, Anthropic tries another
            extra = {"betas": ["server-side-fallback-2026-07-01"], "fallbacks": "default"}
        try:
            response = self.client.beta.messages.create(
                model=self.model,
                max_tokens=16000,
                system=self.system,
                tools=self.tools,
                messages=self.messages,
                output_config={"effort": self.effort},
                cache_control={"type": "ephemeral"},  # reuse the prompt and tools between calls
                **extra,
            )
        except anthropic.APIStatusError as error:
            raise ProviderError(f"Claude API error {error.status_code}: {error.message}") from None
        except anthropic.APIConnectionError:
            raise ProviderError("can't reach the Claude API: check the internet") from None
        self.messages.append({"role": "assistant", "content": response.content})  # as it came
        u = response.usage
        cached = u.cache_read_input_tokens or 0
        blocks = response.content
        return Turn(
            text="\n".join(b.text for b in blocks if b.type == "text"),
            calls=[Call(b.id, b.name, dict(b.input)) for b in blocks if b.type == "tool_use"],
            stop=STOPS.get(response.stop_reason or "", "end"),
            tokens_in=u.input_tokens + cached + (u.cache_creation_input_tokens or 0),
            tokens_out=u.output_tokens,
            cached_in=cached,
        )
