from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
import uvicorn
from datetime import datetime

from infrastructure.config.settings import settings
from infrastructure.database.connection import init_database, close_database
from presentation.api.v1 import meetings, structured_data
from presentation.schemas.common_schemas import HealthCheckResponse, ConfigurationResponse

# ログ設定
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format=settings.log_format
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """アプリケーションライフサイクル管理"""
    # 起動時処理
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    
    try:
        # データベース初期化
        await init_database()
        logger.info("Database initialized successfully")
        
        # その他の初期化処理
        # TODO: 依存性注入の初期化
        
        logger.info(f"{settings.app_name} started successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize application: {e}")
        raise
    
    yield
    
    # 終了時処理
    logger.info(f"Shutting down {settings.app_name}")
    
    try:
        # データベース接続を閉じる
        await close_database()
        logger.info("Database connection closed")
        
        # その他のクリーンアップ処理
        
        logger.info(f"{settings.app_name} shutdown completed")
        
    except Exception as e:
        logger.error(f"Error during application shutdown: {e}")


# FastAPIアプリケーション作成
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="議事録管理システム - Google Meet議事録の収集・構造化分析",
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None
)

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_credentials,
    allow_methods=settings.cors_methods,
    allow_headers=settings.cors_headers,
)


# グローバル例外ハンドラー
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """グローバル例外ハンドラー"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "message": "Internal server error",
            "errors": [str(exc)] if settings.debug else ["An unexpected error occurred"]
        }
    )


# ヘルスチェックエンドポイント
@app.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """ヘルスチェック"""
    logger.info("Health check requested")
    
    try:
        # データベース接続チェック
        database_status = True  # TODO: 実際のDB接続チェック
        
        # Google認証チェック
        google_auth_status = True  # TODO: 実際の認証チェック
        
        # 全体のステータス判定
        overall_status = "healthy" if database_status and google_auth_status else "unhealthy"
        
        return HealthCheckResponse(
            status=overall_status,
            timestamp=datetime.now(),
            version=settings.app_version,
            database=database_status,
            google_auth=google_auth_status,
            details={
                "environment": settings.environment,
                "debug": settings.debug
            }
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthCheckResponse(
            status="unhealthy",
            timestamp=datetime.now(),
            version=settings.app_version,
            database=False,
            google_auth=False,
            details={
                "error": str(e)
            }
        )


# 設定情報エンドポイント
@app.get("/config", response_model=ConfigurationResponse)
async def get_configuration():
    """アプリケーション設定情報を取得"""
    logger.info("Configuration requested")
    
    return ConfigurationResponse(
        available_accounts=settings.available_accounts,
        target_folder_keyword=settings.target_folder_keyword,
        max_workers=settings.max_workers,
        gemini_model=settings.gemini_model,
        environment=settings.environment,
        features={
            "structured_analysis": True,
            "batch_operations": True,
            "export": False,  # 未実装
            "search": False   # 未実装
        }
    )


# ルートエンドポイント
@app.get("/")
async def root():
    """ルートエンドポイント"""
    return {
        "message": f"Welcome to {settings.app_name}",
        "version": settings.app_version,
        "docs_url": "/docs" if settings.debug else None,
        "health_check": "/health",
        "api_prefix": "/api/v1"
    }


# APIルーターを登録
app.include_router(meetings.router, prefix="/api/v1")
app.include_router(structured_data.router, prefix="/api/v1")


# 開発用サーバー起動
if __name__ == "__main__":
    logger.info(f"Starting development server on {settings.host}:{settings.port}")
    
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )