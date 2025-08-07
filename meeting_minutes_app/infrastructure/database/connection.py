from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool
import logging

from ..config.settings import settings

# SQLAlchemy Base
Base = declarative_base()

# Logger
logger = logging.getLogger(__name__)


class DatabaseConnection:
    """データベース接続管理クラス"""
    
    def __init__(self):
        self._engine = None
        self._async_session_maker = None
        self._initialize_database()
    
    def _initialize_database(self):
        """データベース接続を初期化"""
        if not settings.database_url:
            raise ValueError("Database URL is required")
        
        # SQLAlchemy Engine の作成
        self._engine = create_async_engine(
            settings.database_url,
            echo=settings.debug,  # デバッグモードでSQL出力
            pool_size=settings.database_pool_size,
            max_overflow=settings.database_max_overflow,
            poolclass=NullPool if settings.is_development else None,  # 開発環境では接続プールを無効化
        )
        
        # AsyncSessionMaker の作成
        self._async_session_maker = async_sessionmaker(
            bind=self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        
        logger.info("Database connection initialized")
    
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        データベースセッションを取得（async context manager）
        
        Yields:
            AsyncSession: データベースセッション
        """
        if not self._async_session_maker:
            raise RuntimeError("Database not initialized")
        
        async with self._async_session_maker() as session:
            try:
                yield session
            except Exception as e:
                logger.error(f"Database session error: {e}")
                await session.rollback()
                raise
            finally:
                await session.close()
    
    async def create_tables(self):
        """データベーステーブルを作成"""
        if not self._engine:
            raise RuntimeError("Database engine not initialized")
        
        async with self._engine.begin() as conn:
            # 全テーブル作成
            await conn.run_sync(Base.metadata.create_all)
            logger.info("Database tables created")
    
    async def drop_tables(self):
        """データベーステーブルを削除（開発用）"""
        if not self._engine:
            raise RuntimeError("Database engine not initialized")
        
        if not settings.is_development:
            raise RuntimeError("Table dropping is only allowed in development environment")
        
        async with self._engine.begin() as conn:
            # 全テーブル削除
            await conn.run_sync(Base.metadata.drop_all)
            logger.info("Database tables dropped")
    
    async def close(self):
        """データベース接続を閉じる"""
        if self._engine:
            await self._engine.dispose()
            logger.info("Database connection closed")
    
    @property
    def engine(self):
        """SQLAlchemy Engine を取得"""
        return self._engine
    
    def is_connected(self) -> bool:
        """データベース接続状態を確認"""
        return self._engine is not None and not self._engine.closed


# グローバルデータベース接続インスタンス
database_connection = DatabaseConnection()


async def get_database_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI依存性注入用のデータベースセッション取得関数
    
    Yields:
        AsyncSession: データベースセッション
    """
    async for session in database_connection.get_session():
        yield session


async def init_database():
    """データベース初期化（アプリケーション起動時に実行）"""
    try:
        await database_connection.create_tables()
        logger.info("Database initialization completed")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise


async def close_database():
    """データベース接続を閉じる（アプリケーション終了時に実行）"""
    try:
        await database_connection.close()
        logger.info("Database connection closed")
    except Exception as e:
        logger.error(f"Error closing database connection: {e}")