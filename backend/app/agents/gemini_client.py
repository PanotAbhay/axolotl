"""Gemini Interactions transport. No local tools execute inside the SDK."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

from app.agents.prompts import data_block
from app.config import get_settings


class ModelUnavailable(RuntimeError):
    """The configured model failed; never substitute a successful outcome."""


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: Any


@dataclass
class Turn:
    id: str
    text: str = ""
    calls: list[ToolCall] = field(default_factory=list)


def parse_turn(response: Any) -> Turn:
    data = response if isinstance(response, dict) else response.model_dump()
    if data.get("status") not in ("completed", "requires_action"):
        raise ModelUnavailable("Gemini interaction did not complete: " + str(data.get("status")))
    if not data.get("id"):
        raise ModelUnavailable("Gemini returned no interaction id")
    turn = Turn(id=data["id"])
    # Current API uses steps; outputs supports earlier SDK response shapes.
    for step in data.get("steps", data.get("outputs", [])):
        if step.get("type") == "function_call":
            turn.calls.append(ToolCall(step["id"], step["name"], step.get("arguments")))
        elif step.get("type") == "model_output":
            turn.text += "".join(
                c.get("text", "") for c in step.get("content", []) if c.get("type") == "text"
            )
        elif step.get("type") == "text":
            turn.text += step.get("text", "")
    return turn


def function_result(call: ToolCall, result: Any) -> dict:
    return {
        "type": "function_result",
        "name": call.name,
        "call_id": call.id,
        "is_error": isinstance(result, dict) and "error" in result,
        "result": [{"type": "text", "text": data_block(result)}],
    }


class GeminiClient:
    def __init__(self, client=None):
        settings = get_settings()
        self.model = settings.gemini_model
        self.thinking_level = settings.gemini_thinking_level
        if client is None:
            from google import genai

            if not settings.gemini_api_key:
                raise ModelUnavailable("GEMINI_API_KEY is not configured")
            client = genai.Client(api_key=settings.gemini_api_key)
        self.client = client

    async def close(self):
        await self.client.aio.aclose()

    async def turn(
        self,
        input,
        *,
        instruction: str,
        tools: list,
        previous_id: str | None = None,
        repair: bool = False,
    ) -> Turn:
        body = {
            "model": self.model,
            "input": input,
            "system_instruction": instruction,
            "tools": tools,
            "generation_config": {"thinking_level": "high" if repair else self.thinking_level},
        }
        if previous_id:
            body["previous_interaction_id"] = previous_id
        for attempt in range(4):
            try:
                response = await asyncio.wait_for(
                    self.client.aio.interactions.create(**body), timeout=120
                )
                return parse_turn(response)
            except ModelUnavailable:
                raise
            except Exception as exc:
                code = getattr(exc, "code", getattr(exc, "status_code", None))
                if str(code) == "429" and attempt < 3:
                    await asyncio.sleep(2**attempt)
                    continue
                # Avoid propagating SDK request bodies or credentials into events.
                raise ModelUnavailable(
                    f"Gemini request failed ({type(exc).__name__}, status={code})"
                ) from exc
        raise ModelUnavailable("Gemini retry budget exhausted")
