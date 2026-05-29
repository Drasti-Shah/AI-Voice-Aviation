import os
import json
import asyncio
from typing import Awaitable, Callable

from openai import AsyncOpenAI
from aviation_client import get_flight_status

FillerFn = Callable[[], Awaitable[None]]

_client: AsyncOpenAI | None = None


def _client_instance() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"])
    return _client


SYSTEM_PROMPT = (
    "You are an aviation passenger assistant for a demo. Be concise (1-3 sentences), warm, and natural. "
    "You can answer questions about flight status (delays, gate, terminal, ETA) and general baggage / "
    "check-in policy questions. For flight status, ALWAYS call the get_flight_status tool using the IATA "
    "flight code (e.g. AI302, 6E1407). If the caller doesn't give a flight number, ask for it. "
    "For baggage/check-in, give general guidance and remind the caller to confirm with their airline. "
    "Speak plainly, no markdown, no bullet points; the reply will be spoken aloud."
)

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_flight_status",
            "description": "Look up live status for a specific flight by its IATA code (e.g. AI302).",
            "parameters": {
                "type": "object",
                "properties": {
                    "flight_iata": {
                        "type": "string",
                        "description": "IATA flight code, e.g. AI302, 6E1407, UA945",
                    }
                },
                "required": ["flight_iata"],
            },
        },
    }
]


async def answer(user_text: str, history: list[dict], on_tool_call: FillerFn | None = None) -> str:
    """Get a reply. If the LLM picks a tool, optionally fires on_tool_call()
    in parallel — used by callers to play a 'let me check' filler over the
    ~3s of tool+second-LLM latency so the caller doesn't sit in silence."""
    client = _client_instance()
    messages = [{"role": "system", "content": SYSTEM_PROMPT}, *history, {"role": "user", "content": user_text}]

    first = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        tools=TOOLS,
        temperature=0.4,
    )
    msg = first.choices[0].message

    if msg.tool_calls:
        filler_task = asyncio.create_task(on_tool_call()) if on_tool_call else None

        messages.append(msg.model_dump(exclude_none=True))
        for tc in msg.tool_calls:
            if tc.function.name == "get_flight_status":
                args = json.loads(tc.function.arguments or "{}")
                result = await get_flight_status(args.get("flight_iata", ""))
            else:
                result = {"error": "unknown_tool"}
            messages.append(
                {"role": "tool", "tool_call_id": tc.id, "content": json.dumps(result)}
            )

        second = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.4,
        )
        # Wait for the filler audio to finish before returning, so the main
        # reply isn't sent on top of the filler.
        if filler_task is not None:
            try:
                await filler_task
            except Exception:
                pass
        return (second.choices[0].message.content or "").strip()

    return (msg.content or "").strip()
