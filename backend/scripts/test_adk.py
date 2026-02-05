#!/usr/bin/env python
"""
Test script for Google ADK integration.

Tests:
1. Simple agent creation and response
2. Zoho CRM tool integration (if configured)
3. Streaming responses
"""

import asyncio
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types


def create_user_content(text: str) -> types.Content:
    """Create a Content object with user role."""
    return types.Content(
        role="user",
        parts=[types.Part(text=text)],
    )


async def test_simple_agent():
    """Test a simple ADK agent with Gemini."""
    print("\n" + "=" * 60)
    print("Test 1: Simple ADK Agent")
    print("=" * 60)

    agent = Agent(
        name="test_agent",
        model="gemini-3-flash-preview",
        description="A simple test agent",
        instruction="あなたは親切なアシスタントです。日本語で簡潔に応答してください。",
    )

    session_service = InMemorySessionService()
    runner = Runner(
        agent=agent,
        app_name="test",
        session_service=session_service,
    )

    # Create session (async in ADK)
    session = await session_service.create_session(
        app_name="test",
        user_id="test_user",
        session_id="test_session",
    )

    print("\nUser: こんにちは！今日は何曜日ですか？")
    print("\nAgent: ", end="", flush=True)

    # Run with streaming - pass Content object
    response_text = ""
    user_content = create_user_content("こんにちは！今日は何曜日ですか？")

    async for event in runner.run_async(
        user_id="test_user",
        session_id="test_session",
        new_message=user_content,
    ):
        if hasattr(event, "content") and event.content:
            if hasattr(event.content, "parts"):
                for part in event.content.parts:
                    if hasattr(part, "text") and part.text:
                        print(part.text, end="", flush=True)
                        response_text += part.text
            elif isinstance(event.content, str):
                print(event.content, end="", flush=True)
                response_text += event.content

    print("\n")
    print(f"✅ Response received ({len(response_text)} chars)")
    return True


async def test_agent_with_tool():
    """Test ADK agent with a simple function tool."""
    print("\n" + "=" * 60)
    print("Test 2: ADK Agent with Tool")
    print("=" * 60)

    # Define a simple tool
    def get_current_time() -> dict:
        """Get the current time in Tokyo."""
        from datetime import datetime
        from zoneinfo import ZoneInfo
        tz = ZoneInfo("Asia/Tokyo")
        now = datetime.now(tz)
        return {
            "time": now.strftime("%H:%M:%S"),
            "date": now.strftime("%Y-%m-%d"),
            "weekday": ["月曜日", "火曜日", "水曜日", "木曜日", "金曜日", "土曜日", "日曜日"][now.weekday()],
        }

    agent = Agent(
        name="tool_test_agent",
        model="gemini-3-flash-preview",
        description="An agent that can check the time",
        instruction="あなたは時間を確認できるアシスタントです。ユーザーが時間を聞いたらget_current_timeツールを使ってください。日本語で応答してください。",
        tools=[get_current_time],
    )

    session_service = InMemorySessionService()
    runner = Runner(
        agent=agent,
        app_name="test",
        session_service=session_service,
    )

    session = await session_service.create_session(
        app_name="test",
        user_id="test_user",
        session_id="tool_test_session",
    )

    print("\nUser: 今何時ですか？")
    print("\nAgent: ", end="", flush=True)

    response_text = ""
    tool_called = False
    user_content = create_user_content("今何時ですか？")

    async for event in runner.run_async(
        user_id="test_user",
        session_id="tool_test_session",
        new_message=user_content,
    ):
        # Check for tool call
        if hasattr(event, "function_call") and event.function_call:
            tool_called = True
            print(f"\n[Tool: {event.function_call.name}]", end="", flush=True)

        # Check for content
        if hasattr(event, "content") and event.content:
            if hasattr(event.content, "parts"):
                for part in event.content.parts:
                    if hasattr(part, "text") and part.text:
                        print(part.text, end="", flush=True)
                        response_text += part.text
            elif isinstance(event.content, str):
                print(event.content, end="", flush=True)
                response_text += event.content

    print("\n")
    print(f"✅ Tool called: {tool_called}")
    print(f"✅ Response received ({len(response_text)} chars)")
    return tool_called


async def test_zoho_agent():
    """Test the Zoho CRM agent integration."""
    print("\n" + "=" * 60)
    print("Test 3: Zoho CRM Agent (if configured)")
    print("=" * 60)

    from app.infrastructure.config.settings import get_settings
    settings = get_settings()

    if not settings.zoho_refresh_token:
        print("⏭️ Skipped (no ZOHO_REFRESH_TOKEN)")
        return True

    from app.infrastructure.adk.agents import ZohoCRMAgentFactory

    factory = ZohoCRMAgentFactory(settings)
    agent = factory.build_agent()

    session_service = InMemorySessionService()
    runner = Runner(
        agent=agent,
        app_name="test",
        session_service=session_service,
    )

    session = await session_service.create_session(
        app_name="test",
        user_id="test_user",
        session_id="zoho_test_session",
    )

    print("\nUser: 今月のチャネル別獲得数を教えて")
    print("\nAgent: ", end="", flush=True)

    response_text = ""
    user_content = create_user_content("今月のチャネル別獲得数を教えて")

    async for event in runner.run_async(
        user_id="test_user",
        session_id="zoho_test_session",
        new_message=user_content,
    ):
        if hasattr(event, "content") and event.content:
            if hasattr(event.content, "parts"):
                for part in event.content.parts:
                    if hasattr(part, "text") and part.text:
                        print(part.text, end="", flush=True)
                        response_text += part.text

    print("\n")
    print(f"✅ Response received ({len(response_text)} chars)")
    return True


async def main():
    """Run all tests."""
    print("\n🚀 ADK Integration Tests")
    print("=" * 60)

    # Check for API key
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("❌ Error: GEMINI_API_KEY or GOOGLE_API_KEY not set")
        return

    print(f"✅ API Key found (length: {len(api_key)})")

    results = []

    # Test 1: Simple agent
    try:
        results.append(("Simple Agent", await test_simple_agent()))
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        results.append(("Simple Agent", False))

    # Test 2: Agent with tool
    try:
        results.append(("Agent with Tool", await test_agent_with_tool()))
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        results.append(("Agent with Tool", False))

    # Test 3: Zoho agent
    try:
        results.append(("Zoho Agent", await test_zoho_agent()))
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        results.append(("Zoho Agent", False))

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    for name, passed in results:
        status = "✅" if passed else "❌"
        print(f"{status} {name}")

    all_passed = all(r[1] for r in results)
    print("\n" + ("🎉 All tests passed!" if all_passed else "⚠️ Some tests failed"))


if __name__ == "__main__":
    asyncio.run(main())
