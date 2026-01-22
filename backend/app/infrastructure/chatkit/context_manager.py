"""
Context Window Management Module for OpenAI Agents SDK

This module implements multiple levels of context window management:
- L2: call_model_input_filter for custom trimming
- L3: OpenAIResponsesCompactionSession integration
- L4: TrimmingSession / SummarizingSession patterns

Based on OpenAI Agents SDK best practices and Anthropic's context engineering guidelines.

References:
- https://openai.github.io/openai-agents-python/sessions/
- https://cookbook.openai.com/examples/agents_sdk/session_memory
- https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections import deque
from dataclasses import dataclass, field
from typing import (
    Any,
    Callable,
    Deque,
    Dict,
    List,
    Optional,
    Protocol,
    Tuple,
    TypeVar,
    Union,
)

from agents import RunConfig
from agents.items import TResponseInputItem

logger = logging.getLogger(__name__)


# =============================================================================
# Type Definitions
# =============================================================================

@dataclass
class ContextBudget:
    """Token budget configuration for context window management."""
    max_tokens: int = 180_000  # 90% of 200k (safety margin)
    warning_threshold: float = 0.7  # 70% triggers warning
    compaction_threshold: float = 0.85  # 85% triggers compaction
    current_tokens: int = 0

    def is_warning_level(self) -> bool:
        return self.current_tokens >= self.max_tokens * self.warning_threshold

    def needs_compaction(self) -> bool:
        return self.current_tokens >= self.max_tokens * self.compaction_threshold

    def usage_ratio(self) -> float:
        return self.current_tokens / self.max_tokens if self.max_tokens > 0 else 0.0


@dataclass
class ModelInputData:
    """Data structure for model input after filtering."""
    input: List[TResponseInputItem]
    instructions: str


@dataclass
class CallModelData:
    """Data structure passed to call_model_input_filter."""
    model_data: ModelInputData
    agent: Any = None
    context: Any = None


# =============================================================================
# L2: call_model_input_filter Implementation
# =============================================================================

def _is_user_msg(item: TResponseInputItem) -> bool:
    """Return True if the item represents a user message.

    Based on OpenAI Cookbook implementation.
    """
    if isinstance(item, dict):
        role = item.get("role")
        if role is not None:
            return role == "user"
        if item.get("type") == "message":
            return item.get("role") == "user"
    return getattr(item, "role", None) == "user"


def _is_tool_result(item: TResponseInputItem) -> bool:
    """Return True if the item is a tool result/output."""
    if isinstance(item, dict):
        item_type = item.get("type", "")
        role = item.get("role", "")
        return item_type in ("tool_result", "function_call_output") or role in ("tool", "function")
    item_type = getattr(item, "type", "")
    return item_type in ("tool_result", "function_call_output")


def _count_user_turns(items: List[TResponseInputItem]) -> int:
    """Count the number of user turns in the conversation."""
    return sum(1 for item in items if _is_user_msg(item))


def _trim_to_last_n_turns(
    items: List[TResponseInputItem],
    max_turns: int,
) -> List[TResponseInputItem]:
    """Keep only the suffix containing the last N user messages.

    Args:
        items: List of conversation items
        max_turns: Maximum number of user turns to keep

    Returns:
        Trimmed list of items
    """
    if not items or max_turns <= 0:
        return items

    count = 0
    start_idx = 0

    # Walk backward; when we hit the Nth user message, mark its index
    for i in range(len(items) - 1, -1, -1):
        if _is_user_msg(items[i]):
            count += 1
            if count == max_turns:
                start_idx = i
                break

    return items[start_idx:]


def _clear_old_tool_results(
    items: List[TResponseInputItem],
    keep_last_n: int = 3,
) -> List[TResponseInputItem]:
    """Clear tool results from old messages, keeping only recent ones.

    This implements "tool result clearing" - a lightweight compaction technique
    that removes raw outputs from deeply nested tool calls.

    Args:
        items: List of conversation items
        keep_last_n: Number of recent tool results to keep in full

    Returns:
        Items with old tool results summarized
    """
    if not items:
        return items

    result = []
    tool_result_count = 0

    # Count total tool results first
    total_tool_results = sum(1 for item in items if _is_tool_result(item))
    threshold = max(0, total_tool_results - keep_last_n)

    for item in items:
        if _is_tool_result(item):
            tool_result_count += 1
            if tool_result_count <= threshold:
                # Summarize old tool result
                if isinstance(item, dict):
                    summarized = {
                        **item,
                        "content": "[Tool output truncated - see recent results for details]",
                    }
                    result.append(summarized)
                else:
                    # For object types, just append as-is (can't modify)
                    result.append(item)
            else:
                result.append(item)
        else:
            result.append(item)

    return result


def create_trimming_filter(
    max_turns: int = 10,
    max_items: int = 50,
    clear_old_tool_results: bool = True,
    keep_recent_tool_results: int = 5,
) -> Callable[[Any], ModelInputData]:
    """Create a call_model_input_filter that trims conversation history.

    This is L2 implementation - deterministic trimming without LLM calls.

    Args:
        max_turns: Maximum number of user turns to keep
        max_items: Maximum total items in history
        clear_old_tool_results: Whether to clear old tool results
        keep_recent_tool_results: Number of recent tool results to preserve

    Returns:
        Filter function for RunConfig.call_model_input_filter

    Example:
        run_config = RunConfig(
            call_model_input_filter=create_trimming_filter(max_turns=8)
        )
    """
    def filter_fn(data: Any) -> ModelInputData:
        # Handle different input formats
        if hasattr(data, 'model_data'):
            items = list(data.model_data.input)
            instructions = data.model_data.instructions
        else:
            items = list(data.input) if hasattr(data, 'input') else []
            instructions = getattr(data, 'instructions', '')

        original_count = len(items)

        # Step 1: Trim to max_turns
        if max_turns > 0:
            items = _trim_to_last_n_turns(items, max_turns)

        # Step 2: Trim to max_items
        if max_items > 0 and len(items) > max_items:
            items = items[-max_items:]

        # Step 3: Clear old tool results
        if clear_old_tool_results:
            items = _clear_old_tool_results(items, keep_recent_tool_results)

        trimmed_count = len(items)
        if trimmed_count < original_count:
            logger.info(
                f"Context trimmed: {original_count} -> {trimmed_count} items "
                f"(max_turns={max_turns}, max_items={max_items})"
            )

        return ModelInputData(input=items, instructions=instructions)

    return filter_fn


def create_token_budget_filter(
    budget: ContextBudget,
    chars_per_token: float = 4.0,
) -> Callable[[Any], ModelInputData]:
    """Create a filter that trims based on estimated token count.

    Args:
        budget: ContextBudget configuration
        chars_per_token: Estimated characters per token (default 4.0 for mixed content)

    Returns:
        Filter function that respects token budget
    """
    def estimate_tokens(items: List[TResponseInputItem]) -> int:
        """Rough token estimation based on character count."""
        total_chars = 0
        for item in items:
            if isinstance(item, dict):
                content = item.get("content", "")
                if isinstance(content, str):
                    total_chars += len(content)
                elif isinstance(content, list):
                    for part in content:
                        if isinstance(part, dict):
                            total_chars += len(str(part.get("text", "")))
            else:
                total_chars += len(str(getattr(item, "content", "")))
        return int(total_chars / chars_per_token)

    def filter_fn(data: Any) -> ModelInputData:
        if hasattr(data, 'model_data'):
            items = list(data.model_data.input)
            instructions = data.model_data.instructions
        else:
            items = list(data.input) if hasattr(data, 'input') else []
            instructions = getattr(data, 'instructions', '')

        estimated_tokens = estimate_tokens(items)
        budget.current_tokens = estimated_tokens

        if budget.needs_compaction():
            logger.warning(
                f"Context approaching limit: {estimated_tokens}/{budget.max_tokens} tokens "
                f"({budget.usage_ratio():.1%})"
            )
            # Aggressive trimming when near limit
            target_tokens = int(budget.max_tokens * 0.6)  # Trim to 60%
            while estimate_tokens(items) > target_tokens and len(items) > 2:
                items = items[1:]  # Remove oldest item
            logger.info(f"Trimmed to {len(items)} items, ~{estimate_tokens(items)} tokens")

        return ModelInputData(input=items, instructions=instructions)

    return filter_fn


# =============================================================================
# L4: TrimmingSession Implementation
# =============================================================================

class SessionABC(Protocol):
    """Protocol for session implementations."""

    async def get_items(self, limit: Optional[int] = None) -> List[TResponseInputItem]:
        """Retrieve conversation history."""
        ...

    async def add_items(self, items: List[TResponseInputItem]) -> None:
        """Store new items."""
        ...

    async def pop_item(self) -> Optional[TResponseInputItem]:
        """Remove and return most recent item."""
        ...

    async def clear_session(self) -> None:
        """Clear all items."""
        ...


class TrimmingSession:
    """Keep only the last N user turns in memory.

    A "turn" consists of one user message plus all subsequent assistant/tool
    interactions until the next user message arrives.

    This is a deterministic approach with:
    - Zero latency overhead (no model calls)
    - Predictable behavior
    - Suitable for independent tasks with non-overlapping context

    Based on OpenAI Cookbook implementation:
    https://cookbook.openai.com/examples/agents_sdk/session_memory
    """

    def __init__(
        self,
        session_id: str,
        max_turns: int = 8,
        max_items: int = 100,
    ):
        """Initialize TrimmingSession.

        Args:
            session_id: Unique identifier for this session
            max_turns: Maximum number of user turns to keep
            max_items: Maximum total items (safety limit)
        """
        self.session_id = session_id
        self.max_turns = max(1, int(max_turns))
        self.max_items = max(1, int(max_items))
        self._items: Deque[TResponseInputItem] = deque()
        self._lock = asyncio.Lock()

    async def get_items(self, limit: Optional[int] = None) -> List[TResponseInputItem]:
        """Return history trimmed to the last N user turns."""
        async with self._lock:
            trimmed = _trim_to_last_n_turns(list(self._items), self.max_turns)
            if limit is not None and limit >= 0:
                return trimmed[-limit:]
            return trimmed

    async def add_items(self, items: List[TResponseInputItem]) -> None:
        """Append new items, then trim to last N user turns."""
        if not items:
            return
        async with self._lock:
            self._items.extend(items)
            # Apply max_items limit first
            while len(self._items) > self.max_items:
                self._items.popleft()
            # Then trim to max_turns
            trimmed = _trim_to_last_n_turns(list(self._items), self.max_turns)
            self._items.clear()
            self._items.extend(trimmed)

    async def pop_item(self) -> Optional[TResponseInputItem]:
        """Remove and return the most recent item."""
        async with self._lock:
            if self._items:
                return self._items.pop()
            return None

    async def clear_session(self) -> None:
        """Clear all items from the session."""
        async with self._lock:
            self._items.clear()

    def __len__(self) -> int:
        return len(self._items)


# =============================================================================
# L4: SummarizingSession Implementation
# =============================================================================

@dataclass
class SummaryRecord:
    """Record structure for SummarizingSession."""
    msg: Dict[str, Any]
    meta: Dict[str, Any] = field(default_factory=dict)


class LLMSummarizer:
    """Summarizer that uses OpenAI API to compress conversation history.

    Based on OpenAI Cookbook implementation.
    """

    SUMMARY_PROMPT = """あなたは会話履歴を簡潔に要約するアシスタントです。
以下の会話履歴を、重要な情報を保持しながら簡潔に要約してください。

要約に含めるべき項目：
- ユーザーの主な質問・要求
- 重要な決定事項やアクション
- ツール実行の結果の要点
- 現在の状態や次のステップ

要約のガイドライン：
- 箇条書きで構造化する
- 具体的な数値やデータは保持する
- 重要でない詳細は省略する
- 時系列で整理する

出力形式：
## 会話要約
- [要点1]
- [要点2]
...

## 現在の状態
[現在の状況の説明]

## 次のアクション
[必要なアクションがあれば]
"""

    def __init__(
        self,
        client: Any,
        model: str = "gpt-4o-mini",
        max_tokens: int = 500,
        tool_trim_limit: int = 600,
    ):
        """Initialize LLMSummarizer.

        Args:
            client: OpenAI client instance
            model: Model to use for summarization
            max_tokens: Maximum tokens for summary output
            tool_trim_limit: Character limit for tool outputs in summary input
        """
        self.client = client
        self.model = model
        self.max_tokens = max_tokens
        self.tool_trim_limit = tool_trim_limit

    async def summarize(
        self,
        messages: List[Dict[str, Any]],
    ) -> Tuple[str, str]:
        """Create a compact summary from messages.

        Args:
            messages: List of message dicts to summarize

        Returns:
            Tuple of (user_shadow_prompt, assistant_summary)
        """
        user_shadow = "これまでの会話を要約してください。"
        tool_roles = {"tool", "tool_result", "function"}

        def to_snippet(m: Dict[str, Any]) -> Optional[str]:
            role = (m.get("role") or "assistant").lower()
            content = m.get("content", "")
            if isinstance(content, list):
                # Handle content arrays
                text_parts = []
                for part in content:
                    if isinstance(part, dict):
                        text_parts.append(part.get("text", str(part)))
                    else:
                        text_parts.append(str(part))
                content = " ".join(text_parts)
            content = str(content).strip()
            if not content:
                return None
            if role in tool_roles and len(content) > self.tool_trim_limit:
                content = content[:self.tool_trim_limit] + " …"
            return f"{role.upper()}: {content}"

        history_snippets = [s for m in messages if (s := to_snippet(m))]

        if not history_snippets:
            return user_shadow, "会話履歴がありません。"

        prompt_messages = [
            {"role": "system", "content": self.SUMMARY_PROMPT},
            {"role": "user", "content": "\n".join(history_snippets)},
        ]

        try:
            # Use responses API if available
            if hasattr(self.client, "responses"):
                resp = await asyncio.to_thread(
                    self.client.responses.create,
                    model=self.model,
                    input=prompt_messages,
                    max_output_tokens=self.max_tokens,
                )
                summary = resp.output_text
            else:
                # Fallback to chat completions
                resp = await asyncio.to_thread(
                    self.client.chat.completions.create,
                    model=self.model,
                    messages=prompt_messages,
                    max_tokens=self.max_tokens,
                )
                summary = resp.choices[0].message.content

            return user_shadow, summary or "要約を生成できませんでした。"
        except Exception as e:
            logger.error(f"Summarization failed: {e}")
            return user_shadow, f"要約の生成に失敗しました: {str(e)}"


class SummarizingSession:
    """Keep last N user turns verbatim; summarize everything older.

    This preserves long-range context compactly while keeping recent
    interactions in full detail.

    Features:
    - Recent turns preserved verbatim for "rhythm" maintenance
    - Older content compressed into synthetic summary messages
    - Suitable for long-horizon planning and analysis tasks

    Based on OpenAI Cookbook implementation:
    https://cookbook.openai.com/examples/agents_sdk/session_memory
    """

    def __init__(
        self,
        session_id: str,
        keep_last_n_turns: int = 3,
        context_limit: int = 5,
        summarizer: Optional[LLMSummarizer] = None,
    ):
        """Initialize SummarizingSession.

        Args:
            session_id: Unique identifier for this session
            keep_last_n_turns: Number of recent user turns to keep verbatim
            context_limit: Total turn count that triggers summarization
            summarizer: LLMSummarizer instance (required for summarization)
        """
        self.session_id = session_id
        self.keep_last_n_turns = max(1, keep_last_n_turns)
        self.context_limit = max(self.keep_last_n_turns + 1, context_limit)
        self.summarizer = summarizer
        self._records: Deque[SummaryRecord] = deque()
        self._lock = asyncio.Lock()

    def _split_msg_and_meta(
        self,
        item: Dict[str, Any],
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Split item into message and metadata."""
        meta_keys = {"synthetic", "kind", "timestamp", "session_id"}
        meta = {k: v for k, v in item.items() if k in meta_keys}
        msg = {k: v for k, v in item.items() if k not in meta_keys}
        return msg, meta

    def _sanitize_for_model(self, msg: Dict[str, Any]) -> Dict[str, Any]:
        """Remove metadata fields before sending to model."""
        return {k: v for k, v in msg.items() if k not in {"synthetic", "kind"}}

    def _count_user_turns_locked(self) -> int:
        """Count user turns in current records (must hold lock)."""
        return sum(
            1 for rec in self._records
            if rec.msg.get("role") == "user" and not rec.meta.get("synthetic")
        )

    def _summarize_decision_locked(self) -> Tuple[bool, int]:
        """Decide whether summarization is needed (must hold lock).

        Returns:
            Tuple of (need_summary, boundary_index)
        """
        user_turn_count = self._count_user_turns_locked()

        if user_turn_count <= self.context_limit:
            return False, 0

        # Find boundary: keep last N turns verbatim
        keep_count = 0
        boundary = len(self._records)

        for i in range(len(self._records) - 1, -1, -1):
            rec = self._records[i]
            if rec.msg.get("role") == "user" and not rec.meta.get("synthetic"):
                keep_count += 1
                if keep_count == self.keep_last_n_turns:
                    boundary = i
                    break

        return True, boundary

    def _normalize_synthetic_flags_locked(self) -> None:
        """Ensure synthetic records are properly marked (must hold lock)."""
        for rec in self._records:
            if rec.meta.get("synthetic"):
                rec.msg["synthetic"] = True

    async def get_items(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Return model-safe messages (no internal metadata)."""
        async with self._lock:
            data = list(self._records)
        msgs = [self._sanitize_for_model(rec.msg) for rec in data]
        return msgs[-limit:] if limit else msgs

    async def add_items(self, items: List[Dict[str, Any]]) -> None:
        """Append items and summarize older turns if needed."""
        if not items:
            return

        # Add items under lock
        async with self._lock:
            for item in items:
                if isinstance(item, dict):
                    msg, meta = self._split_msg_and_meta(item)
                else:
                    msg = {"role": "user", "content": str(item)}
                    meta = {}
                self._records.append(SummaryRecord(msg=msg, meta=meta))
            need_summary, boundary = self._summarize_decision_locked()

        if not need_summary:
            async with self._lock:
                self._normalize_synthetic_flags_locked()
            return

        if not self.summarizer:
            logger.warning("Summarization needed but no summarizer configured")
            return

        # Summarization runs outside the lock
        async with self._lock:
            snapshot = list(self._records)
            prefix_msgs = [rec.msg for rec in snapshot[:boundary]]

        user_shadow, assistant_summary = await self.summarizer.summarize(prefix_msgs)

        # Re-check and apply summary under lock
        async with self._lock:
            still_need, new_boundary = self._summarize_decision_locked()
            if not still_need:
                self._normalize_synthetic_flags_locked()
                return

            snapshot = list(self._records)
            suffix = snapshot[new_boundary:]

            self._records.clear()
            # Add synthetic summary messages
            self._records.append(SummaryRecord(
                msg={"role": "user", "content": user_shadow},
                meta={"synthetic": True, "kind": "history_summary_prompt"},
            ))
            self._records.append(SummaryRecord(
                msg={"role": "assistant", "content": assistant_summary},
                meta={"synthetic": True, "kind": "history_summary"},
            ))
            self._records.extend(suffix)
            self._normalize_synthetic_flags_locked()

            logger.info(
                f"Session {self.session_id}: Summarized {boundary} items, "
                f"kept {len(suffix)} recent items"
            )

    async def pop_item(self) -> Optional[Dict[str, Any]]:
        """Remove and return the most recent item."""
        async with self._lock:
            if self._records:
                rec = self._records.pop()
                return self._sanitize_for_model(rec.msg)
            return None

    async def clear_session(self) -> None:
        """Clear all items from the session."""
        async with self._lock:
            self._records.clear()

    def __len__(self) -> int:
        return len(self._records)


# =============================================================================
# L3: Compaction Session Wrapper
# =============================================================================

class CompactionSessionWrapper:
    """Wrapper that adds compaction capability to any session.

    This provides automatic compaction similar to OpenAIResponsesCompactionSession
    but works with custom session implementations.

    Features:
    - Configurable compaction threshold
    - Manual compaction trigger
    - Preserves recent items in raw form
    """

    def __init__(
        self,
        underlying_session: Any,
        summarizer: Optional[LLMSummarizer] = None,
        compaction_threshold: int = 100_000,  # Estimated token threshold
        keep_recent_items: int = 10,
        auto_compact: bool = True,
    ):
        """Initialize CompactionSessionWrapper.

        Args:
            underlying_session: Session to wrap
            summarizer: LLMSummarizer for compaction
            compaction_threshold: Token threshold for auto-compaction
            keep_recent_items: Number of recent items to preserve verbatim
            auto_compact: Whether to auto-compact on add_items
        """
        self._session = underlying_session
        self._summarizer = summarizer
        self._compaction_threshold = compaction_threshold
        self._keep_recent_items = keep_recent_items
        self._auto_compact = auto_compact
        self._lock = asyncio.Lock()

    def _estimate_tokens(self, items: List[Any]) -> int:
        """Estimate token count for items."""
        total_chars = 0
        for item in items:
            if isinstance(item, dict):
                content = item.get("content", "")
                if isinstance(content, str):
                    total_chars += len(content)
                elif isinstance(content, list):
                    for part in content:
                        if isinstance(part, dict):
                            total_chars += len(str(part.get("text", "")))
            else:
                total_chars += len(str(getattr(item, "content", "")))
        return int(total_chars / 4.0)  # ~4 chars per token

    async def get_items(self, limit: Optional[int] = None) -> List[Any]:
        """Get items from underlying session."""
        return await self._session.get_items(limit)

    async def add_items(self, items: List[Any]) -> None:
        """Add items and optionally trigger compaction."""
        await self._session.add_items(items)

        if self._auto_compact:
            await self._maybe_compact()

    async def _maybe_compact(self) -> None:
        """Check if compaction is needed and run it."""
        async with self._lock:
            items = await self._session.get_items()
            estimated_tokens = self._estimate_tokens(items)

            if estimated_tokens < self._compaction_threshold:
                return

            if not self._summarizer:
                logger.warning(
                    f"Compaction needed ({estimated_tokens} tokens) but no summarizer"
                )
                return

            logger.info(
                f"Starting compaction: {estimated_tokens} tokens > {self._compaction_threshold}"
            )
            await self._run_compaction(items)

    async def _run_compaction(self, items: List[Any]) -> None:
        """Run compaction on items."""
        if len(items) <= self._keep_recent_items:
            return

        # Split into prefix (to summarize) and suffix (to keep)
        prefix = items[:-self._keep_recent_items]
        suffix = items[-self._keep_recent_items:]

        # Convert to dicts for summarizer
        prefix_dicts = [
            item if isinstance(item, dict) else {"role": "user", "content": str(item)}
            for item in prefix
        ]

        user_shadow, summary = await self._summarizer.summarize(prefix_dicts)

        # Clear and rebuild session
        await self._session.clear_session()

        # Add compacted history
        compacted = [
            {"role": "user", "content": user_shadow, "synthetic": True},
            {"role": "assistant", "content": summary, "synthetic": True},
        ]
        compacted.extend(suffix)

        await self._session.add_items(compacted)

        new_items = await self._session.get_items()
        logger.info(
            f"Compaction complete: {len(items)} -> {len(new_items)} items"
        )

    async def run_compaction(self, force: bool = False) -> None:
        """Manually trigger compaction.

        Args:
            force: If True, compact even if below threshold
        """
        async with self._lock:
            items = await self._session.get_items()
            if force or self._estimate_tokens(items) >= self._compaction_threshold:
                await self._run_compaction(items)

    async def pop_item(self) -> Optional[Any]:
        """Remove and return most recent item."""
        return await self._session.pop_item()

    async def clear_session(self) -> None:
        """Clear all items."""
        await self._session.clear_session()


# =============================================================================
# Factory Functions
# =============================================================================

def create_context_managed_run_config(
    max_turns: int = 10,
    max_items: int = 50,
    clear_old_tool_results: bool = True,
    token_budget: Optional[ContextBudget] = None,
    **extra_config: Any,
) -> RunConfig:
    """Create a RunConfig with context management enabled.

    This combines L2 trimming with optional token budget management.

    Args:
        max_turns: Maximum user turns to keep
        max_items: Maximum total items
        clear_old_tool_results: Whether to summarize old tool outputs
        token_budget: Optional token budget for more aggressive management
        **extra_config: Additional RunConfig parameters

    Returns:
        Configured RunConfig instance

    Example:
        config = create_context_managed_run_config(max_turns=8)
        result = Runner.run_streamed(agent, input, run_config=config)
    """
    if token_budget:
        filter_fn = create_token_budget_filter(token_budget)
    else:
        filter_fn = create_trimming_filter(
            max_turns=max_turns,
            max_items=max_items,
            clear_old_tool_results=clear_old_tool_results,
        )

    return RunConfig(
        call_model_input_filter=filter_fn,
        **extra_config,
    )


def create_session_for_thread(
    thread_id: str,
    session_type: str = "trimming",
    openai_client: Optional[Any] = None,
    **kwargs: Any,
) -> Union[TrimmingSession, SummarizingSession, CompactionSessionWrapper]:
    """Create an appropriate session for a thread.

    Args:
        thread_id: Thread/conversation ID
        session_type: One of "trimming", "summarizing", "compaction"
        openai_client: OpenAI client (required for summarizing/compaction)
        **kwargs: Additional session parameters

    Returns:
        Session instance

    Example:
        session = create_session_for_thread(
            thread.id,
            session_type="summarizing",
            openai_client=client,
            keep_last_n_turns=3,
        )
    """
    if session_type == "trimming":
        return TrimmingSession(
            session_id=thread_id,
            max_turns=kwargs.get("max_turns", 8),
            max_items=kwargs.get("max_items", 100),
        )

    elif session_type == "summarizing":
        summarizer = None
        if openai_client:
            summarizer = LLMSummarizer(
                client=openai_client,
                model=kwargs.get("summarizer_model", "gpt-4o-mini"),
            )
        return SummarizingSession(
            session_id=thread_id,
            keep_last_n_turns=kwargs.get("keep_last_n_turns", 3),
            context_limit=kwargs.get("context_limit", 5),
            summarizer=summarizer,
        )

    elif session_type == "compaction":
        base_session = TrimmingSession(
            session_id=thread_id,
            max_turns=kwargs.get("max_turns", 20),
            max_items=kwargs.get("max_items", 200),
        )
        summarizer = None
        if openai_client:
            summarizer = LLMSummarizer(
                client=openai_client,
                model=kwargs.get("summarizer_model", "gpt-4o-mini"),
            )
        return CompactionSessionWrapper(
            underlying_session=base_session,
            summarizer=summarizer,
            compaction_threshold=kwargs.get("compaction_threshold", 100_000),
            keep_recent_items=kwargs.get("keep_recent_items", 10),
            auto_compact=kwargs.get("auto_compact", True),
        )

    else:
        raise ValueError(f"Unknown session type: {session_type}")
