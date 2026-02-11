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

    @staticmethod
    def _normalize_spaceless(value: Optional[str]) -> str:
        """Normalize and remove ALL whitespace for space-insensitive comparison.

        Japanese names often have inconsistent spacing between family and given
        names (e.g. "山田 太郎" vs "山田太郎" vs "山田　太郎").
        """
        if not value:
            return ""
        v = unicodedata.normalize("NFKC", value)
        v = v.strip().lower()
        v = v.replace("_", "")
        # Remove ALL whitespace (half-width, full-width, tabs, etc.)
        v = re.sub(r"[\s　]+", "", v)
        v = re.sub(r"^[\-・:：〜~、，。]+|[\-・:：〜~、，。]+$", "", v)
        return v

    # Common time prefix in meeting titles: "JP20:30", "JP9:00~ ", "JP18:00〜"
    _TIME_PREFIX_RE = re.compile(
        r"^[\s　]*JP\d{1,2}:\d{2}\s*[~〜～]?\s*", re.IGNORECASE
    )
    # Noise prefixes that sometimes appear before the name: （仮）, (仮), ※, etc.
    _NOISE_PREFIX_RE = re.compile(
        r"^[（(]\s*仮\s*[）)]\s*"
    )

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

        # Strip time prefix (e.g. "JP20:30~ ", "JP9:00〜") before heuristics
        cleaned = self._TIME_PREFIX_RE.sub("", title).strip()
        if not cleaned:
            cleaned = title

        # No regex configured → try built-in heuristics
        # 1) Token(s) before "様" (after ~ or tilde variants)
        patterns = [
            r"(?:(?<=[~〜～])[_\s　]*([^様\-\_\s　@()（）]+(?:[\s　]+[^様\-\_\s　@()（）]+)*)\s*様)",
            r"([^様\-\_\s　@()（）]+(?:[\s　]+[^様\-\_\s　@()（）]+)*)\s*様",
            r"初回面談[^\(（]*[(\（]([^\)）]+)[)\）]",
        ]
        for pat in patterns:
            m = re.search(pat, cleaned)
            if m and m.groups():
                name = m.group(1)
                # Strip noise prefixes like （仮）
                name = self._NOISE_PREFIX_RE.sub("", name).strip()
                if name:
                    return name
        # Fallback: return entire title
        return title

    def is_exact_match(self, title_or_extracted: Optional[str], zoho_candidate_name: Optional[str], *, pre_extracted: bool = False) -> bool:
        """Return True if normalized extracted title name equals Zoho name.

        Uses two-stage comparison:
        1. Standard normalization (spaces compressed to single space)
        2. Space-insensitive normalization (all spaces removed)

        This handles Japanese name spacing inconsistencies like
        "山田 太郎" vs "山田太郎" vs "山田　太郎".

        Args:
            title_or_extracted: Meeting title or pre-extracted name.
            zoho_candidate_name: Candidate name from Zoho CRM.
            pre_extracted: If True, title_or_extracted is already the extracted name.
        """
        extracted = title_or_extracted if pre_extracted else self.extract_from_title(title_or_extracted)
        if not extracted or not zoho_candidate_name:
            return False
        # Stage 1: standard normalized comparison
        if self._normalize(extracted) == self._normalize(zoho_candidate_name):
            return True
        # Stage 2: space-insensitive comparison (Japanese name spacing)
        return self._normalize_spaceless(extracted) == self._normalize_spaceless(zoho_candidate_name)

    def get_search_variations(self, name: str) -> list[str]:
        """Generate name variations to try in Zoho search.

        For Japanese names, spacing between family and given names is
        inconsistent. Returns unique variations ordered by likelihood.
        """
        variations: list[str] = []
        seen: set[str] = set()

        def _add(v: str) -> None:
            v = v.strip()
            if v and v not in seen:
                seen.add(v)
                variations.append(v)

        # 1. Original (raw extracted)
        _add(name)

        # 2. NFKC normalized with compressed spaces
        normalized = self._normalize(name)
        _add(normalized)

        # 3. Without any spaces (common in Zoho data)
        spaceless = re.sub(r"[\s　]+", "", unicodedata.normalize("NFKC", name).strip())
        _add(spaceless)

        # 4. With single space between chars if spaceless had 2+ chars
        #    (try to reconstruct "姓 名" from "姓名" — only for short names)
        #    Not feasible without knowing the split point, skip.

        return variations
