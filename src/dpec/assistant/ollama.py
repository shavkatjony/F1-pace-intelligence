"""The race engineer on a local model through Ollama (https://ollama.com): free, offline, and
nothing leaves the Mac. Once: install Ollama and `ollama pull qwen3:8b` (Lesson 19, Part 11).
"""

import json
import re

import httpx

from dpec.assistant.chat import Call, Output, ProviderError, Turn
from dpec.assistant.tools import Tool


class OllamaChat:
    provider = "ollama"

    def __init__(
        self,
        model: str,
        url: str,
        system: str,
        tools: list[Tool],
        client: httpx.Client | None = None,
    ):
        self.model, self.url = model, url
        self.client = client or httpx.Client(base_url=url, timeout=300)  # local models are slow
        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.schema(),
                },
            }
            for t in tools
        ]
        self.messages: list[dict] = [{"role": "system", "content": system}]
        self.n_calls = 0

    def ask(self, text: str) -> Turn:
        self.messages.append({"role": "user", "content": text})
        return self._send()

    def answer(self, outputs: list[Output]) -> Turn:
        for o in outputs:
            self.messages.append({"role": "tool", "tool_name": o.call.name, "content": o.content})
        return self._send()

    def _send(self) -> Turn:
        body = {
            "model": self.model,
            "messages": self.messages,
            "tools": self.tools,
            "stream": False,
            "options": {"temperature": 0},  # the same question gets the same answer
        }
        try:
            r = self.client.post("/api/chat", json=body)
        except httpx.ConnectError:
            raise ProviderError(
                f"Ollama isn't running at {self.url}: start the Ollama app"
            ) from None
        if r.status_code == 404:
            raise ProviderError(f"model {self.model} isn't downloaded: `ollama pull {self.model}`")
        r.raise_for_status()
        reply = r.json()
        message = reply["message"]
        self.messages.append(message)
        calls = []
        for c in message.get("tool_calls") or []:
            self.n_calls += 1
            args = c["function"].get("arguments") or {}
            if isinstance(args, str):  # some models send the arguments as JSON text
                args = json.loads(args)
            calls.append(Call(f"call_{self.n_calls}", c["function"]["name"], args))
        text = re.sub(r"<think>.*?</think>", "", message.get("content") or "", flags=re.DOTALL)
        return Turn(
            text=text.strip(),
            calls=calls,
            stop="tool" if calls else "end",
            tokens_in=reply.get("prompt_eval_count", 0),
            tokens_out=reply.get("eval_count", 0),
        )
