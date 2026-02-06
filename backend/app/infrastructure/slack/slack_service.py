"""
Slack Service - Dual-token Slack API client with caching.

Uses:
- User Token (xoxp-): search.messages (search:read scope)
- Bot Token (xoxb-): conversations.history, conversations.replies,
  conversations.list, users.info

Caches: channel name->id mapping (1h TTL), user id->name mapping (1h TTL)
"""

from __future__ import annotations

import logging
import re
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

if TYPE_CHECKING:
    from app.infrastructure.config.settings import Settings

logger = logging.getLogger(__name__)

JST = timezone(timedelta(hours=9))

# Channel ID pattern: starts with C (public) or G (private group)
_CHANNEL_ID_RE = re.compile(r"^[CG][A-Z0-9]{8,}$")


class SlackService:
    """Slack API client with dual-token support and caching.

    Workspace-level tokens (not per-user), so a single singleton suffices.
    """

    _instance: Optional["SlackService"] = None
    _lock = threading.Lock()

    def __init__(self, settings: "Settings"):
        self._settings = settings
        self._user_client: Optional[WebClient] = None
        self._bot_client: Optional[WebClient] = None

        if settings.slack_user_token:
            self._user_client = WebClient(token=settings.slack_user_token)
            logger.info("[SlackService] User token client initialized")
        else:
            logger.warning("[SlackService] SLACK_USER_TOKEN not set; search.messages unavailable")

        if settings.slack_bot_token:
            self._bot_client = WebClient(token=settings.slack_bot_token)
            logger.info("[SlackService] Bot token client initialized")
        else:
            logger.warning("[SlackService] SLACK_BOT_TOKEN not set; conversations API unavailable")

        # Caches: (value, created_timestamp)
        self._channel_cache: Dict[str, Tuple[str, float]] = {}  # name -> (id, ts)
        self._channel_list_cache: Optional[Tuple[List[Dict], float]] = None
        self._user_cache: Dict[str, Tuple[str, float]] = {}  # user_id -> (display_name, ts)
        self._cache_ttl = 3600  # 1 hour in seconds

    @classmethod
    def get_instance(cls, settings: "Settings") -> "SlackService":
        """Thread-safe singleton."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(settings)
        return cls._instance

    # ------------------------------------------------------------------
    # Search (User Token)
    # ------------------------------------------------------------------

    def search_messages(
        self,
        query: str,
        count: int = 20,
        sort: str = "timestamp",
        sort_dir: str = "desc",
    ) -> Dict[str, Any]:
        """Full-text search across Slack workspace.

        Requires User Token (xoxp-) with search:read scope.
        """
        if not self._user_client:
            return {
                "success": False,
                "error": "SLACK_USER_TOKENが設定されていません。search.messagesは利用できません。",
            }

        try:
            response = self._user_client.search_messages(
                query=query,
                count=min(50, max(1, count)),
                sort=sort,
                sort_dir=sort_dir,
            )

            raw_matches = response.get("messages", {}).get("matches", [])
            total = response.get("messages", {}).get("total", 0)

            messages = []
            for msg in raw_matches:
                channel_info = msg.get("channel", {})
                user_id = msg.get("user", "")
                user_name = msg.get("username", "") or self.resolve_user_name(user_id)

                messages.append({
                    "channel_id": channel_info.get("id", ""),
                    "channel_name": channel_info.get("name", ""),
                    "user_id": user_id,
                    "user_name": user_name,
                    "text": msg.get("text", ""),
                    "timestamp": msg.get("ts", ""),
                    "datetime_jst": self._ts_to_jst(msg.get("ts", "")),
                    "permalink": msg.get("permalink", ""),
                    "thread_ts": msg.get("thread_ts"),
                })

            return {
                "success": True,
                "total": total,
                "count": len(messages),
                "messages": messages,
            }

        except SlackApiError as e:
            logger.error("[SlackService.search_messages] SlackApiError: %s", e.response.get("error", str(e)))
            return {"success": False, "error": f"Slack検索に失敗しました: {e.response.get('error', str(e))}"}
        except Exception as e:
            logger.error("[SlackService.search_messages] Error: %s", e, exc_info=True)
            return {"success": False, "error": f"Slack検索に失敗しました: {type(e).__name__}"}

    # ------------------------------------------------------------------
    # Channel History (Bot Token)
    # ------------------------------------------------------------------

    def get_channel_history(
        self,
        channel_id: str,
        oldest: Optional[str] = None,
        latest: Optional[str] = None,
        limit: int = 100,
    ) -> Dict[str, Any]:
        """Fetch message history from a specific channel."""
        if not self._bot_client:
            return {"success": False, "error": "SLACK_BOT_TOKENが設定されていません。"}

        try:
            kwargs: Dict[str, Any] = {
                "channel": channel_id,
                "limit": min(200, max(1, limit)),
            }
            if oldest:
                kwargs["oldest"] = oldest
            if latest:
                kwargs["latest"] = latest

            response = self._bot_client.conversations_history(**kwargs)

            raw_messages = response.get("messages", [])
            messages = []
            for msg in raw_messages:
                user_id = msg.get("user", "")
                messages.append({
                    "user_id": user_id,
                    "user_name": self.resolve_user_name(user_id),
                    "text": msg.get("text", ""),
                    "timestamp": msg.get("ts", ""),
                    "datetime_jst": self._ts_to_jst(msg.get("ts", "")),
                    "thread_ts": msg.get("thread_ts"),
                    "reply_count": msg.get("reply_count", 0),
                    "subtype": msg.get("subtype"),
                })

            return {
                "success": True,
                "count": len(messages),
                "has_more": response.get("has_more", False),
                "messages": messages,
            }

        except SlackApiError as e:
            err = e.response.get("error", str(e))
            logger.error("[SlackService.get_channel_history] SlackApiError: %s", err)
            if err == "channel_not_found":
                return {"success": False, "error": "チャンネルが見つかりません。チャンネル名/IDを確認してください。"}
            if err == "not_in_channel":
                return {"success": False, "error": "Botがこのチャンネルに参加していません。チャンネルにBotを招待してください。"}
            return {"success": False, "error": f"チャンネル履歴の取得に失敗しました: {err}"}
        except Exception as e:
            logger.error("[SlackService.get_channel_history] Error: %s", e, exc_info=True)
            return {"success": False, "error": f"チャンネル履歴の取得に失敗しました: {type(e).__name__}"}

    # ------------------------------------------------------------------
    # Thread Replies (Bot Token)
    # ------------------------------------------------------------------

    def get_thread_replies(
        self,
        channel_id: str,
        thread_ts: str,
    ) -> Dict[str, Any]:
        """Fetch all replies in a thread."""
        if not self._bot_client:
            return {"success": False, "error": "SLACK_BOT_TOKENが設定されていません。"}

        try:
            response = self._bot_client.conversations_replies(
                channel=channel_id,
                ts=thread_ts,
                limit=200,
            )

            raw_messages = response.get("messages", [])
            messages = []
            for msg in raw_messages:
                user_id = msg.get("user", "")
                messages.append({
                    "user_id": user_id,
                    "user_name": self.resolve_user_name(user_id),
                    "text": msg.get("text", ""),
                    "timestamp": msg.get("ts", ""),
                    "datetime_jst": self._ts_to_jst(msg.get("ts", "")),
                })

            return {
                "success": True,
                "thread_ts": thread_ts,
                "reply_count": len(messages) - 1,  # Exclude parent message
                "messages": messages,
            }

        except SlackApiError as e:
            err = e.response.get("error", str(e))
            logger.error("[SlackService.get_thread_replies] SlackApiError: %s", err)
            return {"success": False, "error": f"スレッド取得に失敗しました: {err}"}
        except Exception as e:
            logger.error("[SlackService.get_thread_replies] Error: %s", e, exc_info=True)
            return {"success": False, "error": f"スレッド取得に失敗しました: {type(e).__name__}"}

    # ------------------------------------------------------------------
    # Channel List (Bot Token)
    # ------------------------------------------------------------------

    def list_channels(
        self,
        types: str = "public_channel,private_channel",
        limit: int = 200,
    ) -> Dict[str, Any]:
        """List accessible channels. Always excludes im and mpim."""
        if not self._bot_client:
            return {"success": False, "error": "SLACK_BOT_TOKENが設定されていません。"}

        # Force exclude DMs
        allowed_types = {"public_channel", "private_channel"}
        requested = {t.strip() for t in types.split(",")}
        clean_types = ",".join(sorted(requested & allowed_types)) or "public_channel,private_channel"

        # Check cache
        now = time.time()
        if self._channel_list_cache:
            cached_channels, cached_ts = self._channel_list_cache
            if now - cached_ts < self._cache_ttl:
                return {
                    "success": True,
                    "count": len(cached_channels),
                    "channels": cached_channels[:limit],
                }

        try:
            all_channels: List[Dict] = []
            cursor = None

            while True:
                kwargs: Dict[str, Any] = {
                    "types": clean_types,
                    "limit": 200,
                    "exclude_archived": True,
                }
                if cursor:
                    kwargs["cursor"] = cursor

                response = self._bot_client.conversations_list(**kwargs)

                for ch in response.get("channels", []):
                    all_channels.append({
                        "id": ch.get("id", ""),
                        "name": ch.get("name", ""),
                        "topic": ch.get("topic", {}).get("value", ""),
                        "purpose": ch.get("purpose", {}).get("value", ""),
                        "member_count": ch.get("num_members", 0),
                        "is_private": ch.get("is_private", False),
                        "is_archived": ch.get("is_archived", False),
                    })

                cursor = response.get("response_metadata", {}).get("next_cursor")
                if not cursor:
                    break

            # Update caches
            self._channel_list_cache = (all_channels, now)
            for ch in all_channels:
                self._channel_cache[ch["name"]] = (ch["id"], now)

            return {
                "success": True,
                "count": len(all_channels),
                "channels": all_channels[:limit],
            }

        except SlackApiError as e:
            logger.error("[SlackService.list_channels] SlackApiError: %s", e.response.get("error", str(e)))
            return {"success": False, "error": f"チャンネル一覧の取得に失敗しました: {e.response.get('error', str(e))}"}
        except Exception as e:
            logger.error("[SlackService.list_channels] Error: %s", e, exc_info=True)
            return {"success": False, "error": f"チャンネル一覧の取得に失敗しました: {type(e).__name__}"}

    # ------------------------------------------------------------------
    # Resolution Helpers (cached)
    # ------------------------------------------------------------------

    def resolve_channel_id(self, channel_name_or_id: str) -> Optional[str]:
        """Resolve channel name to ID. Returns None if not found."""
        name = channel_name_or_id.lstrip("#").strip()

        if _CHANNEL_ID_RE.match(name):
            return name

        now = time.time()

        # Check cache
        if name in self._channel_cache:
            cached_id, cached_ts = self._channel_cache[name]
            if now - cached_ts < self._cache_ttl:
                return cached_id

        # Rebuild cache from list
        result = self.list_channels()
        if result.get("success"):
            if name in self._channel_cache:
                return self._channel_cache[name][0]

        return None

    def resolve_user_name(self, user_id: str) -> str:
        """Resolve user ID to display name. Returns user_id if not resolvable."""
        if not user_id or not self._bot_client:
            return user_id or "unknown"

        now = time.time()

        # Check cache
        if user_id in self._user_cache:
            cached_name, cached_ts = self._user_cache[user_id]
            if now - cached_ts < self._cache_ttl:
                return cached_name

        try:
            response = self._bot_client.users_info(user=user_id)
            user = response.get("user", {})
            profile = user.get("profile", {})
            display_name = (
                profile.get("display_name")
                or profile.get("real_name")
                or user.get("real_name")
                or user.get("name")
                or user_id
            )
            self._user_cache[user_id] = (display_name, now)
            return display_name

        except SlackApiError:
            self._user_cache[user_id] = (user_id, now)
            return user_id
        except Exception:
            return user_id

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _ts_to_jst(ts: str) -> str:
        """Convert Slack timestamp to JST datetime string."""
        if not ts:
            return ""
        try:
            epoch = float(ts.split(".")[0])
            dt = datetime.fromtimestamp(epoch, tz=JST)
            return dt.strftime("%Y-%m-%d %H:%M")
        except (ValueError, OSError):
            return ts
