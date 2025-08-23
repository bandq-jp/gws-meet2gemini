"""
Gemini AIクライアント

インフラ層でのGemini AI接続を管理する。
技術的な詳細（認証、リトライロジック、APIコール）をカプセル化し、
ドメイン層やアプリケーション層からの利用を簡素化する。
"""
from __future__ import annotations
import os
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass
from time import perf_counter
from google import genai
import dotenv

dotenv.load_dotenv()


@dataclass
class GeminiResult:
    """Gemini API レスポンスの詳細情報"""
    text: Optional[str]
    usage: Optional[Dict[str, Any]]
    model: str
    finish_reason: Optional[str]
    latency_ms: int
    raw: Any


class GeminiClient:
    """Gemini AIクライアント"""
    
    def __init__(
        self, 
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ):
        """
        Args:
            api_key: Gemini API キー（未指定時は環境変数から取得）
            model: 使用するGeminiモデル
            temperature: 温度パラメータ
            max_tokens: 最大出力トークン数
        """
        # API キーの取得
        if api_key:
            self.client = genai.Client(api_key=api_key)
        else:
            gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
            if not gemini_key:
                raise ValueError(
                    "Gemini API key is required. Set GEMINI_API_KEY or GOOGLE_API_KEY."
                )
            self.client = genai.Client(api_key=gemini_key)
        
        # 設定可能なパラメータ
        self.model = model or "gemini-2.5-pro"
        self.temperature = temperature if temperature is not None else 0.1
        self.max_tokens = max_tokens or 20000
    
    def generate_content(
        self,
        prompt: str,
        schema: Optional[Dict[str, Any]] = None,
        response_mime_type: str = "application/json",
        return_usage: bool = False
    ) -> Union[Optional[str], GeminiResult]:
        """構造化データを生成する
        
        Args:
            prompt: 生成プロンプト
            schema: レスポンススキーマ（JSON構造化出力用）
            response_mime_type: レスポンスMIMEタイプ
            return_usage: 使用量情報を含む詳細な結果を返すか
            
        Returns:
            return_usage=Falseの場合: 生成されたテキスト
            return_usage=Trueの場合: GeminiResult（テキスト + 使用量情報）
        """
        config = {
            "temperature": self.temperature,
            "max_output_tokens": self.max_tokens,
        }
        
        if schema:
            config["response_mime_type"] = response_mime_type
            config["response_schema"] = schema
        
        # パフォーマンス測定
        t0 = perf_counter()
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=config,
        )
        latency_ms = int((perf_counter() - t0) * 1000)
        
        # 後方互換性: return_usage=Falseの場合は従来通りテキストのみ返す
        if not return_usage:
            return getattr(response, "text", None) if response else None
        
        # 使用量情報を含む詳細な結果を返す
        usage = getattr(response, "usage_metadata", None)
        finish_reason = None
        try:
            if response and response.candidates:
                finish_reason = response.candidates[0].finish_reason
        except (AttributeError, IndexError):
            pass
        
        # usage_metadataを辞書に変換（to_dict()メソッドがある場合はそれを使用）
        usage_dict = None
        if usage:
            if hasattr(usage, "to_dict"):
                usage_dict = usage.to_dict()
            elif hasattr(usage, "__dict__"):
                usage_dict = dict(usage.__dict__)
            else:
                # フォールバック: 必要な属性を直接取得
                usage_dict = {
                    "prompt_token_count": getattr(usage, "prompt_token_count", None),
                    "candidates_token_count": getattr(usage, "candidates_token_count", None), 
                    "cached_content_token_count": getattr(usage, "cached_content_token_count", None),
                    "total_token_count": getattr(usage, "total_token_count", None)
                }
        
        return GeminiResult(
            text=getattr(response, "text", None) if response else None,
            usage=usage_dict,
            model=self.model,
            finish_reason=finish_reason,
            latency_ms=latency_ms,
            raw=response
        )
    
    def read_text_file(self, file_path: str) -> str:
        """テキストファイルを読み込む（文字エンコーディング自動判定）
        
        Args:
            file_path: ファイルパス
            
        Returns:
            ファイル内容
        """
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                return file.read()
        except UnicodeDecodeError:
            with open(file_path, "r", encoding="shift_jis") as file:
                return file.read()