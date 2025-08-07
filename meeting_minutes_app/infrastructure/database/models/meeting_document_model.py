from sqlalchemy import Column, String, Text, DateTime, JSON, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid

from ..connection import Base


class MeetingDocumentModel(Base):
    """議事録ドキュメントのORMモデル"""
    
    __tablename__ = "meeting_documents"
    
    # 基本フィールド
    id = Column(
        String, 
        primary_key=True, 
        default=lambda: str(uuid.uuid4()),
        comment="議事録ドキュメントの一意ID"
    )
    
    document_id = Column(
        String(100), 
        nullable=False, 
        comment="GoogleドキュメントID"
    )
    
    account_email = Column(
        String(255), 
        nullable=False, 
        comment="アカウントメールアドレス"
    )
    
    # メタデータ（JSON形式で保存）
    metadata = Column(
        JSON, 
        nullable=False, 
        default={},
        comment="会議メタデータ（タイトル、日時、参加者等）"
    )
    
    # テキストコンテンツ
    text_content = Column(
        Text, 
        nullable=False, 
        default="",
        comment="議事録のテキスト内容"
    )
    
    # ドキュメント構造（Docs API構造）
    doc_structure = Column(
        JSON,
        nullable=True,
        comment="Google Docs APIから取得した文書構造"
    )
    
    # タイムスタンプ
    downloaded_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now(),
        comment="ドキュメント取得日時"
    )
    
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now(),
        comment="レコード作成日時"
    )
    
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now(),
        onupdate=func.now(),
        comment="レコード更新日時"
    )
    
    # インデックス
    __table_args__ = (
        # 重複チェック用の複合インデックス
        Index(
            'idx_meeting_doc_duplicate', 
            'document_id', 
            'account_email',
            unique=True
        ),
        # アカウント検索用インデックス
        Index('idx_meeting_account_email', 'account_email'),
        # 作成日時検索用インデックス
        Index('idx_meeting_created_at', 'created_at'),
        # 更新日時検索用インデックス
        Index('idx_meeting_updated_at', 'updated_at'),
        # メタデータ内の日時検索用インデックス（PostgreSQL専用）
        # Index('idx_meeting_date_time', text("((metadata->>'date_time'))")),
    )
    
    def __repr__(self):
        return (
            f"<MeetingDocumentModel("
            f"id={self.id}, "
            f"document_id={self.document_id}, "
            f"account_email={self.account_email}, "
            f"created_at={self.created_at}"
            f")>"
        )
    
    def to_dict(self) -> dict:
        """辞書形式に変換"""
        return {
            "id": self.id,
            "document_id": self.document_id,
            "account_email": self.account_email,
            "metadata": self.metadata,
            "text_content": self.text_content,
            "doc_structure": self.doc_structure,
            "downloaded_at": self.downloaded_at.isoformat() if self.downloaded_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }