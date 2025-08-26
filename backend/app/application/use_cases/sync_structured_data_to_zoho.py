from __future__ import annotations
import logging
from typing import Optional, Dict, Any

from app.infrastructure.supabase.repositories.structured_repository_impl import StructuredRepositoryImpl
from app.infrastructure.zoho.client import ZohoWriteClient, ZohoAuthError, ZohoFieldMappingError
from app.domain.entities.structured_data import ZohoCandidateInfo

# ログ設定
logger = logging.getLogger(__name__)


class SyncStructuredDataToZohoUseCase:
    """既存の構造化データをZoho CRMに手動で同期するユースケース"""
    
    def execute(
        self, 
        meeting_id: str,
        zoho_candidate_id: Optional[str] = None, 
        zoho_record_id: str = None,
        zoho_candidate_name: Optional[str] = None, 
        zoho_candidate_email: Optional[str] = None
    ) -> dict:
        """
        既存の構造化データをZoho CRMに同期
        
        Args:
            meeting_id: 会議ID
            zoho_candidate_id: Zoho候補者ID
            zoho_record_id: Zohoレコード ID (必須)
            zoho_candidate_name: 候補者名
            zoho_candidate_email: 候補者メールアドレス
            
        Returns:
            同期結果辞書
        """
        if not zoho_record_id:
            raise ValueError("Zoho candidate selection is required for sync to Zoho")
        
        # 既存の構造化データを取得
        structured_repo = StructuredRepositoryImpl()
        existing_data = structured_repo.get_structured_data(meeting_id)
        
        if not existing_data:
            raise ValueError(f"No structured data found for meeting_id: {meeting_id}")
        
        logger.info(f"構造化データを取得: meeting_id={meeting_id}")
        
        # Zoho候補者情報でデータを更新（もしくは新規作成）
        zoho_candidate = ZohoCandidateInfo(
            candidate_id=zoho_candidate_id,
            record_id=zoho_record_id,
            candidate_name=zoho_candidate_name,
            candidate_email=zoho_candidate_email
        )
        
        # 構造化データのZoho候補者情報を更新
        existing_data.zoho_candidate = zoho_candidate
        structured_repo.upsert_structured(existing_data)
        logger.info(f"Zoho候補者情報を更新: meeting_id={meeting_id}, candidate={zoho_candidate_name}")
        
        # Zoho CRMに構造化データを書き込み
        zoho_result = self._write_to_zoho(
            zoho_record_id=zoho_record_id,
            structured_data=existing_data.data,
            candidate_name=zoho_candidate_name
        )
        
        # 実際に送信されたフィールドの情報を取得
        synced_fields = []
        if zoho_result.get("status") == "success":
            synced_fields = zoho_result.get("updated_fields", [])
        
        return {
            "meeting_id": meeting_id,
            "zoho_candidate": zoho_candidate,
            "zoho_sync_result": zoho_result,
            "synced_data_fields": synced_fields
        }
    
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
            structured_fields = list(structured_data.keys()) if structured_data else []
            logger.info(f"🔧 [手動同期] Zoho書き込み開始: 求職者「{candidate_name or '不明'}」(record_id={zoho_record_id}), 構造化フィールド数={len(structured_fields)}")
            logger.debug(f"📝 構造化フィールド一覧: {structured_fields}")
            
            # ZohoWriteClientでレコード更新
            zoho_client = ZohoWriteClient()
            result = zoho_client.update_jobseeker_record(
                record_id=zoho_record_id,
                structured_data=structured_data,
                candidate_name=candidate_name
            )
            
            if result["status"] == "success":
                updated_count = len(result.get("updated_fields", []))
                logger.info(f"✅ [手動同期] Zoho書き込み成功: 求職者「{candidate_name or '不明'}」(record_id={zoho_record_id}), 更新フィールド数={updated_count}")
                return {
                    "status": "success",
                    "message": f"Zohoレコードを正常に更新しました（{updated_count}フィールド）",
                    "updated_fields_count": updated_count,
                    "updated_fields": result.get("updated_fields", []),
                    "zoho_response": result.get("data")
                }
            else:
                # Zoho書き込み失敗
                error_msg = result.get("error", "Unknown error")
                logger.warning(f"⚠️ [手動同期] Zoho書き込み失敗: 求職者「{candidate_name or '不明'}」(record_id={zoho_record_id}), error={error_msg}")
                return {
                    "status": "failed",
                    "message": f"Zoho書き込みに失敗しました: {error_msg}",
                    "error": error_msg,
                    "attempted_data_count": len(result.get("attempted_data", {}))
                }
                
        except ZohoFieldMappingError as e:
            logger.error(f"🚫 [手動同期] Zohoフィールドマッピングエラー: 求職者「{candidate_name or '不明'}」(record_id={zoho_record_id}), error={str(e)}")
            return {
                "status": "field_mapping_error",
                "message": f"Zohoフィールド構造に問題があります: {str(e)}",
                "error": str(e),
                "suggestion": "Zoho CRMのフィールド設定を確認するか、管理者に連絡してください。"
            }
            
        except ZohoAuthError as e:
            logger.error(f"🔐 [手動同期] Zoho認証エラー: 求職者「{candidate_name or '不明'}」(record_id={zoho_record_id}), error={str(e)}")
            return {
                "status": "auth_error",
                "message": "Zoho認証に失敗しました。管理者に連絡してください。",
                "error": str(e)
            }
            
        except Exception as e:
            logger.error(f"💥 [手動同期] Zoho書き込み予期しないエラー: 求職者「{candidate_name or '不明'}」(record_id={zoho_record_id}), error={str(e)}")
            return {
                "status": "error",
                "message": f"Zoho書き込みで予期しないエラーが発生しました: {str(e)}",
                "error": str(e)
            }