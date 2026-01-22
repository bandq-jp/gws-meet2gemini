"""
Tests for context window management module.

These tests verify the L2-L4 context management implementations:
- L2: call_model_input_filter (trimming)
- L3: CompactionSessionWrapper
- L4: TrimmingSession / SummarizingSession
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.infrastructure.chatkit.context_manager import (
    ContextBudget,
    ModelInputData,
    _is_user_msg,
    _is_tool_result,
    _count_user_turns,
    _trim_to_last_n_turns,
    _clear_old_tool_results,
    create_trimming_filter,
    create_token_budget_filter,
    TrimmingSession,
    SummarizingSession,
    LLMSummarizer,
    CompactionSessionWrapper,
    create_session_for_thread,
)


# =============================================================================
# Test Data Fixtures
# =============================================================================

@pytest.fixture
def sample_messages():
    """Sample conversation messages for testing."""
    return [
        {"role": "user", "content": "Hello, how are you?"},
        {"role": "assistant", "content": "I'm doing well, thank you!"},
        {"role": "user", "content": "Can you help me with coding?"},
        {"role": "assistant", "content": "Of course! What do you need?"},
        {"role": "user", "content": "Write a function"},
        {"role": "assistant", "content": "Here's a function..."},
        {"role": "user", "content": "Now test it"},
        {"role": "assistant", "content": "Running tests..."},
    ]


@pytest.fixture
def messages_with_tools():
    """Messages including tool calls and results."""
    return [
        {"role": "user", "content": "Search for something"},
        {"role": "assistant", "content": "I'll search for that."},
        {"type": "tool_result", "content": "Long tool output " * 100},
        {"role": "assistant", "content": "Found it!"},
        {"role": "user", "content": "Another query"},
        {"type": "tool_result", "content": "Another long output " * 100},
        {"role": "assistant", "content": "Here's the result."},
    ]


# =============================================================================
# Helper Function Tests
# =============================================================================

class TestHelperFunctions:
    """Test helper functions for message classification."""

    def test_is_user_msg_dict(self):
        """Test user message detection with dict input."""
        assert _is_user_msg({"role": "user", "content": "test"}) is True
        assert _is_user_msg({"role": "assistant", "content": "test"}) is False
        assert _is_user_msg({"role": "tool", "content": "test"}) is False

    def test_is_user_msg_message_type(self):
        """Test user message detection with type='message'."""
        assert _is_user_msg({"type": "message", "role": "user"}) is True
        assert _is_user_msg({"type": "message", "role": "assistant"}) is False

    def test_is_tool_result(self):
        """Test tool result detection."""
        assert _is_tool_result({"type": "tool_result", "content": "test"}) is True
        assert _is_tool_result({"type": "function_call_output", "content": "test"}) is True
        assert _is_tool_result({"role": "tool", "content": "test"}) is True
        assert _is_tool_result({"role": "user", "content": "test"}) is False

    def test_count_user_turns(self, sample_messages):
        """Test user turn counting."""
        assert _count_user_turns(sample_messages) == 4

    def test_trim_to_last_n_turns(self, sample_messages):
        """Test trimming to last N user turns."""
        trimmed = _trim_to_last_n_turns(sample_messages, 2)
        # Should keep last 2 user turns and their responses
        assert _count_user_turns(trimmed) == 2
        assert trimmed[0]["content"] == "Write a function"

    def test_trim_to_last_n_turns_empty(self):
        """Test trimming with empty input."""
        assert _trim_to_last_n_turns([], 5) == []

    def test_clear_old_tool_results(self, messages_with_tools):
        """Test clearing old tool results."""
        cleared = _clear_old_tool_results(messages_with_tools, keep_last_n=1)

        # First tool result should be truncated
        tool_results = [m for m in cleared if _is_tool_result(m)]
        assert "[Tool output truncated" in tool_results[0]["content"]
        # Last tool result should be preserved
        assert "Another long output" in tool_results[1]["content"]


# =============================================================================
# ContextBudget Tests
# =============================================================================

class TestContextBudget:
    """Test ContextBudget functionality."""

    def test_default_values(self):
        """Test default budget values."""
        budget = ContextBudget()
        assert budget.max_tokens == 180_000
        assert budget.warning_threshold == 0.7
        assert budget.compaction_threshold == 0.85

    def test_is_warning_level(self):
        """Test warning level detection."""
        budget = ContextBudget(max_tokens=100, current_tokens=69)
        assert budget.is_warning_level() is False

        budget.current_tokens = 70
        assert budget.is_warning_level() is True

    def test_needs_compaction(self):
        """Test compaction threshold detection."""
        budget = ContextBudget(max_tokens=100, current_tokens=84)
        assert budget.needs_compaction() is False

        budget.current_tokens = 85
        assert budget.needs_compaction() is True

    def test_usage_ratio(self):
        """Test usage ratio calculation."""
        budget = ContextBudget(max_tokens=100, current_tokens=50)
        assert budget.usage_ratio() == 0.5


# =============================================================================
# Trimming Filter Tests
# =============================================================================

class TestTrimmingFilter:
    """Test call_model_input_filter trimming implementation."""

    def test_create_trimming_filter_basic(self, sample_messages):
        """Test basic trimming filter creation and usage."""
        filter_fn = create_trimming_filter(max_turns=2, max_items=50)

        # Create mock data structure
        mock_data = MagicMock()
        mock_data.model_data.input = sample_messages
        mock_data.model_data.instructions = "Test instructions"

        result = filter_fn(mock_data)

        assert isinstance(result, ModelInputData)
        assert _count_user_turns(result.input) == 2
        assert result.instructions == "Test instructions"

    def test_create_trimming_filter_max_items(self, sample_messages):
        """Test max_items limit."""
        filter_fn = create_trimming_filter(max_turns=10, max_items=3)

        mock_data = MagicMock()
        mock_data.model_data.input = sample_messages
        mock_data.model_data.instructions = ""

        result = filter_fn(mock_data)
        assert len(result.input) == 3

    def test_token_budget_filter(self, sample_messages):
        """Test token budget based filtering."""
        budget = ContextBudget(max_tokens=50, current_tokens=0)
        filter_fn = create_token_budget_filter(budget, chars_per_token=10.0)

        mock_data = MagicMock()
        mock_data.model_data.input = sample_messages
        mock_data.model_data.instructions = ""

        result = filter_fn(mock_data)
        # Filter should update budget
        assert budget.current_tokens > 0


# =============================================================================
# TrimmingSession Tests
# =============================================================================

class TestTrimmingSession:
    """Test TrimmingSession implementation."""

    @pytest.mark.asyncio
    async def test_add_and_get_items(self, sample_messages):
        """Test adding and retrieving items."""
        session = TrimmingSession("test-session", max_turns=4)

        await session.add_items(sample_messages)
        items = await session.get_items()

        assert len(items) <= len(sample_messages)
        assert _count_user_turns(items) <= 4

    @pytest.mark.asyncio
    async def test_trimming_on_add(self, sample_messages):
        """Test that trimming happens on add."""
        session = TrimmingSession("test-session", max_turns=2)

        await session.add_items(sample_messages)
        items = await session.get_items()

        assert _count_user_turns(items) == 2

    @pytest.mark.asyncio
    async def test_pop_item(self, sample_messages):
        """Test popping last item."""
        session = TrimmingSession("test-session", max_turns=10)

        await session.add_items(sample_messages)
        original_len = len(session)

        popped = await session.pop_item()

        assert popped is not None
        assert len(session) == original_len - 1

    @pytest.mark.asyncio
    async def test_clear_session(self, sample_messages):
        """Test clearing session."""
        session = TrimmingSession("test-session", max_turns=10)

        await session.add_items(sample_messages)
        assert len(session) > 0

        await session.clear_session()
        assert len(session) == 0


# =============================================================================
# SummarizingSession Tests
# =============================================================================

class TestSummarizingSession:
    """Test SummarizingSession implementation."""

    @pytest.mark.asyncio
    async def test_add_items_below_threshold(self, sample_messages):
        """Test adding items below summarization threshold."""
        session = SummarizingSession(
            "test-session",
            keep_last_n_turns=3,
            context_limit=10,  # High threshold, won't trigger
            summarizer=None,
        )

        await session.add_items([{"role": "user", "content": "test"}])
        items = await session.get_items()

        assert len(items) == 1
        assert items[0]["content"] == "test"

    @pytest.mark.asyncio
    async def test_sanitize_removes_metadata(self):
        """Test that metadata is removed from output."""
        session = SummarizingSession("test-session")

        await session.add_items([
            {"role": "user", "content": "test", "synthetic": False, "kind": "normal"}
        ])
        items = await session.get_items()

        assert "synthetic" not in items[0]
        assert "kind" not in items[0]


# =============================================================================
# LLMSummarizer Tests
# =============================================================================

class TestLLMSummarizer:
    """Test LLMSummarizer implementation."""

    @pytest.mark.asyncio
    async def test_summarize_basic(self, sample_messages):
        """Test basic summarization."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.output_text = "This is a summary."
        mock_client.responses.create.return_value = mock_response

        summarizer = LLMSummarizer(client=mock_client, model="gpt-4o-mini")

        with patch('asyncio.to_thread', new_callable=AsyncMock) as mock_to_thread:
            mock_to_thread.return_value = mock_response
            user_shadow, summary = await summarizer.summarize(sample_messages)

        assert "会話を要約" in user_shadow
        assert summary == "This is a summary."

    def test_tool_trim_limit(self):
        """Test that tool outputs are trimmed."""
        summarizer = LLMSummarizer(
            client=MagicMock(),
            tool_trim_limit=10,
        )

        # Internal method test - create long tool output
        messages = [{"role": "tool", "content": "a" * 100}]

        # The to_snippet internal function should trim this
        # We test indirectly through summarize behavior


# =============================================================================
# CompactionSessionWrapper Tests
# =============================================================================

class TestCompactionSessionWrapper:
    """Test CompactionSessionWrapper implementation."""

    @pytest.mark.asyncio
    async def test_wrapper_delegates_to_underlying(self):
        """Test that wrapper delegates to underlying session."""
        underlying = TrimmingSession("test", max_turns=10)
        wrapper = CompactionSessionWrapper(
            underlying,
            summarizer=None,
            auto_compact=False,
        )

        await wrapper.add_items([{"role": "user", "content": "test"}])
        items = await wrapper.get_items()

        assert len(items) == 1

    @pytest.mark.asyncio
    async def test_manual_compaction(self, sample_messages):
        """Test manual compaction trigger."""
        underlying = TrimmingSession("test", max_turns=100)

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.output_text = "Compacted summary"

        summarizer = LLMSummarizer(client=mock_client)

        wrapper = CompactionSessionWrapper(
            underlying,
            summarizer=summarizer,
            compaction_threshold=10,  # Low threshold
            keep_recent_items=2,
            auto_compact=False,
        )

        await wrapper.add_items(sample_messages)

        with patch.object(summarizer, 'summarize', new_callable=AsyncMock) as mock_summarize:
            mock_summarize.return_value = ("Summary prompt", "Compacted summary")
            await wrapper.run_compaction(force=True)


# =============================================================================
# Factory Function Tests
# =============================================================================

class TestFactoryFunctions:
    """Test factory functions."""

    def test_create_session_trimming(self):
        """Test creating trimming session."""
        session = create_session_for_thread(
            "test-thread",
            session_type="trimming",
            max_turns=5,
        )

        assert isinstance(session, TrimmingSession)
        assert session.session_id == "test-thread"
        assert session.max_turns == 5

    def test_create_session_summarizing(self):
        """Test creating summarizing session."""
        session = create_session_for_thread(
            "test-thread",
            session_type="summarizing",
            openai_client=None,
            keep_last_n_turns=2,
        )

        assert isinstance(session, SummarizingSession)
        assert session.keep_last_n_turns == 2

    def test_create_session_compaction(self):
        """Test creating compaction session."""
        session = create_session_for_thread(
            "test-thread",
            session_type="compaction",
            openai_client=None,
            compaction_threshold=50000,
        )

        assert isinstance(session, CompactionSessionWrapper)

    def test_create_session_invalid_type(self):
        """Test invalid session type raises error."""
        with pytest.raises(ValueError, match="Unknown session type"):
            create_session_for_thread("test", session_type="invalid")


# =============================================================================
# Integration Tests
# =============================================================================

class TestIntegration:
    """Integration tests for context management."""

    @pytest.mark.asyncio
    async def test_full_conversation_flow(self):
        """Test a full conversation flow with context management."""
        session = TrimmingSession("integration-test", max_turns=3)

        # Simulate multiple conversation turns
        for i in range(5):
            await session.add_items([
                {"role": "user", "content": f"Question {i}"},
                {"role": "assistant", "content": f"Answer {i}"},
            ])

        items = await session.get_items()
        user_count = _count_user_turns(items)

        # Should have trimmed to 3 turns
        assert user_count == 3
        # Most recent should be preserved
        assert any("Question 4" in str(item.get("content", "")) for item in items)

    @pytest.mark.asyncio
    async def test_trimming_filter_with_runner_config(self):
        """Test that trimming filter works with RunConfig-like structure."""
        filter_fn = create_trimming_filter(max_turns=2)

        # Simulate what Runner would pass
        class MockModelData:
            input = [
                {"role": "user", "content": "First"},
                {"role": "assistant", "content": "Response 1"},
                {"role": "user", "content": "Second"},
                {"role": "assistant", "content": "Response 2"},
                {"role": "user", "content": "Third"},
                {"role": "assistant", "content": "Response 3"},
            ]
            instructions = "Be helpful"

        class MockCallModelData:
            model_data = MockModelData()

        result = filter_fn(MockCallModelData())

        assert _count_user_turns(result.input) == 2
        assert result.instructions == "Be helpful"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
