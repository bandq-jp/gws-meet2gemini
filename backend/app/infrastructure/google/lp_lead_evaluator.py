"""
LP流入の有効リード/TCV判定・チャネル分類ロジック.

GAS側のスプシ数式 + identifySource_() / classifyInflowSource() と同じロジックを
Pythonで再現。これにより、バックエンドがスプシと同じ判定結果を返す。
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, urlparse


# === 有効リード/TCV基準（デフォルト値、スプシの有効リードTCV要件シートで上書き可能） ===

DEFAULT_VALID_LOCATIONS = [
    "東京都", "埼玉県", "神奈川県", "千葉県",
    "大阪府", "福岡県", "北海道", "広島県", "愛知県", "リモート",
]

DEFAULT_MIN_AGE = 23
DEFAULT_MAX_AGE = 32


def calc_age(birthdate_str: str) -> Optional[int]:
    """生年(4桁) or 生年月日 → 現在の年齢を計算.

    スプシからの値は float(2001.0) や int(2001) で来ることがあるため、
    小数点以下を除去して処理する。
    """
    if not birthdate_str:
        return None

    bd = birthdate_str.strip()
    now = datetime.now()

    # float表記を整数化: "2001.0" → "2001"
    if re.match(r"^\d+\.\d+$", bd):
        try:
            bd = str(int(float(bd)))
        except (ValueError, OverflowError):
            pass

    # 4桁の年のみ
    if re.match(r"^\d{4}$", bd):
        birth_year = int(bd)
        if birth_year < 1900 or birth_year > now.year:
            return None
        return now.year - birth_year

    # YYYY-MM-DD or YYYY/MM/DD
    m = re.match(r"^(\d{4})[-/](\d{1,2})[-/](\d{1,2})", bd)
    if m:
        try:
            birth = datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            age = now.year - birth.year
            if (now.month, now.day) < (birth.month, birth.day):
                age -= 1
            return age
        except ValueError:
            return None

    return None


def is_valid_lead(
    age: Optional[int],
    locations: str,
    criteria: Optional[Dict[str, Any]] = None,
) -> bool:
    """有効リード判定: 年齢 + 勤務地."""
    min_age = (criteria or {}).get("min_age", DEFAULT_MIN_AGE)
    max_age = (criteria or {}).get("max_age", DEFAULT_MAX_AGE)
    valid_locs = (criteria or {}).get("locations", DEFAULT_VALID_LOCATIONS)

    if age is None:
        return False

    age_ok = min_age <= age <= max_age

    user_locs = [loc.strip() for loc in locations.split(",") if loc.strip()]
    location_ok = any(loc in valid_locs for loc in user_locs)

    return age_ok and location_ok


def is_tcv(
    age: Optional[int],
    locations: str,
    salesexp: str,
    criteria: Optional[Dict[str, Any]] = None,
) -> bool:
    """TCV判定: 有効リード基準 + 営業/人材経験."""
    if not is_valid_lead(age, locations, criteria):
        return False
    return salesexp.strip() == "はい"


def classify_channel(parent_path: str) -> str:
    """parentPathからチャネルを分類.

    GAS identifySource_() / classifyInflowSource() と同じロジック。
    """
    path = (parent_path or "").split("?")[0].strip().lower()

    if path.startswith("/meta"):
        return "meta"
    if path.startswith("/media"):
        return "media"
    if any(path.startswith(p) for p in ["/cp_a", "/750", "/speed", "/consultant"]):
        return "ad"
    if path.startswith("/jobs"):
        return "jobs"
    if path.startswith("/form") or path.startswith("/list_form"):
        return "other_lp"
    if path.startswith("/do_not") or path.startswith("/no-use"):
        return "test"
    if path in ("", "/"):
        return "direct"

    return "other"


def is_test_row(fullname: str, email: str) -> bool:
    """テスト行かどうかを判定."""
    if "テスト" in fullname or "てすと" in fullname:
        return True
    email_lower = email.lower()
    if "test" in email_lower:
        return True
    if email_lower.endswith("@bandq.jp"):
        return True
    return False


def extract_utm_params(parent_path: str) -> Dict[str, str]:
    """parentPathからUTMパラメータを抽出."""
    try:
        parsed = urlparse(parent_path if "?" in parent_path else f"https://dummy{parent_path}")
        params = parse_qs(parsed.query)
        return {
            "utm_source": params.get("utm_source", [""])[0],
            "utm_medium": params.get("utm_medium", [""])[0],
            "utm_campaign": params.get("utm_campaign", [""])[0],
            "utm_content": params.get("utm_content", [""])[0],
            "utm_term": params.get("utm_term", [""])[0],
            "utm_adset": params.get("utm_adset", [""])[0],
        }
    except Exception:
        return {}
