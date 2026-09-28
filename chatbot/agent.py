"""The agent loop: model requests tools -> we run them -> feed results back."""
from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from typing import Any

from .tools import TOOLS, run_tool

DEFAULT_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
MAX_STEPS = 6          # max model calls per user turn (prevents infinite loops)
MAX_HISTORY = 30       # messages kept (excluding system prompt)

SYSTEM_PROMPT = (
    "You are a helpful assistant with tools: get_weather, calculate, search_web, "
    "query_database. Rules: use calculate for ANY arithmetic; use get_weather for "
    "weather; use query_database for questions about customers, products or orders; "
    "use search_web for current or unknown facts. For simple chat or general "
    "knowledge you already have, answer directly without tools. If a tool returns an "
    "error, fix your arguments and retry once, otherwise explain the problem. "
    "Base answers on tool results and be concise."
)


@dataclass
class ToolCall:
    name: str
    arguments: dict
    result: str
    seconds: float


@dataclass
class Turn:
    answer: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    steps: int = 0
    seconds: float = 0.0


class Agent:
    def __init__(self, model: str = DEFAULT_MODEL, client: Any = None):
        if client is None:
            import ollama
            client = ollama.Client()
        self.client, self.model = client, model
        self.history: list[dict] = []

    def reset(self) -> None:
        self.history = []

    def _trim(self) -> None:
        """Drop oldest messages, cutting only at a user message so tool pairs stay intact."""
        while len(self.history) > MAX_HISTORY:
            nxt = next((i for i in range(1, len(self.history))
                        if self.history[i]["role"] == "user"), None)
            if nxt is None:
                break
            self.history = self.history[nxt:]

    def run(self, user_input: str) -> Turn:
        start = time.time()
        self.history.append({"role": "user", "content": user_input})
        turn = Turn(answer="")
        for step in range(1, MAX_STEPS + 1):
            resp = self.client.chat(
                model=self.model, tools=TOOLS,
                messages=[{"role": "system", "content": SYSTEM_PROMPT}, *self.history])
            msg = resp.message
            calls = msg.tool_calls or []
            entry: dict[str, Any] = {"role": "assistant", "content": msg.content or ""}
            if calls:
                entry["tool_calls"] = [{"function": {"name": c.function.name,
                                                     "arguments": dict(c.function.arguments)}}
                                       for c in calls]
            self.history.append(entry)
            turn.steps = step
            if not calls:
                turn.answer = msg.content or ""
                break
            for c in calls:
                t0 = time.time()
                args = dict(c.function.arguments)
                result = run_tool(c.function.name, args)
                turn.tool_calls.append(ToolCall(c.function.name, args, result, time.time() - t0))
                self.history.append({"role": "tool", "content": result,
                                     "tool_name": c.function.name})
        else:
            turn.answer = "Sorry, I hit the tool-call limit before finishing. Try rephrasing."
            self.history.append({"role": "assistant", "content": turn.answer})
        turn.seconds = time.time() - start
        self._trim()
        return turn
