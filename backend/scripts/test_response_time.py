#!/usr/bin/env python3
"""
Response Time Benchmark for Marketing AI.

Tests the response time for different query types:
1. Simple queries (no sub-agent)
2. Medium queries (1 sub-agent)
3. Complex queries (multiple sub-agents)

Usage:
    cd backend
    uv run python scripts/test_response_time.py
"""

import asyncio
import json
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any

# Add backend to path
sys.path.insert(0, "/home/als0028/study/bandq-jp/gws-meet2gemini/backend")

from app.infrastructure.config.settings import Settings
from app.infrastructure.marketing.agent_service import MarketingAgentService
from app.infrastructure.chatkit.mcp_manager import MCPSessionManager


@dataclass
class BenchmarkResult:
    """Result of a single benchmark run."""
    query: str
    scenario: str
    ttft: float  # Time to first token (seconds)
    total_time: float  # Total response time (seconds)
    event_count: int
    sub_agent_count: int
    sub_agents_called: list[str]
    error: str | None = None


async def run_single_benchmark(
    agent_service: MarketingAgentService,
    query: str,
    scenario: str,
) -> BenchmarkResult:
    """Run a single benchmark for a query."""
    print(f"\n  Testing: {query[:50]}...")

    start_time = time.perf_counter()
    first_token_time = None
    event_count = 0
    sub_agents_called = []
    error = None

    try:
        async for event in agent_service.stream_chat(
            user_id="benchmark-user",
            user_email="benchmark@bandq.jp",
            conversation_id=f"benchmark-{int(time.time())}",
            message=query,
            context_items=None,
        ):
            if first_token_time is None:
                first_token_time = time.perf_counter()

            event_count += 1

            # Track sub-agent calls
            if event.get("type") == "sub_agent_event":
                agent_name = event.get("agent", "unknown")
                if agent_name not in sub_agents_called:
                    sub_agents_called.append(agent_name)

            # Print progress
            event_type = event.get("type", "unknown")
            if event_type in ("text_delta", "reasoning"):
                pass  # Skip verbose events
            elif event_type == "sub_agent_event":
                print(f"    -> Sub-agent: {event.get('agent')}")
            elif event_type == "tool_call":
                print(f"    -> Tool: {event.get('name')}")
            elif event_type == "done":
                pass

    except Exception as e:
        error = str(e)
        print(f"    ERROR: {error}")

    total_time = time.perf_counter() - start_time
    ttft = (first_token_time or total_time) - start_time

    result = BenchmarkResult(
        query=query,
        scenario=scenario,
        ttft=round(ttft, 3),
        total_time=round(total_time, 3),
        event_count=event_count,
        sub_agent_count=len(sub_agents_called),
        sub_agents_called=sub_agents_called,
        error=error,
    )

    print(f"    TTFT: {result.ttft}s, Total: {result.total_time}s, Events: {result.event_count}")
    return result


async def main():
    """Run benchmark suite."""
    print("=" * 60)
    print("Marketing AI Response Time Benchmark")
    print("=" * 60)
    print(f"Started: {datetime.now().isoformat()}")

    # Initialize
    settings = Settings()
    mcp_manager = MCPSessionManager(settings)
    agent_service = MarketingAgentService(settings, mcp_manager)

    print(f"\nModel: {settings.marketing_agent_model}")
    print(f"Sub-Agent Model: {settings.sub_agent_model}")

    # Define test scenarios
    scenarios = {
        "simple": [
            "こんにちは",
            "あなたは何ができますか？",
        ],
        "medium": [
            "Zoho CRMの求職者数を教えて",
        ],
        "complex": [
            "hitocareer.comのトラフィックと求職者データを分析して",
        ],
    }

    results: list[BenchmarkResult] = []

    for scenario, queries in scenarios.items():
        print(f"\n--- Scenario: {scenario.upper()} ---")

        for query in queries:
            result = await run_single_benchmark(agent_service, query, scenario)
            results.append(result)

            # Small delay between tests
            await asyncio.sleep(1)

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    for scenario in ["simple", "medium", "complex"]:
        scenario_results = [r for r in results if r.scenario == scenario]
        if not scenario_results:
            continue

        avg_ttft = sum(r.ttft for r in scenario_results) / len(scenario_results)
        avg_total = sum(r.total_time for r in scenario_results) / len(scenario_results)

        print(f"\n{scenario.upper()}:")
        print(f"  Avg TTFT: {avg_ttft:.3f}s")
        print(f"  Avg Total: {avg_total:.3f}s")
        print(f"  Queries: {len(scenario_results)}")

    # Save results
    output_file = "/tmp/benchmark_results.json"
    with open(output_file, "w") as f:
        json.dump(
            {
                "timestamp": datetime.now().isoformat(),
                "model": settings.marketing_agent_model,
                "sub_agent_model": settings.sub_agent_model,
                "results": [
                    {
                        "query": r.query,
                        "scenario": r.scenario,
                        "ttft": r.ttft,
                        "total_time": r.total_time,
                        "event_count": r.event_count,
                        "sub_agent_count": r.sub_agent_count,
                        "sub_agents_called": r.sub_agents_called,
                        "error": r.error,
                    }
                    for r in results
                ],
            },
            f,
            indent=2,
            ensure_ascii=False,
        )
    print(f"\nResults saved to: {output_file}")

    print("\n" + "=" * 60)
    print("Benchmark Complete")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
