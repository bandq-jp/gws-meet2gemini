from __future__ import annotations
import re
import unicodedata
from typing import Optional


class CandidateTitleMatcher:
    """Extract and compare candidate names from meeting titles.

    - Optionally uses a configurable regex to extract a candidate name from the
      Google Docs title. If no regex is provided, the whole title is treated as
      the candidate name candidate (safe default).
    - Performs strict equality on normalized strings ("100% match").
    - Normalization: NFKC + lowercase + trim + compress internal spaces.
    """

    def __init__(self, title_regex: Optional[str] = None) -> None:
        self.title_regex = title_regex
        self._compiled: Optional[re.Pattern[str]] = None
        if title_regex:
            try:
                self._compiled = re.compile(title_regex)
            except re.error:
                # Fail closed: ignore invalid regex and treat as no-regex
                self._compiled = None

    @staticmethod
    def _normalize(value: Optional[str]) -> str:
        if not value:
            return ""
        # NFKC converts full-width <-> half-width where appropriate
        v = unicodedata.normalize("NFKC", value)
        v = v.strip().lower()
        # Remove underscores commonly used as separators in titles
        v = v.replace("_", "")
        # Compress any whitespace runs to a single space
        v = re.sub(r"\s+", " ", v)
        # Trim common surrounding punctuation
        v = re.sub(r"^[\-・:：〜~、，。\s]+|[\-・:：〜~、，。\s]+$", "", v)
        return v

    def extract_from_title(self, title: Optional[str]) -> Optional[str]:
        if not title:
            return None
        if self._compiled:
            m = self._compiled.search(title)
            if m:
                # Prefer named group 'name' if present; else group(1)
                if "name" in m.groupdict():
                    return m.group("name")
                if m.groups():
                    return m.group(1)
                # If the pattern matches but has no groups, use the match span
                return m.group(0)
            return None
        # No regex configured → try built-in heuristics
        # 1) Generic: token(s) before "様"
        patterns = [
            r"(?:(?<=~)[_\s]*([^様\-\_\s　@()]+(?:[\s　][^様\-\_\s　@()]+)*)\s*様)",
            r"([^様\-\_\s　@()]+(?:[\s　][^様\-\_\s　@()]+)*)\s*様",
            r"初回面談[^\(]*\(([^\)]+)\)",
        ]
        for pat in patterns:
            m = re.search(pat, title)
            if m and m.groups():
                return m.group(1)
        # Fallback: return entire title
        return title

    def is_exact_match(self, title: Optional[str], zoho_candidate_name: Optional[str]) -> bool:
        """Return True if normalized extracted title name equals Zoho name."""
        extracted = self.extract_from_title(title)
        if not extracted or not zoho_candidate_name:
            return False
        return self._normalize(extracted) == self._normalize(zoho_candidate_name)
