from __future__ import annotations
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.infrastructure.config.settings import get_settings as get_backend_settings

router = APIRouter()


class GeminiSettings(BaseModel):
    """Gemini AI設定"""
    gemini_enabled: bool = Field(default=True, description="Gemini AI処理を有効にするかどうか")
    gemini_model: str = Field(default="gemini-2.5-pro", description="使用するGeminiモデル")
    gemini_max_tokens: int = Field(default=20000, ge=1024, le=32768, description="最大トークン数")
    gemini_temperature: float = Field(default=0.1, ge=0.0, le=2.0, description="温度パラメータ")
    gemini_fallback_enabled: bool = Field(default=True, description="Pro失敗時にFlashへ自動フォールバック")


class SettingsResponse(BaseModel):
    """設定レスポンス"""
    gemini: GeminiSettings


# 設定を格納するグローバル変数（本来はDBや設定ファイルに保存）
_current_settings = {
    "gemini": GeminiSettings()
}


@router.get("/", response_model=SettingsResponse)
async def get_settings_endpoint():
    """現在の設定を取得"""
    try:
        # 環境変数から現在の設定を読み込み
        backend_settings = get_backend_settings()
        
        # Gemini設定を構築（環境変数から直接取得）
        gemini_settings = GeminiSettings(
            gemini_enabled=bool(backend_settings.gemini_api_key),  # API キーがあれば有効
            gemini_model=backend_settings.gemini_model,
            gemini_max_tokens=backend_settings.gemini_max_tokens,
            gemini_temperature=backend_settings.gemini_temperature,
            gemini_fallback_enabled=True,  # フォールバックモデルが設定されていれば有効
        )
        
        return SettingsResponse(gemini=gemini_settings)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"設定の取得に失敗しました: {str(e)}")



@router.get("/gemini/models", response_model=dict)
async def get_available_gemini_models():
    """利用可能なGeminiモデル一覧を取得"""
    models = [
        {
            "value": "gemini-2.5-pro",
            "label": "Gemini 2.5 Pro",
            "description": "最新の高性能モデル（推奨）"
        },
        {
            "value": "gemini-2.5-flash",
            "label": "Gemini 2.5 Flash", 
            "description": "最新の高速モデル"
        },
        {
            "value": "gemini-1.5-pro",
            "label": "Gemini 1.5 Pro (レガシー)",
            "description": "従来の高性能モデル"
        },
        {
            "value": "gemini-1.5-flash",
            "label": "Gemini 1.5 Flash (レガシー)",
            "description": "従来の高速モデル"
        }
    ]
    return {"models": models}


def get_current_gemini_settings() -> GeminiSettings:
    """現在のGemini設定を取得（他のモジュールから使用）"""
    # 環境変数から現在の設定を取得
    backend_settings = get_backend_settings()
    
    return GeminiSettings(
        gemini_enabled=bool(backend_settings.gemini_api_key),  # API キーがあれば有効
        gemini_model=backend_settings.gemini_model,
        gemini_max_tokens=backend_settings.gemini_max_tokens,
        gemini_temperature=backend_settings.gemini_temperature,
        gemini_fallback_enabled=True,  # 環境変数でフォールバックモデルが設定されていれば有効
    )
