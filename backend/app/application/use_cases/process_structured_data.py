from __future__ import annotations
from typing import Optional
from uuid import UUID

from app.infrastructure.supabase.repositories.meeting_repository_impl import MeetingRepositoryImpl
from app.infrastructure.supabase.repositories.structured_repository_impl import StructuredRepositoryImpl
from app.infrastructure.supabase.repositories.custom_schema_repository_impl import CustomSchemaRepositoryImpl
from app.infrastructure.gemini.structured_extractor import StructuredDataExtractor
from app.domain.entities.structured_data import StructuredData, ZohoCandidateInfo
from app.presentation.api.v1.settings import get_current_gemini_settings

# from app.infrastructure.zoho.cliant import ZohoWriteClient


class ProcessStructuredDataUseCase:
    def execute(self, meeting_id: str, zoho_candidate_id: Optional[str] = None, 
                     zoho_record_id: Optional[str] = None, 
                     zoho_candidate_name: Optional[str] = None, 
                     zoho_candidate_email: Optional[str] = None,
                     custom_schema_id: Optional[UUID] = None) -> dict:
        meetings = MeetingRepositoryImpl()
        structured_repo = StructuredRepositoryImpl()
        meeting = meetings.get_meeting(meeting_id)
        if not meeting or not meeting.get("text_content"):
            raise ValueError("Meeting text not found")
        
        # Require Zoho candidate selection
        if not zoho_record_id:
            raise ValueError("Zoho candidate selection is required for structured output processing")
        
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
        # Extract candidate and agent names for better context
        candidate_name = zoho_candidate_name
        agent_name = meeting.get("organizer_name")
        
        # カスタムスキーマが指定されている場合はそれを使用、そうでなければデフォルト処理
        if custom_schema:
            data = self._extract_with_custom_schema(
                extractor, meeting["text_content"], custom_schema, 
                candidate_name, agent_name
            )
        else:
            data = extractor.extract_all_structured_data(
                meeting["text_content"], 
                candidate_name=candidate_name, 
                agent_name=agent_name,
                use_parallel=True
            )
        
        # Create structured data with Zoho candidate info
        zoho_candidate = ZohoCandidateInfo(
            candidate_id=zoho_candidate_id,
            record_id=zoho_record_id,
            candidate_name=zoho_candidate_name,
            candidate_email=zoho_candidate_email
        )
        
        structured_data = StructuredData(
            meeting_id=meeting_id,
            data=data,
            zoho_candidate=zoho_candidate
        )
        
        structured_repo.upsert_structured(structured_data)

        
        return {
            "meeting_id": meeting_id, 
            "data": data, 
            "zoho_candidate": zoho_candidate,
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
                print(f"Group extraction failed for {group_name}: {e}")
                continue
        
        return combined_result
