"""
Match candidate to job openings using ADK CompanyDatabaseAgent.

Uses Gemini + semantic search to analyze candidate profile and recommend
matching companies with detailed reasoning.
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


def _build_job_match_agent(settings) -> Agent:
    """Build a dedicated agent for job matching analysis."""
    tools = [find_companies_for_candidate, semantic_search_companies]

    # Optionally add strict search tools
    try:
        if settings.company_db_spreadsheet_id:
            from app.infrastructure.adk.tools.company_db_tools import ADK_COMPANY_DB_TOOLS
            tools.extend(ADK_COMPANY_DB_TOOLS)
    except Exception:
        pass

    instruction = """あなたはCA（キャリアアドバイザー）を支援する求人マッチングの専門家です。

## タスク
候補者のプロフィール情報を分析し、最適な求人をセマンティック検索で見つけ、CA向けに推薦レポートを作成してください。

## 手順

### Step 1: 候補者分析
ユーザーから提供される候補者プロフィールの以下を分析:
- 転職理由・転職軸（最重要）
- 希望年収・現年収
- 希望勤務地
- 年齢
- 職歴・スキル
- 性格特性・懸念点

### Step 2: セマンティック検索
`find_companies_for_candidate` を使い、転職理由をベースに企業をマッチング。
- transfer_reasons には転職理由・転職軸・希望条件を組み合わせた文章を渡す
- age, desired_salary, desired_locations も指定して精度向上
- limit は10以上に設定

追加で `semantic_search_companies` を使い、別角度でも検索:
- 職歴やスキルに関連する企業
- 候補者の懸念点を解消できる企業

### Step 3: レポート作成
以下のJSON形式で結果を出力してください。JSONブロック以外のテキストは出力しないでください。

```json
{
  "analysis_text": "候補者の特徴と転職ニーズの分析サマリー（3-5文）",
  "recommended_companies": [
    {
      "company_name": "企業名",
      "match_score": 0.85,
      "recommendation_reason": "この候補者に推薦する理由（2-3文）",
      "appeal_points": ["候補者への訴求ポイント1", "訴求ポイント2"],
      "age_limit": null,
      "max_salary": null,
      "locations": null,
      "remote": null
    }
  ],
  "total_found": 10
}
```

## 重要ルール
- 必ずツールを使って検索すること（推測で企業名を出さない）
- match_score はツールの similarity_score をそのまま使用
- recommendation_reason は候補者の具体的な希望と企業の特徴を紐づけて記述
- appeal_points はCAが候補者に企業を紹介する際に使える訴求ポイント
- 結果は match_score の高い順にソート
- 最大10社まで推薦
"""

    return Agent(
        name="JobMatchAgent",
        model=settings.adk_sub_agent_model or "gemini-3-flash-preview",
        description="候補者プロフィールから最適な求人を分析・推薦",
        instruction=instruction,
        tools=tools,
        generate_content_config=types.GenerateContentConfig(
            max_output_tokens=8192,
            temperature=0.7,
        ),
    )


def _build_candidate_profile_text(
    zoho_record: Dict[str, Any],
    structured_outputs: List[Dict[str, Any]],
    overrides: Optional[Dict[str, Any]] = None,
) -> str:
    """Build a text description of the candidate for the agent."""
    parts = ["## 候補者プロフィール\n"]

    # Zoho data
    name = zoho_record.get("Name", "不明")
    parts.append(f"- 氏名: {name}")

    age = zoho_record.get("field15")
    if age:
        parts.append(f"- 年齢: {age}歳")

    current_salary = zoho_record.get("field17")
    if current_salary:
        parts.append(f"- 現年収: {current_salary}万円")

    desired_salary = zoho_record.get("field20")
    if desired_salary:
        parts.append(f"- 希望年収: {desired_salary}万円")

    status = zoho_record.get("customer_status")
    if status:
        parts.append(f"- ステータス: {status}")

    channel = zoho_record.get("field14")
    if channel:
        parts.append(f"- 流入経路: {channel}")

    desired_timing = zoho_record.get("field66")
    if desired_timing:
        parts.append(f"- 転職希望時期: {desired_timing}")

    career = zoho_record.get("field85")
    if career:
        parts.append(f"- 職歴: {career}")

    # Structured output data (from interview transcripts)
    if structured_outputs:
        latest = structured_outputs[0].get("data", {})
        parts.append("\n## 面談抽出データ\n")

        field_map = {
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
        }

        for key, label in field_map.items():
            value = latest.get(key)
            if value:
                if isinstance(value, list):
                    parts.append(f"- {label}: {', '.join(str(v) for v in value)}")
                else:
                    parts.append(f"- {label}: {value}")

    # Overrides
    if overrides:
        if overrides.get("transfer_reasons"):
            parts.append(f"\n## 追加情報\n- 転職理由(補足): {overrides['transfer_reasons']}")
        if overrides.get("desired_salary"):
            parts.append(f"- 希望年収(上書き): {overrides['desired_salary']}万円")
        if overrides.get("desired_locations"):
            parts.append(f"- 希望勤務地(上書き): {', '.join(overrides['desired_locations'])}")

    parts.append("\n\n上記プロフィールをもとに、最適な求人を検索・分析し、推薦レポートをJSON形式で出力してください。")

    return "\n".join(parts)


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
        # Find matching closing brace
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

    # Fallback: return text as analysis
    return {
        "analysis_text": text,
        "recommended_companies": [],
        "total_found": 0,
    }


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

    run_config = RunConfig(
        max_llm_calls=20,
    )

    collected_text = []

    async for event in runner.run_async(
        user_id="system",
        session_id=session.id,
        new_message=user_content,
        run_config=run_config,
    ):
        # Collect text from agent response
        if hasattr(event, "content") and event.content:
            content = event.content
            if hasattr(content, "parts"):
                for part in content.parts:
                    if hasattr(part, "text") and part.text:
                        collected_text.append(part.text)

    return "\n".join(collected_text)


class MatchCandidateJobsUseCase:
    def __init__(self):
        self.zoho_client = ZohoClient()
        self.structured_repo = StructuredRepositoryImpl()
        self.settings = get_settings()

    def execute(
        self,
        record_id: str,
        overrides: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Execute job matching for a candidate.

        Args:
            record_id: Zoho record ID
            overrides: Optional overrides for transfer_reasons, desired_salary, desired_locations

        Returns:
            JobMatchResponse dict
        """
        # 1. Fetch Zoho record
        zoho_record = self.zoho_client.get_app_hc_record(record_id)
        if not zoho_record:
            return {"error": "候補者レコードが見つかりません"}

        # 2. Fetch structured outputs
        structured_outputs = self.structured_repo.get_all_by_zoho_record_id(record_id)

        # 3. Build candidate profile text
        profile_text = _build_candidate_profile_text(zoho_record, structured_outputs, overrides)

        # 4. Build and run ADK agent
        agent = _build_job_match_agent(self.settings)

        try:
            # Run async agent in sync context
            loop = asyncio.new_event_loop()
            try:
                response_text = loop.run_until_complete(_run_agent(agent, profile_text))
            finally:
                loop.close()
        except Exception as e:
            logger.error("[match_candidate_jobs] ADK agent failed: %s", e)
            # Fallback: direct semantic search without agent
            return self._fallback_semantic_search(zoho_record, structured_outputs, overrides)

        # 5. Parse response
        parsed = _parse_agent_response(response_text)

        # 6. Build candidate profile for response
        candidate_profile = {
            "name": zoho_record.get("Name"),
            "age": zoho_record.get("field15"),
            "current_salary": zoho_record.get("field17"),
            "desired_salary": zoho_record.get("field20"),
            "status": zoho_record.get("customer_status"),
        }

        return {
            "candidate_profile": candidate_profile,
            "recommended_companies": parsed.get("recommended_companies", []),
            "total_found": parsed.get("total_found", 0),
            "analysis_text": parsed.get("analysis_text"),
        }

    def _fallback_semantic_search(
        self,
        zoho_record: Dict[str, Any],
        structured_outputs: List[Dict[str, Any]],
        overrides: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Fallback: direct semantic search without ADK agent."""
        logger.info("[match_candidate_jobs] Using fallback semantic search")

        # Build search query
        reasons_parts = []
        if overrides and overrides.get("transfer_reasons"):
            reasons_parts.append(overrides["transfer_reasons"])

        if structured_outputs:
            latest = structured_outputs[0].get("data", {})
            for key in ["transfer_reasons", "transfer_priorities", "desired_industry"]:
                val = latest.get(key)
                if val:
                    if isinstance(val, list):
                        reasons_parts.append(", ".join(str(v) for v in val))
                    else:
                        reasons_parts.append(str(val))

        if not reasons_parts:
            reasons_parts.append("転職希望")

        transfer_reasons = ". ".join(reasons_parts)

        age = zoho_record.get("field15")
        desired_salary = overrides.get("desired_salary") if overrides else None
        if not desired_salary:
            desired_salary = zoho_record.get("field20")
        desired_locations = overrides.get("desired_locations") if overrides else None

        limit = (overrides or {}).get("limit", 10)

        result = find_companies_for_candidate(
            transfer_reasons=transfer_reasons,
            age=int(age) if age else None,
            desired_salary=int(desired_salary) if desired_salary else None,
            desired_locations=desired_locations,
            limit=limit,
        )

        companies = []
        for c in result.get("recommended_companies", []):
            companies.append({
                "company_name": c.get("company_name", ""),
                "match_score": c.get("match_score", 0),
                "recommendation_reason": None,
                "appeal_points": c.get("appeal_points", []),
                "age_limit": c.get("age_limit"),
                "max_salary": c.get("max_salary"),
                "locations": c.get("locations"),
                "remote": c.get("remote"),
            })

        candidate_profile = {
            "name": zoho_record.get("Name"),
            "age": age,
            "current_salary": zoho_record.get("field17"),
            "desired_salary": desired_salary,
            "status": zoho_record.get("customer_status"),
        }

        return {
            "candidate_profile": candidate_profile,
            "recommended_companies": companies,
            "total_found": result.get("total_found", len(companies)),
            "analysis_text": "セマンティック検索による自動マッチング結果です（ADKエージェント分析は利用できませんでした）",
        }
