from typing import List, Optional
from sqlalchemy import and_, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from ....domain.entities.meeting_document import MeetingDocument
from ....domain.repositories.meeting_repository import MeetingRepository
from ....domain.value_objects.account_email import AccountEmail
from ....domain.value_objects.document_id import DocumentId
from ....domain.value_objects.meeting_metadata import MeetingMetadata
from ..models.meeting_document_model import MeetingDocumentModel


class MeetingRepositoryImpl(MeetingRepository):
    """議事録リポジトリの実装"""
    
    def __init__(self, session: AsyncSession):
        self._session = session
    
    async def save(self, meeting_document: MeetingDocument) -> MeetingDocument:
        """議事録ドキュメントを保存"""
        model = self._entity_to_model(meeting_document)
        
        self._session.add(model)
        await self._session.commit()
        await self._session.refresh(model)
        
        return self._model_to_entity(model)
    
    async def find_by_id(self, meeting_id: str) -> Optional[MeetingDocument]:
        """IDで議事録ドキュメントを検索"""
        query = select(MeetingDocumentModel).where(MeetingDocumentModel.id == meeting_id)
        result = await self._session.execute(query)
        model = result.scalar_one_or_none()
        
        return self._model_to_entity(model) if model else None
    
    async def find_by_document_id_and_account(
        self, 
        document_id: DocumentId, 
        account_email: AccountEmail
    ) -> Optional[MeetingDocument]:
        """ドキュメントIDとアカウントで議事録ドキュメントを検索"""
        query = select(MeetingDocumentModel).where(
            and_(
                MeetingDocumentModel.document_id == document_id.value,
                MeetingDocumentModel.account_email == account_email.value
            )
        )
        result = await self._session.execute(query)
        model = result.scalar_one_or_none()
        
        return self._model_to_entity(model) if model else None
    
    async def find_all(
        self,
        account_email: Optional[AccountEmail] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[MeetingDocument]:
        """議事録ドキュメント一覧を取得"""
        query = select(MeetingDocumentModel)
        
        if account_email:
            query = query.where(MeetingDocumentModel.account_email == account_email.value)
        
        query = query.order_by(desc(MeetingDocumentModel.created_at)).limit(limit).offset(offset)
        
        result = await self._session.execute(query)
        models = result.scalars().all()
        
        return [self._model_to_entity(model) for model in models]
    
    async def find_by_account(
        self,
        account_email: AccountEmail,
        limit: int = 100,
        offset: int = 0
    ) -> List[MeetingDocument]:
        """指定アカウントの議事録ドキュメント一覧を取得"""
        return await self.find_all(account_email=account_email, limit=limit, offset=offset)
    
    async def update(self, meeting_document: MeetingDocument) -> MeetingDocument:
        """議事録ドキュメントを更新"""
        # 既存のモデルを取得
        query = select(MeetingDocumentModel).where(MeetingDocumentModel.id == meeting_document.id)
        result = await self._session.execute(query)
        existing_model = result.scalar_one_or_none()
        
        if not existing_model:
            raise ValueError(f"Meeting document not found: {meeting_document.id}")
        
        # フィールドを更新
        existing_model.document_id = meeting_document.document_id.value
        existing_model.account_email = meeting_document.account_email.value
        existing_model.metadata = self._metadata_to_dict(meeting_document.metadata)
        existing_model.text_content = meeting_document.text_content
        existing_model.doc_structure = meeting_document.doc_structure
        existing_model.downloaded_at = meeting_document.downloaded_at
        existing_model.updated_at = meeting_document.updated_at
        
        await self._session.commit()
        await self._session.refresh(existing_model)
        
        return self._model_to_entity(existing_model)
    
    async def delete(self, meeting_id: str) -> bool:
        """議事録ドキュメントを削除"""
        query = select(MeetingDocumentModel).where(MeetingDocumentModel.id == meeting_id)
        result = await self._session.execute(query)
        model = result.scalar_one_or_none()
        
        if not model:
            return False
        
        await self._session.delete(model)
        await self._session.commit()
        return True
    
    async def exists(self, document_id: DocumentId, account_email: AccountEmail) -> bool:
        """指定されたドキュメントIDとアカウントの組み合わせが存在するかチェック"""
        query = select(func.count(MeetingDocumentModel.id)).where(
            and_(
                MeetingDocumentModel.document_id == document_id.value,
                MeetingDocumentModel.account_email == account_email.value
            )
        )
        result = await self._session.execute(query)
        count = result.scalar()
        return count > 0
    
    async def count_by_account(self, account_email: Optional[AccountEmail] = None) -> int:
        """議事録ドキュメント数をカウント"""
        query = select(func.count(MeetingDocumentModel.id))
        
        if account_email:
            query = query.where(MeetingDocumentModel.account_email == account_email.value)
        
        result = await self._session.execute(query)
        return result.scalar()
    
    async def find_recent(
        self,
        account_email: Optional[AccountEmail] = None,
        days: int = 30,
        limit: int = 50
    ) -> List[MeetingDocument]:
        """最近の議事録ドキュメントを取得"""
        from datetime import datetime, timedelta
        
        cutoff_date = datetime.now() - timedelta(days=days)
        
        query = select(MeetingDocumentModel).where(
            MeetingDocumentModel.created_at >= cutoff_date
        )
        
        if account_email:
            query = query.where(MeetingDocumentModel.account_email == account_email.value)
        
        query = query.order_by(desc(MeetingDocumentModel.created_at)).limit(limit)
        
        result = await self._session.execute(query)
        models = result.scalars().all()
        
        return [self._model_to_entity(model) for model in models]
    
    def _entity_to_model(self, entity: MeetingDocument) -> MeetingDocumentModel:
        """エンティティをORMモデルに変換"""
        return MeetingDocumentModel(
            id=entity.id,
            document_id=entity.document_id.value,
            account_email=entity.account_email.value,
            metadata=self._metadata_to_dict(entity.metadata),
            text_content=entity.text_content,
            doc_structure=entity.doc_structure,
            downloaded_at=entity.downloaded_at,
            created_at=entity.created_at,
            updated_at=entity.updated_at
        )
    
    def _model_to_entity(self, model: MeetingDocumentModel) -> MeetingDocument:
        """ORMモデルをエンティティに変換"""
        document_id = DocumentId(model.document_id)
        account_email = AccountEmail(model.account_email)
        metadata = self._dict_to_metadata(model.metadata)
        
        entity = MeetingDocument(
            id=model.id,
            document_id=document_id,
            account_email=account_email,
            metadata=metadata,
            text_content=model.text_content,
            doc_structure=model.doc_structure,
            downloaded_at=model.downloaded_at,
            created_at=model.created_at,
            updated_at=model.updated_at
        )
        
        return entity
    
    def _metadata_to_dict(self, metadata: MeetingMetadata) -> dict:
        """MeetingMetadata を辞書に変換"""
        return {
            "title": metadata.title,
            "date_time": metadata.date_time.isoformat() if metadata.date_time else None,
            "web_view_link": metadata.web_view_link,
            "created_time": metadata.created_time,
            "modified_time": metadata.modified_time,
            "owner_email": metadata.owner_email,
            "invited_accounts": metadata.invited_accounts
        }
    
    def _dict_to_metadata(self, data: dict) -> MeetingMetadata:
        """辞書を MeetingMetadata に変換"""
        from datetime import datetime
        
        date_time = None
        if data.get('date_time'):
            try:
                date_time = datetime.fromisoformat(data['date_time'])
            except (ValueError, TypeError):
                pass
        
        return MeetingMetadata(
            title=data.get("title", ""),
            date_time=date_time,
            web_view_link=data.get("web_view_link", ""),
            created_time=data.get("created_time", ""),
            modified_time=data.get("modified_time", ""),
            owner_email=data.get("owner_email", ""),
            invited_accounts=data.get("invited_accounts", [])
        )