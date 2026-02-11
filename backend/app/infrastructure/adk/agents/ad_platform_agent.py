"""
Ad Platform Agent (ADK version) - Meta Ads integration.

Handles Meta (Facebook/Instagram) advertising analysis.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, List

from google.adk.agents import Agent
from google.adk.planners import BuiltInPlanner
from google.genai import types

from .base import SubAgentFactory

if TYPE_CHECKING:
    from app.infrastructure.config.settings import Settings

logger = logging.getLogger(__name__)


class AdPlatformAgentFactory(SubAgentFactory):
    """
    Factory for ADK Ad Platform sub-agent.

    Specializes in:
    - Campaign/AdSet/Ad performance
    - Interest targeting research
    - Audience size estimation
    - CTR, CPM, CPA, ROAS analysis
    """

    @property
    def agent_name(self) -> str:
        return "AdPlatformAgent"

    @property
    def tool_name(self) -> str:
        return "call_ad_platform_agent"

    @property
    def tool_description(self) -> str:
        return (
            "Meta広告（Facebook/Instagram）のパフォーマンス分析を実行。"
            "キャンペーン分析、インタレストターゲティング調査、"
            "オーディエンスサイズ推定、CTR/CPM/CPA/ROAS分析を担当。"
        )

    @property
    def thinking_level(self) -> str:
        return "high"

    def _get_domain_tools(
        self,
        mcp_servers: List[Any] | None = None,
        asset: dict[str, Any] | None = None,
    ) -> List[Any]:
        """
        Return MCP toolset for Meta Ads.

        Orchestrator passes pre-filtered toolsets for this domain.
        """
        if mcp_servers:
            logger.info(f"[AdPlatformAgent] Using {len(mcp_servers)} MCP toolsets")
            return list(mcp_servers)
        return []

    def _build_instructions(self) -> str:
        return """
あなたはMeta広告（Facebook/Instagram）分析のプロフェッショナルです。

## 現在の日時（日本時間）: {app:current_date}（{app:day_of_week}曜日） {app:current_time}

## 重要ルール（絶対厳守）
1. **許可を求めるな**: 即座にツールを実行
2. **推測するな**: データが必要なら必ずツールを呼び出す
3. **日付を正確に計算**: 相対日付は今日({app:current_date})から正確にYYYY-MM-DD算出。**未来の日付をuntilに絶対使用しない**。広告のcreated_time以降の日付をsinceに設定すること
4. **比較分析時は同一期間**: 対象広告とキャンペーン平均の比較は**必ず同じtime_range**
5. **breakdownは1つずつ**: 複数同時指定は非対応
6. **リンククリックベースで報告（最重要）**:
   - CTR/CPC/CVR は必ず **inline_link_clicks** ベースで計算・報告
   - `inline_link_click_ctr`(リンクCTR), `cost_per_inline_link_click`(リンクCPC) を主指標
   - `clicks`/`ctr`/`cpc`（全クリック=いいね・コメント・シェア含む）は参考値のみ
   - CVR = conversions / inline_link_clicks × 100
   - 表見出しには「CTR (リンク)」「CPC (リンク)」と明記

## CPC要因分解
リンクCPC上昇時: **CPC = CPM / (リンクCTR × 1000)**
- CPM上昇 → オークション要因（競合・時期）
- リンクCTR低下 → クリエイティブ要因（疲弊・訴求不適切）

## get_ad_image 使用ルール
- 取得画像は視覚的にコンテキストに読み込み済み（Geminiマルチモーダル分析可能）
- 結果のImage URLを `![広告画像](URL)` でmarkdownに含めてユーザーに表示
- `get_ad_creatives`のthumbnail_url(64x64)は使用しない

## 回答方針
- 主要KPIを表形式で整理（リンクCTR, リンクCPC, CPM, CPA, ROAS, Frequency）
- 前期比がある場合は変化率を計算して記載
- **必ず具体的な改善提案を含める**（数値根拠付き）
- **データ出所と対象期間を明記**（例: 「Meta Ads ad_id=XXX 2026-02-06〜09」）
- **計算根拠の開示**: 生データと計算式を添える（例: 「CPC (リンク) = ¥51,167 / 62回 = ¥825」）
- チャート化が有効な場合はオーケストレーターの render_chart を使用するよう示唆

## データ検証ルール（数値報告前に必ず確認）
1. date_start/date_stopが意図した期間と一致しているか確認
2. 広告の作成日より前のデータを報告しない
3. 比較先のtime_rangeが対象と同一であることを確認
4. リンクCTR = inline_link_clicks / impressions × 100 で検算
5. リンクCPC = spend / inline_link_clicks で検算
"""

    def build_agent(
        self,
        mcp_servers: List[Any] | None = None,
        asset: dict[str, Any] | None = None,
    ) -> Agent:
        """Build ADK agent with MCP toolset."""
        tools = self._get_domain_tools(mcp_servers, asset)

        return Agent(
            name=self.agent_name,
            model=self.model,
            description=self.tool_description,
            instruction=self._build_instructions(),
            tools=tools,
            planner=BuiltInPlanner(
                thinking_config=types.ThinkingConfig(
                    thinking_level=self.thinking_level,
                ),
            ),
            generate_content_config=types.GenerateContentConfig(
                max_output_tokens=self._settings.adk_max_output_tokens,
            ),
        )
