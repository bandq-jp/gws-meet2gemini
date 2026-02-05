"""
Supabase Memory Service for ADK.

Provides semantic search using pgvector and Gemini embeddings.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

from google.adk.memory import BaseMemoryService
from google.adk.memory.base_memory_service import SearchMemoryResponse
from google.adk.memory.memory_entry import MemoryEntry
from google.genai import Client, types

if TYPE_CHECKING:
    from google.adk.sessions.session import Session
    from app.infrastructure.config.settings import Settings

logger = logging.getLogger(__name__)


class SupabaseMemoryService(BaseMemoryService):
    """
    Supabase-backed memory service with semantic search via pgvector.

    Uses Gemini embeddings for vector similarity search.
    """

    def __init__(self, settings: "Settings"):
        """
        Initialize the Supabase memory service.

        Args:
            settings: Application settings containing Supabase and Gemini config.
        """
        self._settings = settings

        # Lazy import to avoid circular dependencies
        from app.infrastructure.supabase.client import get_supabase
        self._supabase = get_supabase()

        # Create Gemini client for embeddings
        self._genai_client = Client(api_key=settings.gemini_api_key)
        self._embedding_model = settings.memory_embedding_model
        self._embedding_dimensions = settings.memory_embedding_dimensions
        self._max_results = settings.memory_max_results

        logger.info(
            f"[Memory] SupabaseMemoryService initialized "
            f"(model={self._embedding_model}, dims={self._embedding_dimensions})"
        )

    async def _get_embedding(self, text: str) -> list[float]:
        """
        Generate embedding vector using Gemini Embedding API.

        Args:
            text: Text to embed.

        Returns:
            Embedding vector (list of floats).
        """
        try:
            # Use Gemini embedding model with Matryoshka truncation
            result = self._genai_client.models.embed_content(
                model=f"models/{self._embedding_model}",
                contents=text,
                config={"output_dimensionality": self._embedding_dimensions},
            )
            # Result has .embeddings list, first item has .values
            return list(result.embeddings[0].values)
        except Exception as e:
            logger.error(f"[Memory] Embedding generation failed: {e}")
            raise

    async def add_session_to_memory(self, session: "Session") -> None:
        """
        Add session events to memory storage with embeddings.

        Filters out events without text content and generates embeddings
        for semantic search.

        Args:
            session: The ADK Session object containing events.
        """
        if not session.events:
            logger.debug(f"[Memory] No events in session {session.id}")
            return

        entries_to_insert = []
        event_count = 0

        for event in session.events:
            # Skip events without content
            if not event.content or not event.content.parts:
                continue

            # Extract text from all parts
            text_parts = []
            for part in event.content.parts:
                if hasattr(part, "text") and part.text:
                    text_parts.append(part.text)

            if not text_parts:
                continue

            # Combine all text parts
            full_text = " ".join(text_parts)

            # Skip very short content (likely not useful for memory)
            if len(full_text.strip()) < 10:
                continue

            try:
                # Generate embedding
                embedding = await self._get_embedding(full_text)

                # Prepare entry for insertion
                entry = {
                    "app_name": session.app_name,
                    "user_id": session.user_id,
                    "session_id": session.id,
                    "event_id": getattr(event, "id", None),
                    "author": getattr(event, "author", None),
                    "event_timestamp": _format_timestamp(getattr(event, "timestamp", None)),
                    "content_text": full_text,
                    "embedding": embedding,
                    "metadata": {
                        "role": getattr(event.content, "role", None),
                        "has_function_calls": _has_function_calls(event),
                    },
                }
                entries_to_insert.append(entry)
                event_count += 1

            except Exception as e:
                logger.warning(f"[Memory] Failed to process event: {e}")
                continue

        # Bulk insert to Supabase
        if entries_to_insert:
            try:
                self._supabase.table("marketing_memories").insert(
                    entries_to_insert
                ).execute()
                logger.info(
                    f"[Memory] Saved {event_count} events from session {session.id}"
                )
            except Exception as e:
                logger.error(f"[Memory] Failed to save session to memory: {e}")

    async def search_memory(
        self,
        *,
        app_name: str,
        user_id: str,
        query: str,
    ) -> SearchMemoryResponse:
        """
        Search memory using semantic similarity.

        Uses pgvector cosine distance for finding relevant past conversations.

        Args:
            app_name: Application name.
            user_id: User identifier.
            query: Search query text.

        Returns:
            SearchMemoryResponse containing relevant MemoryEntry objects.
        """
        try:
            # Generate query embedding
            query_embedding = await self._get_embedding(query)

            # Search using Supabase RPC function
            result = self._supabase.rpc(
                "search_memories_by_embedding",
                {
                    "query_embedding": query_embedding,
                    "match_app_name": app_name,
                    "match_user_id": user_id,
                    "match_count": self._max_results,
                    "similarity_threshold": 0.3,  # Minimum similarity score
                },
            ).execute()

            # Convert to MemoryEntry objects
            memories = []
            for row in result.data or []:
                try:
                    memory = MemoryEntry(
                        id=str(row.get("id", "")),
                        author=row.get("author"),
                        timestamp=_format_timestamp_str(row.get("event_timestamp") or row.get("created_at")),
                        content=types.Content(
                            parts=[types.Part(text=row.get("content_text", ""))],
                            role=row.get("metadata", {}).get("role", "user"),
                        ),
                        custom_metadata={
                            "similarity": row.get("similarity"),
                            "session_id": row.get("session_id"),
                            "conversation_id": str(row.get("conversation_id")) if row.get("conversation_id") else None,
                        },
                    )
                    memories.append(memory)
                except Exception as e:
                    logger.warning(f"[Memory] Failed to parse memory entry: {e}")
                    continue

            logger.info(
                f"[Memory] Search found {len(memories)} results for query: {query[:50]}..."
            )
            return SearchMemoryResponse(memories=memories)

        except Exception as e:
            logger.error(f"[Memory] Search failed: {e}")
            return SearchMemoryResponse(memories=[])


def _format_timestamp(timestamp: Optional[float]) -> Optional[str]:
    """Convert Unix timestamp to ISO 8601 string."""
    if timestamp is None:
        return None
    try:
        return datetime.fromtimestamp(timestamp).isoformat()
    except (ValueError, OSError):
        return None


def _format_timestamp_str(timestamp_str: Optional[str]) -> Optional[str]:
    """Format timestamp string to ISO 8601 if needed."""
    if timestamp_str is None:
        return None
    # If already ISO format, return as-is
    if "T" in str(timestamp_str):
        return str(timestamp_str).split("+")[0]  # Remove timezone for consistency
    return timestamp_str


def _has_function_calls(event: Any) -> bool:
    """Check if event contains function calls."""
    if not hasattr(event, "content") or not event.content:
        return False
    if not hasattr(event.content, "parts"):
        return False
    for part in event.content.parts:
        if hasattr(part, "function_call") and part.function_call:
            return True
    return False
