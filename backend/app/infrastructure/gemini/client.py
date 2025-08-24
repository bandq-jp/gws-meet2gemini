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
from google.genai import types, errors as genai_errors
import httpx
import random
import time
import logging
import dotenv
from app.infrastructure.gemini.error_utils import classify_gemini_error

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
        return_usage: bool = False,
        model_override: Optional[str] = None,
    ) -> Union[Optional[str], GeminiResult]:
        """
        Pro優先。429/5xx/403/404など一部エラー時にFlashへ自動フォールバック。
        スレッドセーフのため self.model は変更せず、ローカルの試行リストで制御。
        
        Args:
            prompt: 生成プロンプト
            schema: レスポンススキーマ（JSON構造化出力用）
            response_mime_type: レスポンスMIMEタイプ
            return_usage: 使用量情報を含む詳細な結果を返すか
            model_override: 使用するモデルの指定（テスト用）
            
        Returns:
            return_usage=Falseの場合: 生成されたテキスト
            return_usage=Trueの場合: GeminiResult（テキスト + 使用量情報）
        """
        logger = logging.getLogger(__name__)
        
        # --- 準備：contents の構築（config はモデルごとに組み立てる） ---
        contents = [types.Content(role="user", parts=[types.Part.from_text(text=prompt)])]

        def _output_cap_for_model(name: str) -> int:
            # 保守的な上限（多くのモデルで 20000 が安全）
            # 必要に応じてモデル別の上限を更新
            model_caps = {
                "gemini-2.5-pro": 20000,
                "gemini-2.5-flash": 20000,
            }
            return model_caps.get(name, 20000)

        def _build_config(name: str) -> types.GenerateContentConfig:
            max_tokens_capped = min(self.max_tokens, _output_cap_for_model(name))
            if schema:
                return types.GenerateContentConfig(
                    temperature=self.temperature,
                    max_output_tokens=max_tokens_capped,
                    response_mime_type=response_mime_type,
                    response_schema=schema,
                )
            return types.GenerateContentConfig(
                temperature=self.temperature,
                max_output_tokens=max_tokens_capped,
            )

        # --- モデル試行リストを作る ---
        primary = model_override or self.model
        fallback_map = {
            "gemini-2.5-pro": ["gemini-2.5-flash"],
            "gemini-1.5-pro": ["gemini-1.5-flash"],
        }
        models_to_try = [primary] + fallback_map.get(primary, [])

        last_exc: Exception | None = None
        for idx, model_name in enumerate(models_to_try):
            t0 = perf_counter()
            try:
                response = self.client.models.generate_content(
                    model=model_name,
                    contents=contents,
                    config=_build_config(model_name),
                )
                latency_ms = int((perf_counter() - t0) * 1000)
                
                # usage, finish_reason などの抽出は既存ロジックを流用
                usage = getattr(response, "usage_metadata", None)
                finish_reason = None
                try:
                    if response and response.candidates:
                        finish_reason = response.candidates[0].finish_reason
                except (AttributeError, IndexError):
                    pass
                
                # レスポンステキストの抽出（response.text が空の場合のフォールバックも実装）
                resp_text = getattr(response, "text", None)
                if not resp_text and getattr(response, "candidates", None):
                    try:
                        parts = getattr(response.candidates[0].content, "parts", [])
                        texts = [getattr(p, "text", "") for p in parts if getattr(p, "text", None)]
                        resp_text = "".join(texts) if texts else None
                    except Exception:
                        pass

                # 安全性ブロックやフィードバック情報がある場合はログに残す
                try:
                    prompt_feedback = getattr(response, "prompt_feedback", None)
                    if prompt_feedback and getattr(prompt_feedback, "block_reason", None):
                        logging.getLogger(__name__).warning(
                            "Gemini prompt blocked: reason=%s", prompt_feedback.block_reason
                        )
                except Exception:
                    pass

                usage_dict = None
                if usage:
                    usage_dict = {
                        "prompt_token_count": getattr(usage, "prompt_token_count", None),
                        "candidates_token_count": getattr(usage, "candidates_token_count", None),
                        "cached_content_token_count": getattr(usage, "cached_content_token_count", None),
                        "total_token_count": getattr(usage, "total_token_count", None),
                        "thoughts_token_count": getattr(usage, "thoughts_token_count", None),
                        "tool_use_prompt_token_count": getattr(usage, "tool_use_prompt_token_count", None),
                    }
                
                result = GeminiResult(
                    text=resp_text,
                    usage=usage_dict,
                    model=model_name,            # ← 実際に使ったモデルを記録
                    finish_reason=finish_reason,
                    latency_ms=latency_ms,
                    raw=response,
                )
                
                # 後方互換性: return_usage=Falseの場合は従来通りテキストのみ返す
                if not return_usage:
                    return result.text
                
                return result

            except genai_errors.APIError as e:
                code = getattr(e, "code", None)
                msg = getattr(e, "message", "") or str(e)
                decision = classify_gemini_error(code, msg)
                logger.warning(
                    "Gemini API error model=%s code=%s reason=%s msg=%s",
                    model_name, code, decision.reason, msg
                )
                last_exc = e
                # 次のモデルがあればフォールバックを試す
                if decision.should_fallback and (idx < len(models_to_try) - 1):
                    # 指数バックオフ＋ジッター（過剰待機は避けて最大 ~3s）
                    delay = min(1.5 ** idx + random.random() * 0.25, 3.0)
                    time.sleep(delay)
                    continue
                # フォールバック不可／最後の試行なら再送せず送出
                raise

            except httpx.TimeoutException as e:
                logger.warning("Gemini request timeout model=%s: %s", model_name, str(e))
                last_exc = e
                if idx < len(models_to_try) - 1:
                    time.sleep(0.25)
                    continue
                raise

            except Exception as e:
                # 予期しないエラーもキャッチしてログ出力
                latency_ms = int((perf_counter() - t0) * 1000)
                logger.error(
                    "Unexpected Gemini API error: model=%s, attempt=%d/%d, latency=%dms, exception_type=%s, error=%s",
                    model_name, idx + 1, len(models_to_try), latency_ms, type(e).__name__, str(e)
                )
                last_exc = e
                if idx < len(models_to_try) - 1:
                    logger.warning("Retrying after unexpected error with next model: %s -> %s", model_name, models_to_try[idx + 1])
                    time.sleep(0.25)
                    continue
                logger.error("Gemini request failed permanently due to unexpected error after %d attempts", len(models_to_try))
                raise

        # 全試行失敗（理論上ここは到達しないが安全のため）
        if last_exc:
            logger.error("All Gemini API attempts failed, raising last exception: %s", type(last_exc).__name__)
            raise last_exc
    
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
