"""
構造化データ抽出サービス（リファクタリング版）

DDD/オニオンアーキテクチャに従い、以下のように責任を分離：
- ドメイン層: スキーマ定義（business rules）
- インフラ層: Gemini AI接続、抽出ロジック（technical details）

元のGeminiStructuredExtractorSplitクラスから以下を分離：
- スキーマ定義 → domain/schemas/structured_extraction_schema.py
- Geminiクライアント → infrastructure/gemini/client.py
- 抽出ロジック → このファイル（responsibility: orchestration）
"""
from __future__ import annotations
import json
import time
import concurrent.futures
from typing import Dict, Any, Optional
from functools import partial

from app.domain.schemas.structured_extraction_schema import StructuredExtractionSchema
from app.infrastructure.gemini.client import GeminiClient


class StructuredDataExtractor:
    """構造化データ抽出サービス（分割処理対応）"""
    
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
        self.gemini_client = GeminiClient(
            api_key=api_key,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens
        )
    
    def extract_structured_data_group(
        self,
        text_content: str,
        schema: Dict[str, Any],
        group_name: str,
        candidate_name: Optional[str] = None,
        agent_name: Optional[str] = None,
        max_retries: int = 3,
    ) -> Dict[str, Any]:
        """特定のグループのスキーマを使用して構造化データを抽出する
        
        Args:
            text_content: 議事録テキスト
            schema: 抽出スキーマ
            group_name: グループ名
            candidate_name: 候補者名
            agent_name: エージェント名
            max_retries: 最大リトライ回数
            
        Returns:
            抽出された構造化データ
        """
        # 話者情報の構築
        speaker_info = self._build_speaker_info(candidate_name, agent_name)
        
        prompt = f"""
以下の議事録テキストから、{group_name}に関する情報を構造化して抽出してください。
{speaker_info}
【テキスト内容】
{text_content}

【抽出ルール】
1. テキストに明確に記載されている情報のみを抽出してください。
2. すべての前提として、推測や補完は行わず、記載がない項目はnullとしてください。不明な情報は必ずnullとしてください。
3. 複数選択可能な項目は配列形式で記載してください。
4. 選択リストの場合は、提供された選択肢の中から最も適切なものを選んでください。
5. 数値項目は適切な型（整数・小数）で記載してください。
6. 年収などの数値は数字のみを抽出してください（「万円」などの単位は除く）。
7. 話者情報を参考に、求職者とエージェントの発言を適切に区別して情報を抽出してください。

{group_name}の情報のみを構造化されたJSONで回答してください。
"""
        
        # リトライロジック
        for attempt in range(max_retries):
            try:
                response_text = self.gemini_client.generate_content(
                    prompt=prompt,
                    schema=schema
                )
                
                if response_text:
                    return json.loads(response_text)
                else:
                    if attempt < max_retries - 1:
                        time.sleep(1)
                        continue
                        
            except json.JSONDecodeError:
                if attempt < max_retries - 1:
                    time.sleep(1)
                    continue
            except Exception:
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
        
        return {}
    
    def extract_all_structured_data(
        self, 
        text_content: str, 
        candidate_name: Optional[str] = None,
        agent_name: Optional[str] = None, 
        use_parallel: bool = True
    ) -> Dict[str, Any]:
        """全グループのスキーマを使用して構造化データを抽出する
        
        Args:
            text_content: 議事録テキスト
            candidate_name: 候補者名
            agent_name: エージェント名
            use_parallel: 並列処理を使用するか
            
        Returns:
            すべてのグループから抽出された構造化データ
        """
        schema_groups = StructuredExtractionSchema.get_all_schema_groups()
        combined_result: Dict[str, Any] = {}
        
        if use_parallel:
            extract_func = partial(
                self._extract_group_wrapper, 
                text_content, 
                candidate_name, 
                agent_name
            )
            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                futures = [
                    executor.submit(extract_func, schema, name)
                    for schema, name in schema_groups
                ]
                for fut in concurrent.futures.as_completed(futures):
                    try:
                        combined_result.update(fut.result())
                    except Exception:
                        # 個別グループの失敗は握りつぶし、全体の処理を継続
                        pass
        else:
            for schema, group_name in schema_groups:
                combined_result.update(
                    self.extract_structured_data_group(
                        text_content, schema, group_name, candidate_name, agent_name
                    )
                )
        
        return combined_result
    
    def _extract_group_wrapper(
        self, 
        text_content: str, 
        candidate_name: Optional[str], 
        agent_name: Optional[str], 
        schema: Dict[str, Any], 
        group_name: str
    ) -> Dict[str, Any]:
        """並列処理用のラッパー関数"""
        return self.extract_structured_data_group(
            text_content, schema, group_name, candidate_name, agent_name
        )
    
    def _build_speaker_info(
        self, 
        candidate_name: Optional[str], 
        agent_name: Optional[str]
    ) -> str:
        """話者情報を構築する
        
        Args:
            candidate_name: 候補者名
            agent_name: エージェント名
            
        Returns:
            話者情報の文字列
        """
        if candidate_name and agent_name:
            return f"""
【話者情報】
- 求職者名: {candidate_name} (注意: Google Meetでの表示名のため、議事録内では異なる名前で表記されている可能性があります)
- エージェント名: {agent_name} (注意: 議事録内では異なる名前で表記されている可能性があります)
- 基本的にエージェント以外の発言は求職者によるものです
- エージェントの発言は、主催者({agent_name})の発言として識別してください
"""
        elif candidate_name:
            return f"""
【話者情報】
- 求職者名: {candidate_name} (注意: Google Meetでの表示名のため、議事録内では異なる名前で表記されている可能性があります)
- 基本的にエージェント以外の発言は求職者によるものです
"""
        elif agent_name:
            return f"""
【話者情報】  
- エージェント名: {agent_name} (注意: 議事録内では異なる名前で表記されている可能性があります)
- エージェントの発言は、主催者({agent_name})の発言として識別してください
- 基本的にエージェント以外の発言は求職者によるものです
"""
        return ""


# 後方互換性のため、元のクラス名でもアクセス可能にする
GeminiStructuredExtractorSplit = StructuredDataExtractor