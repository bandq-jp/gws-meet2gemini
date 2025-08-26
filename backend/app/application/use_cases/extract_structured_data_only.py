from __future__ import annotations
import logging
from typing import Optional, Dict, Any
from uuid import UUID
from dataclasses import asdict

from app.infrastructure.supabase.repositories.meeting_repository_impl import MeetingRepositoryImpl
from app.infrastructure.supabase.repositories.structured_repository_impl import StructuredRepositoryImpl
from app.infrastructure.supabase.repositories.custom_schema_repository_impl import CustomSchemaRepositoryImpl
from app.infrastructure.supabase.repositories.ai_usage_repository_impl import AiUsageRepositoryImpl
from app.infrastructure.gemini.structured_extractor import StructuredDataExtractor
from app.domain.entities.structured_data import StructuredData
from app.presentation.api.v1.settings import get_current_gemini_settings

# ログ設定
logger = logging.getLogger(__name__)


class ExtractStructuredDataOnlyUseCase:
    """構造化出力のみを実行するユースケース（Zoho書き込みは行わない）"""
    
    def execute(self, meeting_id: str, custom_schema_id: Optional[UUID] = None) -> dict:
        meetings = MeetingRepositoryImpl()
        structured_repo = StructuredRepositoryImpl()
        meeting = meetings.get_meeting(meeting_id)
        
        if not meeting or not meeting.get("text_content"):
            raise ValueError("Meeting text not found")
        
        # カスタムスキーマを取得（指定されている場合）
        custom_schema = None
        schema_version = "default"
        if custom_schema_id:
            custom_schema_repo = CustomSchemaRepositoryImpl()
            custom_schema = custom_schema_repo.get_by_id(custom_schema_id)
            if not custom_schema:
                raise ValueError("指定されたカスタムスキーマが見つかりません")
            if not custom_schema.is_active:
                raise ValueError("指定されたカスタムスキーマは非アクティブです")
            schema_version = f"custom-{custom_schema.id}"
        else:
            # デフォルトスキーマを使用
            custom_schema_repo = CustomSchemaRepositoryImpl()
            custom_schema = custom_schema_repo.get_default_schema()
            if custom_schema:
                schema_version = f"default-{custom_schema.id}"
        
        # 現在の設定を取得
        gemini_settings = get_current_gemini_settings()
        
        extractor = StructuredDataExtractor(
            model=gemini_settings.gemini_model,
            temperature=gemini_settings.gemini_temperature,
            max_tokens=gemini_settings.gemini_max_tokens
        )
        
        # Extract agent name for context
        agent_name = meeting.get("organizer_name")
        
        # カスタムスキーマが指定されている場合はそれを使用、そうでなければデフォルト処理
        if custom_schema:
            data = self._extract_with_custom_schema(
                extractor, meeting["text_content"], custom_schema, 
                None, agent_name  # candidate_nameはNoneで処理
            )
        else:
            data = extractor.extract_all_structured_data(
                meeting["text_content"], 
                candidate_name=None,  # 候補者名は指定しない
                agent_name=agent_name,
                use_parallel=True
            )
        
        # Zoho候補者情報なしで構造化データを作成
        structured_data = StructuredData(
            meeting_id=meeting_id,
            data=data,
            zoho_candidate=None  # Zoho候補者情報はなし
        )
        
        # Supabaseに構造化データを保存
        structured_repo.upsert_structured(structured_data)
        logger.info(f"構造化出力をSupabaseに保存完了: meeting_id={meeting_id}")
        
        # 使用量ログの保存（失敗しても処理は継続）
        try:
            usage_repo = AiUsageRepositoryImpl()
            usage_repo.insert_many(
                meeting_id=meeting_id,
                events=[asdict(event) for event in extractor.usage_events]
            )
            logger.info(f"AI使用量ログを保存完了: meeting_id={meeting_id}, events_count={len(extractor.usage_events)}")
        except Exception as e:
            logger.warning(f"AI使用量ログ保存に失敗: meeting_id={meeting_id}, error={str(e)}")
        
        return {
            "meeting_id": meeting_id, 
            "data": data, 
            "zoho_candidate": None,
            "custom_schema_id": custom_schema_id,
            "schema_version": schema_version
        }
    
    def _extract_with_custom_schema(
        self, 
        extractor: StructuredDataExtractor, 
        text_content: str, 
        custom_schema, 
        candidate_name: Optional[str], 
        agent_name: Optional[str]
    ) -> dict:
        """カスタムスキーマを使用した構造化データ抽出"""
        combined_result = {}
        
        # カスタムスキーマのグループを取得
        schema_groups = custom_schema.to_json_schema_groups()
        
        # 各グループを順次処理（並列処理は既存のextract_all_structured_dataに任せる）
        for schema_dict, group_name in schema_groups:
            try:
                result = extractor.extract_structured_data_group(
                    text_content,
                    schema_dict,
                    group_name,
                    candidate_name,
                    agent_name
                )
                combined_result.update(result)
            except Exception as e:
                # 個別グループの失敗は握りつぶし、全体の処理を継続
                logger.warning(f"Group extraction failed for {group_name}: {e}")
                continue
        
        return combined_result