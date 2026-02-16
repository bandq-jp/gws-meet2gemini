"""
Multi-source Job Matching for Candidates.

Architecture:
1. PRIMARY: Zoho JD-hc (old: JOB / new: JobDescription) — 構造化求人票
2. SUPPLEMENTARY: Semantic search (company_chunks pgvector) — 企業カルチャー/訴求
3. COMPLEMENTARY: Gmail / Slack — 最新情報
4. INPUT: Zoho APP-hc + 面談構造化データ + 議事録全文

The ADK agent receives all data sources and produces a unified analysis.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
import uuid
from typing import Any, Dict, List, Optional

from google.adk.agents import Agent
from google.adk.runners import Runner, RunConfig
from google.adk.sessions import InMemorySessionService
from google.genai import types

from app.infrastructure.config.settings import get_settings
from app.infrastructure.adk.tools.semantic_company_tools import (
    find_companies_for_candidate,
    semantic_search_companies,
)
from app.infrastructure.zoho.client import ZohoClient
from app.infrastructure.supabase.repositories.structured_repository_impl import (
    StructuredRepositoryImpl,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Candidate Profile Builder
# ---------------------------------------------------------------------------

_STRUCTURED_FIELD_MAP = {
    "transfer_reasons": "転職検討理由",
    "transfer_trigger": "きっかけ",
    "transfer_priorities": "転職軸",
    "desired_timing": "希望時期",
    "desired_industry": "希望業界",
    "desired_position": "希望職種",
    "current_company": "現職企業",
    "current_duties": "現職業務内容",
    "career_history": "職歴サマリー",
    "current_salary": "現年収",
    "desired_first_year_salary": "初年度希望年収",
    "personality_traits": "人物像",
    "strengths": "強み",
    "concerns": "懸念点",
    "experience_industry": "経験業界",
    "experience_field_hr": "HR分野経験",
    "industry_reason": "業界希望理由",
    "position_industry_reason": "職種希望理由",
    "ca_ra_focus": "CA/RA配分",
    "career_vision": "キャリアビジョン",
    "business_vision": "ビジネスビジョン",
    "remote_time_memo": "リモートワーク希望",
    "culture_scale_memo": "企業規模・カルチャー",
}


def _build_candidate_context(
    zoho_record: Dict[str, Any],
    structured_outputs: List[Dict[str, Any]],
    transcripts: List[Dict[str, Any]],
    jd_results: List[Dict[str, Any]],
    overrides: Optional[Dict[str, Any]] = None,
) -> str:
    """Build comprehensive candidate context for the ADK agent."""
    parts: List[str] = []

    # --- Section 1: Zoho CRM 基本情報 ---
    parts.append("# 候補者プロフィール（Zoho CRM）\n")
    zoho_fields = {
        "Name": "氏名", "field15": "年齢", "field17": "現年収（万円）",
        "field20": "希望年収（万円）", "customer_status": "ステータス",
        "field14": "流入経路", "field66": "転職希望時期",
        "field85": "職歴", "field131": "現職業務内容",
        "field58": "転職検討理由", "field96": "転職きっかけ",
        "transfer_priorities": "転職軸",
        "desired_industry": "希望業界", "desired_position": "希望職種",
        "field46": "現職の良いところ", "field56": "現職の悪いところ",
        "career_vision": "キャリアビジョン",
    }
    for api_name, label in zoho_fields.items():
        val = zoho_record.get(api_name)
        if val:
            if isinstance(val, list):
                parts.append(f"- {label}: {', '.join(str(v) for v in val)}")
            elif isinstance(val, dict) and "name" in val:
                parts.append(f"- {label}: {val['name']}")
            else:
                parts.append(f"- {label}: {val}")

    # --- Section 2: 面談構造化データ（全件）---
    if structured_outputs:
        parts.append("\n# 面談抽出データ（構造化）\n")
        for i, so in enumerate(structured_outputs):
            data = so.get("data", {})
            if not data:
                continue
            meeting_title = so.get("title", f"面談{i+1}")
            parts.append(f"\n## {meeting_title}\n")
            for key, label in _STRUCTURED_FIELD_MAP.items():
                val = data.get(key)
                if val:
                    if isinstance(val, list):
                        parts.append(f"- {label}: {', '.join(str(v) for v in val)}")
                    else:
                        parts.append(f"- {label}: {val}")

    # --- Section 3: 議事録全文（トランクケート付き）---
    if transcripts:
        parts.append("\n# 面談議事録（全文）\n")
        for t in transcripts:
            title = t.get("title", "議事録")
            dt = t.get("meeting_datetime", "")
            text = t.get("text_content", "")
            if not text:
                continue
            # 最大8000文字に制限（合計でmax_output_tokensに収まるように）
            if len(text) > 8000:
                text = text[:8000] + "\n...(以下省略)"
            parts.append(f"\n## {title} ({dt})\n")
            parts.append(text)

    # --- Section 4: Zoho JD検索結果 ---
    if jd_results:
        parts.append(f"\n# Zoho求人票データ（{len(jd_results)}件）\n")
        for jd in jd_results:
            name = jd.get("name") or "求人名不明"
            company = jd.get("company") or "企業不明"
            parts.append(f"\n## {company} / {name}")
            jd_display_fields = {
                "salary_min": "年収下限", "salary_max": "年収上限",
                "expected_salary": "理論年収", "location": "勤務地",
                "remote": "リモート", "is_remote": "リモート可",
                "flex": "フレックス", "overtime": "残業",
                "age_max": "年齢上限", "education": "学歴",
                "exp_count_max": "経験社数上限",
                "hr_experience": "人材業界経験",
                "position": "ポジション", "category": "カテゴリ",
                "class_level": "クラス", "tags": "タグ",
                "hiring_appetite": "採用温度感",
                "is_open": "オープン", "fee": "Fee",
                "job_details": "業務内容",
                "ideal_candidate": "求める人物像",
                "hiring_background": "募集背景",
                "org_structure": "組織構成",
                "after_career": "その後のキャリア",
                "benefits": "福利厚生",
                "company_features": "会社特徴",
            }
            for key, label in jd_display_fields.items():
                val = jd.get(key)
                if val is not None and val != "" and val != []:
                    if isinstance(val, list):
                        parts.append(f"  - {label}: {', '.join(str(v) for v in val)}")
                    elif isinstance(val, bool):
                        parts.append(f"  - {label}: {'あり' if val else 'なし'}")
                    else:
                        text_val = str(val)
                        if len(text_val) > 500:
                            text_val = text_val[:500] + "..."
                        parts.append(f"  - {label}: {text_val}")

    # --- Section 5: Overrides ---
    if overrides:
        parts.append("\n# CA追加情報\n")
        if overrides.get("transfer_reasons"):
            parts.append(f"- 転職理由(補足): {overrides['transfer_reasons']}")
        if overrides.get("desired_salary"):
            parts.append(f"- 希望年収(上書き): {overrides['desired_salary']}万円")
        if overrides.get("desired_locations"):
            parts.append(f"- 希望勤務地(上書き): {', '.join(overrides['desired_locations'])}")

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Agent Builder
# ---------------------------------------------------------------------------

_AGENT_INSTRUCTION = """あなたはCA（キャリアアドバイザー）を支援する求人マッチングの専門家です。

## あなたの役割
候補者のプロフィール・面談内容・求人票データを多角的に分析し、最適な求人を推薦するレポートを作成する。

## 提供されるデータ
1. **候補者プロフィール（Zoho CRM）**: 基本属性・転職理由・希望条件
2. **面談構造化データ**: AI抽出された転職理由・希望・人物像
3. **面談議事録全文**: 候補者との会話の詳細（ニュアンス・温度感を読み取る）
4. **Zoho求人票データ**: 構造化された求人情報（年収・勤務地・要件等）

## 分析の手順

### Step 1: 候補者の深層理解
議事録全文と構造化データから以下を分析:
- **転職の本質的な動機**（表面的な理由だけでなく、議事録から読み取れる本音）
- **譲れない条件** vs **あれば嬉しい条件**
- **性格・志向性**（チャレンジ志向？安定志向？マネジメント志向？）
- **懸念点・NG条件**
- **CAが気をつけるべきポイント**

### Step 2: 求人票との構造マッチング
提供されたZoho求人票データから、候補者条件にマッチする求人を特定:
- 年齢要件の適合
- 年収レンジの適合
- 勤務地の適合
- ポジション・経験の適合
- 採用温度感（「緊急」「通常」は優先）

### Step 3: セマンティック補完検索
`semantic_search_companies` を使って、求人票だけでは分からない情報を補完:
- 企業カルチャーが候補者の性格に合うか
- 成長環境・WLB等の候補者のソフトニーズにマッチするか

### Step 4: 最新情報の確認（任意）
必要に応じて `search_gmail` や `search_slack_messages` で最新の求人情報や社内評判を確認。
特に以下の場合に有効:
- 求人票の採用温度感が不明な場合
- 条件変更の可能性がある場合
- 企業の最新動向を確認したい場合

### Step 5: レポート作成
以下のJSON形式で結果を出力してください。JSONブロック以外のテキストは出力しないでください。

```json
{
  "analysis_text": "【候補者分析】転職動機・志向性・重要条件の分析サマリー。議事録から読み取った本音やCAへのアドバイスも含む（5-10文）",
  "recommended_jobs": [
    {
      "job_name": "求人名（Zoho求人票のName）",
      "company_name": "企業名",
      "match_score": 0.85,
      "recommendation_reason": "この求人を推薦する理由。候補者の具体的な希望・志向と求人の特徴を紐づけて説明（3-5文）",
      "appeal_points": ["CAが候補者に訴求する際のポイント1", "ポイント2", "ポイント3"],
      "concerns": ["この求人の懸念点やCAが注意すべき点"],
      "salary_range": "500-700万円",
      "location": "東京都",
      "remote": "週2-3",
      "position": "CA",
      "hiring_appetite": "緊急",
      "source": "zoho_jd"
    }
  ],
  "total_found": 10,
  "data_sources_used": ["zoho_jd", "semantic", "gmail", "slack"]
}
```

## 重要ルール
- **求人票データが最優先**: Zoho求人票に載っている求人は必ず評価対象にする
- **match_score の基準**: 1.0=完全マッチ, 0.8+=強く推薦, 0.6+=推薦, 0.4+=条件付き推薦
- **議事録の活用**: 構造化データにない情報（候補者の発言のニュアンス、迷い、本音）を積極的に活用
- **CAへの示唆**: recommendation_reason にはCAが面談で使える具体的な訴求文言を含める
- **懸念点も正直に**: concerns に年齢超過、年収ギャップ等のリスクを記載
- **結果はmatch_scoreの高い順にソート**
- **推薦は最大10件**
"""


def _build_job_match_agent(settings) -> Agent:
    """Build the multi-source job matching agent."""
    tools = [find_companies_for_candidate, semantic_search_companies]

    # Add company DB strict search tools
    try:
        if settings.company_db_spreadsheet_id:
            from app.infrastructure.adk.tools.company_db_tools import ADK_COMPANY_DB_TOOLS
            tools.extend(ADK_COMPANY_DB_TOOLS)
    except Exception:
        pass

    # Add Gmail tools
    try:
        from app.infrastructure.adk.tools.workspace_tools import (
            search_gmail, get_email_detail,
        )
        tools.extend([search_gmail, get_email_detail])
    except Exception as e:
        logger.debug("[job_match] Gmail tools not available: %s", e)

    # Add Slack tools
    try:
        from app.infrastructure.adk.tools.slack_tools import (
            search_slack_messages, search_company_in_slack,
        )
        tools.extend([search_slack_messages, search_company_in_slack])
    except Exception as e:
        logger.debug("[job_match] Slack tools not available: %s", e)

    return Agent(
        name="JobMatchAgent",
        model=settings.adk_sub_agent_model or "gemini-3-flash-preview",
        description="多角的な求人マッチング分析（Zoho JD + セマンティック + Mail + Slack）",
        instruction=_AGENT_INSTRUCTION,
        tools=tools,
        generate_content_config=types.GenerateContentConfig(
            max_output_tokens=8192,
            temperature=0.5,
        ),
    )


# ---------------------------------------------------------------------------
# Response Parsing & Normalization
# ---------------------------------------------------------------------------

def _parse_agent_response(text: str) -> Dict[str, Any]:
    """Parse the agent's JSON response from its text output."""
    # Try to extract JSON from markdown code block
    json_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass

    # Try to find raw JSON object
    brace_start = text.find("{")
    if brace_start >= 0:
        depth = 0
        for i in range(brace_start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[brace_start : i + 1])
                    except json.JSONDecodeError:
                        break

    return {
        "analysis_text": text,
        "recommended_jobs": [],
        "total_found": 0,
    }


def _safe_int(val: Any) -> Optional[int]:
    if val is None:
        return None
    try:
        cleaned = str(val).replace("万円", "").replace("万", "").replace(",", "").replace(" ", "").strip()
        return int(cleaned) if cleaned else None
    except (ValueError, TypeError):
        return None


def _normalize_job_results(jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Normalize job match results from LLM output."""
    normalized = []
    for j in jobs:
        normalized.append({
            "job_name": str(j.get("job_name") or j.get("company_name", "")),
            "company_name": str(j.get("company_name", "")),
            "match_score": float(j.get("match_score", 0)) if j.get("match_score") is not None else 0.0,
            "recommendation_reason": j.get("recommendation_reason"),
            "appeal_points": j.get("appeal_points") or [],
            "concerns": j.get("concerns") or [],
            "salary_range": str(j.get("salary_range", "")) if j.get("salary_range") else None,
            "location": str(j.get("location", "")) if j.get("location") else None,
            "remote": str(j.get("remote", "")) if j.get("remote") else None,
            "position": str(j.get("position", "")) if j.get("position") else None,
            "hiring_appetite": str(j.get("hiring_appetite", "")) if j.get("hiring_appetite") else None,
            "source": str(j.get("source", "unknown")),
        })
    return normalized


# ---------------------------------------------------------------------------
# Agent Runner
# ---------------------------------------------------------------------------

async def _run_agent(agent: Agent, user_message: str) -> str:
    """Run the ADK agent and collect text response."""
    session_service = InMemorySessionService()
    runner = Runner(
        agent=agent,
        app_name="job_match",
        session_service=session_service,
    )

    session = await session_service.create_session(
        app_name="job_match",
        user_id="system",
        session_id=str(uuid.uuid4()),
    )

    user_content = types.Content(
        role="user",
        parts=[types.Part(text=user_message)],
    )

    run_config = RunConfig(max_llm_calls=30)

    collected_text = []
    async for event in runner.run_async(
        user_id="system",
        session_id=session.id,
        new_message=user_content,
        run_config=run_config,
    ):
        if hasattr(event, "content") and event.content:
            content = event.content
            if hasattr(content, "parts"):
                for part in content.parts:
                    if hasattr(part, "text") and part.text:
                        collected_text.append(part.text)

    return "\n".join(collected_text)


# ---------------------------------------------------------------------------
# Use Case
# ---------------------------------------------------------------------------

class MatchCandidateJobsUseCase:
    def __init__(self):
        self.zoho_client = ZohoClient()
        self.structured_repo = StructuredRepositoryImpl()
        self.settings = get_settings()

    def execute(
        self,
        record_id: str,
        overrides: Optional[Dict[str, Any]] = None,
        jd_module_version: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute multi-source job matching for a candidate.

        Args:
            record_id: Zoho APP-hc record ID
            overrides: Optional overrides (transfer_reasons, desired_salary, desired_locations, limit)
            jd_module_version: "old" (JOB) or "new" (JobDescription). None = settings default.

        Returns:
            JobMatchResponse dict
        """
        jd_version = jd_module_version or self.settings.zoho_jd_module_version

        # ── 1. Candidate data collection ──
        zoho_record = self.zoho_client.get_app_hc_record(record_id)
        if not zoho_record:
            return {"error": "候補者レコードが見つかりません"}

        # 全構造化データ（複数面談分）
        structured_outputs = self.structured_repo.get_all_by_zoho_record_id(record_id)

        # 議事録全文
        transcripts = self.structured_repo.get_full_transcripts_by_zoho_record_id(record_id)

        # ── 2. Zoho JD search (PRIMARY) ──
        age = _safe_int(zoho_record.get("field15"))
        desired_salary = _safe_int(
            (overrides or {}).get("desired_salary") or zoho_record.get("field20")
        )

        jd_results = self.zoho_client.search_jd_for_candidate(
            age=age,
            desired_salary=desired_salary,
            version=jd_version,
            limit=50,
        )
        logger.info(
            "[job_match] Zoho JD search (%s): %d results for record %s",
            jd_version, len(jd_results), record_id,
        )

        # ── 3. Build context for agent ──
        context = _build_candidate_context(
            zoho_record=zoho_record,
            structured_outputs=structured_outputs,
            transcripts=transcripts,
            jd_results=jd_results,
            overrides=overrides,
        )

        # ── 4. Run ADK agent ──
        agent = _build_job_match_agent(self.settings)

        try:
            loop = asyncio.new_event_loop()
            try:
                response_text = loop.run_until_complete(_run_agent(agent, context))
            finally:
                loop.close()
        except Exception as e:
            logger.error("[job_match] ADK agent failed: %s", e)
            return self._fallback_jd_match(zoho_record, jd_results)

        # ── 5. Parse & normalize ──
        parsed = _parse_agent_response(response_text)

        # Support both "recommended_jobs" (new) and "recommended_companies" (legacy)
        raw_jobs = parsed.get("recommended_jobs") or parsed.get("recommended_companies", [])
        jobs = _normalize_job_results(raw_jobs)

        candidate_profile = {
            "name": zoho_record.get("Name"),
            "age": age,
            "current_salary": _safe_int(zoho_record.get("field17")),
            "desired_salary": desired_salary,
            "status": zoho_record.get("customer_status"),
        }

        return {
            "candidate_profile": candidate_profile,
            "recommended_jobs": jobs,
            "total_found": parsed.get("total_found", len(jobs)),
            "analysis_text": parsed.get("analysis_text"),
            "data_sources_used": parsed.get("data_sources_used", ["zoho_jd"]),
            "jd_module_version": jd_version,
        }

    def _fallback_jd_match(
        self,
        zoho_record: Dict[str, Any],
        jd_results: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Fallback: return JD results without agent analysis."""
        logger.info("[job_match] Using fallback JD match (no agent)")

        age = _safe_int(zoho_record.get("field15"))
        desired_salary = _safe_int(zoho_record.get("field20"))

        jobs = []
        for jd in jd_results[:10]:
            salary_min = jd.get("salary_min")
            salary_max = jd.get("salary_max")
            salary_range = None
            if salary_min or salary_max:
                salary_range = f"{salary_min or '?'}-{salary_max or '?'}万円"

            jobs.append({
                "job_name": jd.get("name") or "",
                "company_name": jd.get("company") or "",
                "match_score": 0.5,
                "recommendation_reason": None,
                "appeal_points": [],
                "concerns": [],
                "salary_range": salary_range,
                "location": jd.get("location"),
                "remote": str(jd["remote"]) if jd.get("remote") is not None else None,
                "position": str(jd["position"]) if jd.get("position") else None,
                "hiring_appetite": str(jd["hiring_appetite"]) if jd.get("hiring_appetite") else None,
                "source": "zoho_jd",
            })

        return {
            "candidate_profile": {
                "name": zoho_record.get("Name"),
                "age": age,
                "current_salary": _safe_int(zoho_record.get("field17")),
                "desired_salary": desired_salary,
                "status": zoho_record.get("customer_status"),
            },
            "recommended_jobs": jobs,
            "total_found": len(jobs),
            "analysis_text": "Zoho求人票データによる自動マッチング結果です（ADKエージェント分析は利用できませんでした）",
            "data_sources_used": ["zoho_jd"],
            "jd_module_version": self.settings.zoho_jd_module_version,
        }
