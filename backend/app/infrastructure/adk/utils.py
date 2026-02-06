"""
Shared utilities for the ADK infrastructure module.
"""

from __future__ import annotations

import re

# Patterns that indicate internal/sensitive information in error messages
_SENSITIVE_PATTERNS = [
    # File paths (Unix/Windows)
    re.compile(r"(/[\w./-]+\.py\b|/[\w./-]+/site-packages/|/home/[\w./-]+|/app/[\w./-]+)"),
    # API keys / tokens (common formats)
    re.compile(r"(api[_-]?key|token|secret|password|credential)[=:\s]+\S+", re.IGNORECASE),
    re.compile(r"\b(sk-[a-zA-Z0-9]{20,}|AIza[a-zA-Z0-9_-]{35}|ghp_[a-zA-Z0-9]{36})\b"),
    # Stack trace lines
    re.compile(r'^\s*File ".*", line \d+', re.MULTILINE),
    re.compile(r"^\s*Traceback \(most recent call last\)", re.MULTILINE),
    # IP addresses and ports
    re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}(:\d+)?\b"),
    # Connection strings / DSNs
    re.compile(r"(postgresql|mysql|redis|amqp|mongodb)://\S+", re.IGNORECASE),
    # Environment variable references with values
    re.compile(r"[A-Z_]{4,}=\S+"),
]

# Generic user-facing error message
_DEFAULT_USER_ERROR = "エラーが発生しました。もう一度お試しください。"


def normalize_agent_name(name: str) -> str:
    """Convert agent name to frontend-friendly snake_case format.

    Handles acronyms: CRM, SEO, CA, WordPress.

    Examples:
        - "ZohoCRMAgent" -> "zoho_crm"
        - "AnalyticsAgent" -> "analytics"
        - "AdPlatformAgent" -> "ad_platform"
        - "SEOAgent" -> "seo"
        - "WordPressAgent" -> "wordpress"
        - "CandidateInsightAgent" -> "candidate_insight"
        - "CASupportAgent" -> "ca_support"
    """
    if name.endswith("Agent"):
        name = name[:-5]  # Remove 'Agent' suffix

    # Handle acronyms and compound words before CamelCase conversion
    name = name.replace("WordPress", "Wordpress")
    name = name.replace("CRM", "Crm")
    name = name.replace("SEO", "Seo")
    name = name.replace("CA", "Ca")

    # Convert CamelCase to snake_case
    result = []
    for i, char in enumerate(name):
        if char.isupper() and i > 0:
            result.append("_")
        result.append(char.lower())

    return "".join(result)


def sanitize_error(error_message: str) -> str:
    """Sanitize an error message to remove sensitive information.

    Removes internal file paths, API keys, stack traces, connection strings,
    and other potentially sensitive data from error messages before they are
    sent to the user.

    The full error should always be logged via the logger before calling this.

    Args:
        error_message: The raw error message string.

    Returns:
        A sanitized, user-safe error message.
    """
    if not error_message:
        return _DEFAULT_USER_ERROR

    # If any sensitive pattern is found, return the generic message
    for pattern in _SENSITIVE_PATTERNS:
        if pattern.search(error_message):
            return _DEFAULT_USER_ERROR

    # Even if no sensitive pattern matched, truncate long error messages
    # as they often contain internal details
    if len(error_message) > 200:
        return _DEFAULT_USER_ERROR

    # For short, non-sensitive error messages, return a sanitized version
    # that includes the original message for debugging context
    return f"エラーが発生しました: {error_message}"
