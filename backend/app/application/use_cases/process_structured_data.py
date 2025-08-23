from __future__ import annotations
import logging
from typing import Optional, Dict, Any
from uuid import UUID

from app.infrastructure.supabase.repositories.meeting_repository_impl import MeetingRepositoryImpl
from app.infrastructure.supabase.repositories.structured_repository_impl import StructuredRepositoryImpl
from app.infrastructure.supabase.repositories.custom_schema_repository_impl import CustomSchemaRepositoryImpl
from app.infrastructure.gemini.structured_extractor import StructuredDataExtractor
from app.domain.entities.structured_data import StructuredData, ZohoCandidateInfo
from app.presentation.api.v1.settings import get_current_gemini_settings
from app.infrastructure.zoho.client import ZohoWriteClient, ZohoAuthError

# ログ設定
logger = logging.getLogger(__name__)


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
        
        # Supabaseに構造化データを保存
        structured_repo.upsert_structured(structured_data)
        logger.info(f"構造化データをSupabaseに保存完了: meeting_id={meeting_id}, candidate={zoho_candidate_name}")
        
        # Zoho CRMに構造化データを書き込み（失敗しても処理は継続）
        zoho_result = self._write_to_zoho(
            zoho_record_id=zoho_record_id,
            structured_data=data,
            candidate_name=zoho_candidate_name
        )
        
        return {
            "meeting_id": meeting_id, 
            "data": data, 
            "zoho_candidate": zoho_candidate,
            "custom_schema_id": custom_schema_id,
            "schema_version": schema_version,
            "zoho_write_result": zoho_result  # Zoho書き込み結果を含める
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
    
    def _write_to_zoho(
        self,
        zoho_record_id: str,
        structured_data: Dict[str, Any], 
        candidate_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """構造化データをZoho CRMに書き込み
        
        Args:
            zoho_record_id: Zohoレコード ID
            structured_data: 構造化出力データ
            candidate_name: 候補者名（ログ用）
            
        Returns:
            書き込み結果辞書
        """
        try:
            logger.info(f"Zoho書き込み開始: record_id={zoho_record_id}, candidate={candidate_name}")
            
            # ZohoWriteClientでレコード更新
            zoho_client = ZohoWriteClient()
            result = zoho_client.update_jobseeker_record(
                record_id=zoho_record_id,
                structured_data=structured_data
            )
            
            if result["status"] == "success":
                updated_count = len(result.get("updated_fields", []))
                logger.info(
                    f"Zoho書き込み成功: record_id={zoho_record_id}, "
                    f"candidate={candidate_name}, updated_fields={updated_count}"
                )
                return {
                    "status": "success",
                    "message": f"Zohoレコードを正常に更新しました（{updated_count}フィールド）",
                    "updated_fields_count": updated_count,
                    "updated_fields": result.get("updated_fields", []),
                    "zoho_response": result.get("data")
                }
            else:
                # Zoho書き込み失敗（構造化出力処理は成功として継続）
                error_msg = result.get("error", "Unknown error")
                logger.warning(
                    f"Zoho書き込み失敗: record_id={zoho_record_id}, "
                    f"candidate={candidate_name}, error={error_msg}"
                )
                return {
                    "status": "failed",
                    "message": f"Zoho書き込みに失敗しました: {error_msg}",
                    "error": error_msg,
                    "attempted_data_count": len(result.get("attempted_data", {}))
                }
                
        except ZohoAuthError as e:
            logger.error(
                f"Zoho認証エラー: record_id={zoho_record_id}, "
                f"candidate={candidate_name}, error={str(e)}"
            )
            return {
                "status": "auth_error",
                "message": "Zoho認証に失敗しました。管理者に連絡してください。",
                "error": str(e)
            }
            
        except Exception as e:
            logger.error(
                f"Zoho書き込み予期しないエラー: record_id={zoho_record_id}, "
                f"candidate={candidate_name}, error={str(e)}"
            )
            return {
                "status": "error",
                "message": f"Zoho書き込みで予期しないエラーが発生しました: {str(e)}",
                "error": str(e)
            }
