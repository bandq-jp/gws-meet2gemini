"""
Gemini AIクライアント

インフラ層でのGemini AI接続を管理する。
技術的な詳細（認証、リトライロジック、APIコール）をカプセル化し、
ドメイン層やアプリケーション層からの利用を簡素化する。
"""
from __future__ import annotations
import os
from typing import Dict, Any, Optional
from google import genai
import dotenv

dotenv.load_dotenv()


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
        response_mime_type: str = "application/json"
    ) -> Optional[str]:
        """構造化データを生成する
        
        Args:
            prompt: 生成プロンプト
            schema: レスポンススキーマ（JSON構造化出力用）
            response_mime_type: レスポンスMIMEタイプ
            
        Returns:
            生成されたテキスト
        """
        config = {
            "temperature": self.temperature,
            "max_output_tokens": self.max_tokens,
        }
        
        if schema:
            config["response_mime_type"] = response_mime_type
            config["response_schema"] = schema
        
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=config,
        )
        
        return getattr(response, "text", None) if response else None
    
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