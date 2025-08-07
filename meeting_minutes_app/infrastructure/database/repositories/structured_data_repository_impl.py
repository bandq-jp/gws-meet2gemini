from typing import List, Optional
from sqlalchemy import desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from ....domain.entities.structured_data import StructuredData
from ....domain.repositories.structured_data_repository import StructuredDataRepository
from ..models.structured_data_model import StructuredDataModel


class StructuredDataRepositoryImpl(StructuredDataRepository):
    """構造化データリポジトリの実装"""
    
    def __init__(self, session: AsyncSession):
        self._session = session
    
    async def save(self, structured_data: StructuredData) -> StructuredData:
        """構造化データを保存"""
        model = self._entity_to_model(structured_data)
        
        self._session.add(model)
        await self._session.commit()
        await self._session.refresh(model)
        
        return self._model_to_entity(model)
    
    async def find_by_id(self, structured_data_id: str) -> Optional[StructuredData]:
        """IDで構造化データを検索"""
        query = select(StructuredDataModel).where(StructuredDataModel.id == structured_data_id)
        result = await self._session.execute(query)
        model = result.scalar_one_or_none()
        
        return self._model_to_entity(model) if model else None
    
    async def find_by_meeting_document_id(self, meeting_document_id: str) -> Optional[StructuredData]:
        """議事録ドキュメントIDで構造化データを検索"""
        query = select(StructuredDataModel).where(
            StructuredDataModel.meeting_document_id == meeting_document_id
        )
        result = await self._session.execute(query)
        model = result.scalar_one_or_none()
        
        return self._model_to_entity(model) if model else None
    
    async def find_all(
        self,
        extraction_status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[StructuredData]:
        """構造化データ一覧を取得"""
        query = select(StructuredDataModel)
        
        if extraction_status:
            query = query.where(StructuredDataModel.extraction_status == extraction_status)
        
        query = query.order_by(desc(StructuredDataModel.created_at)).limit(limit).offset(offset)
        
        result = await self._session.execute(query)
        models = result.scalars().all()
        
        return [self._model_to_entity(model) for model in models]
    
    async def update(self, structured_data: StructuredData) -> StructuredData:
        """構造化データを更新"""
        # 既存のモデルを取得
        query = select(StructuredDataModel).where(StructuredDataModel.id == structured_data.id)
        result = await self._session.execute(query)
        existing_model = result.scalar_one_or_none()
        
        if not existing_model:
            raise ValueError(f"Structured data not found: {structured_data.id}")
        
        # フィールドを更新
        self._update_model_from_entity(existing_model, structured_data)
        
        await self._session.commit()
        await self._session.refresh(existing_model)
        
        return self._model_to_entity(existing_model)
    
    async def delete(self, structured_data_id: str) -> bool:
        """構造化データを削除"""
        query = select(StructuredDataModel).where(StructuredDataModel.id == structured_data_id)
        result = await self._session.execute(query)
        model = result.scalar_one_or_none()
        
        if not model:
            return False
        
        await self._session.delete(model)
        await self._session.commit()
        return True
    
    async def exists_for_meeting_document(self, meeting_document_id: str) -> bool:
        """指定された議事録ドキュメントの構造化データが存在するかチェック"""
        query = select(func.count(StructuredDataModel.id)).where(
            StructuredDataModel.meeting_document_id == meeting_document_id
        )
        result = await self._session.execute(query)
        count = result.scalar()
        return count > 0
    
    async def find_pending_extractions(self, limit: int = 50) -> List[StructuredData]:
        """抽出待ちの構造化データを取得"""
        query = select(StructuredDataModel).where(
            StructuredDataModel.extraction_status == "pending"
        ).order_by(StructuredDataModel.created_at).limit(limit)
        
        result = await self._session.execute(query)
        models = result.scalars().all()
        
        return [self._model_to_entity(model) for model in models]
    
    async def find_failed_extractions(self, limit: int = 50) -> List[StructuredData]:
        """抽出失敗の構造化データを取得"""
        query = select(StructuredDataModel).where(
            StructuredDataModel.extraction_status == "failed"
        ).order_by(desc(StructuredDataModel.updated_at)).limit(limit)
        
        result = await self._session.execute(query)
        models = result.scalars().all()
        
        return [self._model_to_entity(model) for model in models]
    
    async def count_by_status(self, extraction_status: str) -> int:
        """ステータス別の構造化データ数をカウント"""
        query = select(func.count(StructuredDataModel.id)).where(
            StructuredDataModel.extraction_status == extraction_status
        )
        result = await self._session.execute(query)
        return result.scalar()
    
    async def find_completed_extractions(
        self,
        limit: int = 100,
        offset: int = 0
    ) -> List[StructuredData]:
        """抽出完了済みの構造化データを取得"""
        query = select(StructuredDataModel).where(
            StructuredDataModel.extraction_status == "completed"
        ).order_by(desc(StructuredDataModel.updated_at)).limit(limit).offset(offset)
        
        result = await self._session.execute(query)
        models = result.scalars().all()
        
        return [self._model_to_entity(model) for model in models]
    
    def _entity_to_model(self, entity: StructuredData) -> StructuredDataModel:
        """エンティティをORMモデルに変換"""
        model = StructuredDataModel()
        self._update_model_from_entity(model, entity)
        return model
    
    def _update_model_from_entity(self, model: StructuredDataModel, entity: StructuredData):
        """エンティティの内容でモデルを更新"""
        model.id = entity.id
        model.meeting_document_id = entity.meeting_document_id
        
        # 転職活動状況・エージェント関連
        model.transfer_activity_status = entity.transfer_activity_status
        model.agent_count = entity.agent_count
        model.current_agents = entity.current_agents
        model.introduced_jobs = entity.introduced_jobs
        model.job_appeal_points = entity.job_appeal_points
        model.job_concerns = entity.job_concerns
        model.companies_in_selection = entity.companies_in_selection
        model.other_offer_salary = entity.other_offer_salary
        model.other_company_intention = entity.other_company_intention
        
        # 転職理由・希望条件
        model.transfer_reasons = entity.transfer_reasons
        model.transfer_trigger = entity.transfer_trigger
        model.desired_timing = entity.desired_timing
        model.timing_details = entity.timing_details
        model.current_job_status = entity.current_job_status
        model.transfer_status_memo = entity.transfer_status_memo
        model.transfer_priorities = entity.transfer_priorities
        
        # 職歴・経験
        model.career_history = entity.career_history
        model.current_duties = entity.current_duties
        model.company_good_points = entity.company_good_points
        model.company_bad_points = entity.company_bad_points
        model.enjoyed_work = entity.enjoyed_work
        model.difficult_work = entity.difficult_work
        
        # 希望業界・職種
        model.experience_industry = entity.experience_industry
        model.experience_field_hr = entity.experience_field_hr
        model.desired_industry = entity.desired_industry
        model.industry_reason = entity.industry_reason
        model.desired_position = entity.desired_position
        model.position_industry_reason = entity.position_industry_reason
        
        # 年収・待遇条件
        model.current_salary = entity.current_salary
        model.salary_breakdown = entity.salary_breakdown
        model.desired_first_year_salary = entity.desired_first_year_salary
        model.base_incentive_ratio = entity.base_incentive_ratio
        model.max_future_salary = entity.max_future_salary
        model.salary_memo = entity.salary_memo
        model.remote_time_memo = entity.remote_time_memo
        model.ca_ra_focus = entity.ca_ra_focus
        model.customer_acquisition = entity.customer_acquisition
        model.new_existing_ratio = entity.new_existing_ratio
        
        # 企業文化・キャリアビジョン
        model.business_vision = entity.business_vision
        model.desired_employee_count = entity.desired_employee_count
        model.culture_scale_memo = entity.culture_scale_memo
        model.career_vision = entity.career_vision
        
        # メタデータ
        model.extraction_metadata = entity.extraction_metadata
        model.extraction_status = entity.extraction_status
        model.created_at = entity.created_at
        model.updated_at = entity.updated_at
    
    def _model_to_entity(self, model: StructuredDataModel) -> StructuredData:
        """ORMモデルをエンティティに変換"""
        return StructuredData(
            id=model.id,
            meeting_document_id=model.meeting_document_id,
            
            # 転職活動状況・エージェント関連
            transfer_activity_status=model.transfer_activity_status,
            agent_count=model.agent_count,
            current_agents=model.current_agents,
            introduced_jobs=model.introduced_jobs,
            job_appeal_points=model.job_appeal_points,
            job_concerns=model.job_concerns,
            companies_in_selection=model.companies_in_selection or [],
            other_offer_salary=model.other_offer_salary,
            other_company_intention=model.other_company_intention or [],
            
            # 転職理由・希望条件
            transfer_reasons=model.transfer_reasons or [],
            transfer_trigger=model.transfer_trigger or [],
            desired_timing=model.desired_timing,
            timing_details=model.timing_details,
            current_job_status=model.current_job_status,
            transfer_status_memo=model.transfer_status_memo or [],
            transfer_priorities=model.transfer_priorities or [],
            
            # 職歴・経験
            career_history=model.career_history or [],
            current_duties=model.current_duties,
            company_good_points=model.company_good_points,
            company_bad_points=model.company_bad_points,
            enjoyed_work=model.enjoyed_work,
            difficult_work=model.difficult_work,
            
            # 希望業界・職種
            experience_industry=model.experience_industry,
            experience_field_hr=model.experience_field_hr,
            desired_industry=model.desired_industry or [],
            industry_reason=model.industry_reason or [],
            desired_position=model.desired_position or [],
            position_industry_reason=model.position_industry_reason or [],
            
            # 年収・待遇条件
            current_salary=model.current_salary,
            salary_breakdown=model.salary_breakdown,
            desired_first_year_salary=model.desired_first_year_salary,
            base_incentive_ratio=model.base_incentive_ratio,
            max_future_salary=model.max_future_salary,
            salary_memo=model.salary_memo or [],
            remote_time_memo=model.remote_time_memo or [],
            ca_ra_focus=model.ca_ra_focus,
            customer_acquisition=model.customer_acquisition,
            new_existing_ratio=model.new_existing_ratio,
            
            # 企業文化・キャリアビジョン
            business_vision=model.business_vision or [],
            desired_employee_count=model.desired_employee_count or [],
            culture_scale_memo=model.culture_scale_memo or [],
            career_vision=model.career_vision or [],
            
            # メタデータ
            extraction_metadata=model.extraction_metadata,
            extraction_status=model.extraction_status,
            created_at=model.created_at,
            updated_at=model.updated_at
        )