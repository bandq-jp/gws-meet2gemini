from typing import Dict, Any, Protocol
from ..entities.meeting_document import MeetingDocument
from ..entities.structured_data import StructuredData


class StructuredExtractionProvider(Protocol):
    """構造化抽出プロバイダーのインターフェース"""
    
    async def extract_structured_data(self, text_content: str) -> Dict[str, Any]:
        """テキストから構造化データを抽出"""
        pass


class StructuredExtractionService:
    """構造化データ抽出を行うドメインサービス"""
    
    def __init__(self, extraction_provider: StructuredExtractionProvider):
        self._extraction_provider = extraction_provider
    
    async def extract_from_meeting_document(
        self,
        meeting_document: MeetingDocument
    ) -> StructuredData:
        """
        議事録ドキュメントから構造化データを抽出
        
        Args:
            meeting_document: 議事録ドキュメント
            
        Returns:
            抽出された構造化データ
        """
        if not meeting_document.text_content:
            raise ValueError("Meeting document has no text content for extraction")
        
        try:
            # 構造化データの抽出
            extracted_data = await self._extraction_provider.extract_structured_data(
                meeting_document.text_content
            )
            
            # 構造化データエンティティを作成
            structured_data = StructuredData.from_extracted_data(
                meeting_document.id,
                extracted_data
            )
            
            return structured_data
            
        except Exception as e:
            # 抽出失敗時は失敗状態の構造化データを作成
            structured_data = StructuredData.create(meeting_document.id)
            structured_data.mark_extraction_failed(str(e))
            return structured_data
    
    async def re_extract(
        self,
        meeting_document: MeetingDocument,
        existing_structured_data: StructuredData
    ) -> StructuredData:
        """
        既存の構造化データを再抽出
        
        Args:
            meeting_document: 議事録ドキュメント
            existing_structured_data: 既存の構造化データ
            
        Returns:
            更新された構造化データ
        """
        try:
            # 新しい抽出を実行
            extracted_data = await self._extraction_provider.extract_structured_data(
                meeting_document.text_content
            )
            
            # 既存のデータを更新
            existing_structured_data.update_from_extracted_data(extracted_data)
            
            return existing_structured_data
            
        except Exception as e:
            # 抽出失敗をマーク
            existing_structured_data.mark_extraction_failed(str(e))
            return existing_structured_data
    
    def validate_extraction_result(self, extracted_data: Dict[str, Any]) -> bool:
        """
        抽出結果の妥当性を検証
        
        Args:
            extracted_data: 抽出されたデータ
            
        Returns:
            妥当性チェック結果
        """
        if not isinstance(extracted_data, dict):
            return False
        
        # 最低限のフィールドの存在チェック
        # 実際のビジネスルールに応じてカスタマイズ
        return True
    
    def calculate_extraction_quality_score(self, structured_data: StructuredData) -> float:
        """
        抽出品質スコアを計算
        
        Args:
            structured_data: 構造化データ
            
        Returns:
            品質スコア（0.0-1.0）
        """
        if not structured_data.is_extraction_completed():
            return 0.0
        
        # 抽出されたフィールド数に基づく簡易的な品質スコア
        total_fields = 36  # 全フィールド数
        extracted_fields = 0
        
        # 各フィールドの存在チェック
        fields_to_check = [
            structured_data.transfer_activity_status,
            structured_data.agent_count,
            structured_data.current_agents,
            structured_data.desired_timing,
            structured_data.current_duties,
            structured_data.experience_industry,
            structured_data.current_salary,
            # 他のフィールドも必要に応じて追加
        ]
        
        extracted_fields = sum(1 for field in fields_to_check if field is not None)
        
        # リストフィールドの存在チェック
        list_fields = [
            structured_data.transfer_reasons,
            structured_data.career_history,
            structured_data.desired_industry,
            structured_data.business_vision,
            # 他のリストフィールドも追加
        ]
        
        extracted_fields += sum(1 for field in list_fields if field and len(field) > 0)
        
        return min(extracted_fields / total_fields, 1.0)