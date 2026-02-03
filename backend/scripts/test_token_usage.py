#!/usr/bin/env python3
"""
Token Usage Test Script for Marketing Agent

Tests the OpenAI Agents SDK to measure token usage after optimization.
Uses the MARKETING_AGENT_MODEL (gpt-5-mini) configured in environment.

Usage:
    cd backend
    uv run python scripts/test_token_usage.py
"""

import asyncio
import os
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import dotenv
dotenv.load_dotenv()

from agents import Agent, Runner
from app.infrastructure.config.settings import get_settings
from app.infrastructure.chatkit.seo_agent_factory import (
    MARKETING_INSTRUCTIONS,
    GA4_ALLOWED_TOOLS,
    GSC_ALLOWED_TOOLS,
    AHREFS_ALLOWED_TOOLS,
    META_ADS_ALLOWED_TOOLS,
    WORDPRESS_ALLOWED_TOOLS,
    WORDPRESS_HITOCAREER_ALLOWED_TOOLS,
)
from app.infrastructure.chatkit.zoho_crm_tools import ZOHO_CRM_TOOLS
from app.infrastructure.chatkit.candidate_insight_tools import CANDIDATE_INSIGHT_TOOLS


def count_tokens_estimate(text: str) -> int:
    """Rough token count estimate (4 chars ~ 1 token for Japanese)"""
    return len(text) // 3


def print_section(title: str, content: str = ""):
    """Print formatted section"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")
    if content:
        print(content)


async def test_agent_token_usage():
    """Test agent creation and measure token usage"""
    settings = get_settings()

    print_section("Token Usage Test - Marketing Agent Optimization")

    # Check API key
    if not settings.openai_api_key:
        print("ERROR: OPENAI_API_KEY not set")
        return

    model = settings.marketing_agent_model
    print(f"\nModel: {model}")

    # Tool counts - BEFORE optimization
    print_section("Tool Counts - Before Optimization")
    before_counts = {
        "GA4": 6,  # unchanged
        "GSC": 19,  # was 19, now 10
        "Ahrefs": 52,  # was 52, now 20
        "Meta Ads": 31,  # was 31, now 20
        "WordPress (legacy)": 3,
        "WordPress (hitocareer)": 25,
        "Zoho CRM": 9,
        "Candidate Insight": 4,
    }
    before_total = sum(before_counts.values())
    for name, count in before_counts.items():
        print(f"  {name}: {count} tools")
    print(f"  ───────────────────")
    print(f"  Total: {before_total} tools")

    # Tool counts - AFTER optimization
    print_section("Tool Counts - After Optimization")

    after_counts = {
        "GA4": len(GA4_ALLOWED_TOOLS),
        "GSC": len(GSC_ALLOWED_TOOLS),
        "Ahrefs": len(AHREFS_ALLOWED_TOOLS),
        "Meta Ads": len(META_ADS_ALLOWED_TOOLS),
        "WordPress (legacy)": len(WORDPRESS_ALLOWED_TOOLS),
        "WordPress (hitocareer)": len(WORDPRESS_HITOCAREER_ALLOWED_TOOLS),
        "Zoho CRM": len(ZOHO_CRM_TOOLS),
        "Candidate Insight": len(CANDIDATE_INSIGHT_TOOLS),
    }

    after_total = sum(after_counts.values())

    for name, count in after_counts.items():
        before = before_counts[name]
        diff = count - before
        diff_str = f"({diff:+d})" if diff != 0 else "(same)"
        print(f"  {name}: {count} tools {diff_str}")
    print(f"  ───────────────────")
    print(f"  Total: {after_total} tools ({after_total - before_total:+d})")

    # Instructions comparison
    print_section("System Instructions Comparison")

    before_instructions_chars = 5100  # Approximate original size
    before_tokens_est = 1700  # Original estimate

    after_instructions_chars = len(MARKETING_INSTRUCTIONS)
    after_tokens_est = count_tokens_estimate(MARKETING_INSTRUCTIONS)

    print(f"  Before: ~{before_instructions_chars} chars (~{before_tokens_est} tokens)")
    print(f"  After:  {after_instructions_chars} chars (~{after_tokens_est} tokens)")
    print(f"  Reduction: {before_instructions_chars - after_instructions_chars:,} chars ({(1 - after_instructions_chars/before_instructions_chars)*100:.0f}%)")

    # Create minimal agent for token test (without MCP tools to avoid connection)
    print_section("Running Token Test with OpenAI API...")

    # Simple agent with just function tools
    agent = Agent(
        name="TokenTestAgent",
        instructions=MARKETING_INSTRUCTIONS,
        model=model,
        tools=list(ZOHO_CRM_TOOLS) + list(CANDIDATE_INSIGHT_TOOLS),
    )

    try:
        # Run simple test
        result = await Runner.run(
            agent,
            input="こんにちは。あなたのツールを一覧で教えてください。",
        )

        print_section("API Response Token Usage")

        # Get usage from raw responses
        total_input = 0
        total_output = 0
        if hasattr(result, 'raw_responses') and result.raw_responses:
            for i, response in enumerate(result.raw_responses):
                if hasattr(response, 'usage') and response.usage:
                    usage = response.usage
                    total_input += usage.input_tokens
                    total_output += usage.output_tokens
                    print(f"\n  Response {i+1}:")
                    print(f"    Input tokens:  {usage.input_tokens:,}")
                    print(f"    Output tokens: {usage.output_tokens:,}")
                    print(f"    Total tokens:  {usage.total_tokens:,}")

                    if hasattr(usage, 'input_tokens_details'):
                        details = usage.input_tokens_details
                        print(f"\n    Input breakdown:")
                        if hasattr(details, 'cached_tokens'):
                            print(f"      Cached: {details.cached_tokens:,}")
                        if hasattr(details, 'text_tokens'):
                            print(f"      Text: {details.text_tokens:,}")

        # Summary
        print_section("Optimization Summary")
        print(f"  Tool count reduction:        {before_total} → {after_total} ({(1 - after_total/before_total)*100:.0f}% reduction)")
        print(f"  Instructions char reduction: {before_instructions_chars} → {after_instructions_chars} ({(1 - after_instructions_chars/before_instructions_chars)*100:.0f}% reduction)")
        print(f"  Actual input tokens (13 tools): {total_input:,}")

        # Estimate for full tool set
        # Rough estimate: ~100 tokens per MCP tool schema
        mcp_tools_tokens_estimate = (after_total - 13) * 80  # 80 tokens per MCP tool (allowed list only)
        estimated_full = total_input + mcp_tools_tokens_estimate
        print(f"  Estimated full input tokens: ~{estimated_full:,}")

        # Print final output (truncated)
        print_section("Agent Response (first 300 chars)")
        output_text = result.final_output[:300] if result.final_output else "(no output)"
        print(output_text)
        if result.final_output and len(result.final_output) > 300:
            print(f"\n... ({len(result.final_output) - 300} more chars)")

    except Exception as e:
        print(f"\nERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

    print_section("Test Complete")


if __name__ == "__main__":
    asyncio.run(test_agent_token_usage())
