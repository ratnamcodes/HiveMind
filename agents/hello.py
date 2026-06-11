"""Minimal ADK 2.0 agent demonstrating Gemini 3.5 function calling."""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from google.adk.agents import LlmAgent as Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

load_dotenv()


def get_current_time(timezone: str) -> dict[str, Any]:
    """Return the current time in the given IANA timezone (e.g. 'Asia/Kolkata').

    Args:
        timezone: An IANA timezone name such as 'Asia/Kolkata' or 'UTC'.

    Returns:
        A dict with 'status', 'timezone', and 'iso_time' (ISO 8601 string).
    """
    try:
        now = datetime.now(ZoneInfo(timezone))
    except Exception as e:
        return {"status": "error", "timezone": timezone, "error": str(e)}
    return {"status": "success", "timezone": timezone, "iso_time": now.isoformat()}


APP_NAME = "hello"
USER_ID = "demo-user"

agent = Agent(
    name="hello",
    model="gemini-3.5-flash",
    instruction="Use get_current_time when asked about times.",
    tools=[get_current_time],
)


async def run_once(prompt: str) -> tuple[str, list[dict[str, Any]]]:
    """Run the hello agent on one prompt; return (final_text, tool_call_trace)."""
    session_service = InMemorySessionService()
    runner = Runner(
        agent=agent,
        app_name=APP_NAME,
        session_service=session_service,
    )
    session = await session_service.create_session(
        app_name=APP_NAME, user_id=USER_ID
    )
    message = types.Content(role="user", parts=[types.Part(text=prompt)])

    final_text = ""
    tool_trace: list[dict[str, Any]] = []

    async for event in runner.run_async(
        user_id=session.user_id,
        session_id=session.id,
        new_message=message,
    ):
        for call in event.get_function_calls() or []:
            tool_trace.append(
                {"kind": "call", "name": call.name, "args": dict(call.args or {})}
            )
        for resp in event.get_function_responses() or []:
            tool_trace.append(
                {"kind": "response", "name": resp.name, "response": dict(resp.response or {})}
            )
        if event.is_final_response() and event.content and event.content.parts:
            final_text = "".join(part.text or "" for part in event.content.parts)

    return final_text, tool_trace


if __name__ == "__main__":
    prompt = "What's the time in Asia/Kolkata?"
    text, trace = asyncio.run(run_once(prompt))

    print("=== Tool call sequence ===")
    for entry in trace:
        print(entry)
    print("\n=== Final response ===")
    print(text)
