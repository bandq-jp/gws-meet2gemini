#!/usr/bin/env python3
"""
Gemini 2.5 Pro構造化出力プログラム（JSON Schema版）
プレビュー版のresponseJsonSchemaフィールドを使用して
複雑なスキーマを処理する
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Any
from google import genai
import dotenv

dotenv.load_dotenv()

class GeminiStructuredExtractorJsonSchema:
    """Gemini 2.5を使用した構造化データ抽出器（JSON Schema版）"""
    
    def __init__(self, api_key: str = None):
        """
        初期化
        
        Args:
            api_key: Gemini API キー（環境変数GEMINI_API_KEYからも取得可能）
        """
        if api_key:
            self.client = genai.Client(api_key=api_key)
        else:
            gemini_key = os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY')
            if not gemini_key:
                raise ValueError("Gemini API key is required. Set GEMINI_API_KEY or GOOGLE_API_KEY environment variable or pass api_key parameter.")
            self.client = genai.Client(api_key=gemini_key)
    
    def _get_json_schema(self) -> Dict[str, Any]:
        """
        完全なJSON Schemaを構築（プレビュー版responseJsonSchemaフィールド用）
        """
        return {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "properties": {
                # 転職活動状況（選択リスト）
                "transfer_activity_status": {
                    "type": "string",
                    "enum": [
                        "情報収集中（転職意欲高）",
                        "情報収集中（転職意欲低）",
                        "他社エージェント面談済み",
                        "企業打診済み ~ 一次選考フェーズ",
                        "最終面接待ち ~ 内定済み"
                    ]
                },
                "agent_count": {"type": "string"},
                "current_agents": {"type": "string"},
                "introduced_jobs": {"type": "string"},
                "job_appeal_points": {"type": "string"},
                "job_concerns": {"type": "string"},
                "companies_in_selection": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "other_offer_salary": {"type": "string"},
                "other_company_intention": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                # 転職検討理由（複数選択リスト）- 簡略版
                "transfer_reasons": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "給与・昇給",
                            "雰囲気・人間関係",
                            "評価・キャリア",
                            "労働環境",
                            "スキルアップ",
                            "業界・会社の将来性",
                            "働き方・WLB",
                            "その他"
                        ]
                    }
                },
                "transfer_trigger": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "desired_timing": {
                    "type": "string",
                    "enum": ["すぐにでも", "3ヶ月以内", "6ヶ月以内", "1年以内", "1年以上先"]
                },
                "timing_details": {"type": "string"},
                "current_job_status": {
                    "type": "string",
                    "enum": ["離職中", "離職確定", "離職未確定"]
                },
                "transfer_status_memo": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "transfer_priorities": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "career_history": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                # 経験業界（簡略版）
                "experience_industry": {
                    "type": "string",
                    "enum": [
                        "人材",
                        "IT・通信",
                        "メーカー",
                        "商社",
                        "金融",
                        "コンサル",
                        "サービス",
                        "建設・不動産",
                        "流通・小売",
                        "広告・メディア",
                        "その他"
                    ]
                },
                "experience_field_hr": {
                    "type": "string",
                    "enum": [
                        "総合型",
                        "特化型",
                        "新卒",
                        "ITエンジニア",
                        "営業職",
                        "バックオフィス",
                        "エグゼクティブ",
                        "その他"
                    ]
                },
                "current_duties": {"type": "string"},
                "company_good_points": {"type": "string"},
                "company_bad_points": {"type": "string"},
                "enjoyed_work": {"type": "string"},
                "difficult_work": {"type": "string"},
                "desired_industry": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "industry_reason": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "desired_position": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "人材紹介",
                            "個人営業",
                            "法人営業",
                            "企画・マネジメント",
                            "人事",
                            "コンサルタント",
                            "こだわりなし"
                        ]
                    }
                },
                "ca_ra_focus": {"type": "string"},
                "customer_acquisition": {"type": "string"},
                "new_existing_ratio": {"type": "string"},
                "position_industry_reason": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "current_salary": {"type": "integer"},
                "salary_breakdown": {"type": "string"},
                "desired_first_year_salary": {"type": "number"},
                "base_incentive_ratio": {"type": "string"},
                "max_future_salary": {"type": "string"},
                "salary_memo": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "remote_time_memo": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "business_vision": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["拡大・成長", "IPO", "少数精鋭", "長期安定", "こだわりなし"]
                    }
                },
                "desired_employee_count": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["-30", "30-150", "150-300", "300-"]
                    }
                },
                "culture_scale_memo": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "career_vision": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "プレイヤー",
                            "マネージャー",
                            "安定/WLB",
                            "人事",
                            "事業開発",
                            "コンサル",
                            "独立"
                        ]
                    }
                }
            },
            "additionalProperties": false
        }
    
    def read_text_file(self, file_path: str) -> str:
        """テキストファイルを読み込み"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read()
        except UnicodeDecodeError:
            with open(file_path, 'r', encoding='shift_jis') as file:
                return file.read()
    
    def extract_structured_data(self, text_content: str) -> Dict[str, Any]:
        """
        構造化データを抽出（JSON Schema版）
        
        Args:
            text_content: 抽出対象のテキスト
            
        Returns:
            抽出された構造化データ
        """
        prompt = f"""
以下の議事録テキストから、転職に関する情報を構造化して抽出してください。

【テキスト内容】
{text_content}

【抽出ルール】
1. テキストに明確に記載されている情報のみを抽出してください
2. 推測や補完は行わず、記載がない項目はnullとしてください  
3. 複数選択可能な項目は配列形式で記載してください
4. 選択リストの場合は、提供された選択肢の中から最も適切なものを選んでください
5. 数値項目は適切な型（整数・小数）で記載してください
6. 年収などの数値は数字のみを抽出してください（「万円」などの単位は除く）

構造化されたJSONで回答してください。
"""
        
        try:
            # プレビュー版JSON Schemaを使用
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config={
                    "response_mime_type": "application/json",
                    "response_json_schema": self._get_json_schema(),
                    "temperature": 0.1,
                    "max_output_tokens": 65536
                }
            )
            
            return json.loads(response.text)
            
        except Exception as e:
            print(f"JSON Schema構造化出力エラー: {e}")
            # フォールバック：テキストプロンプトでのスキーマ指定
            return self._fallback_text_prompt_extraction(text_content)
    
    def _fallback_text_prompt_extraction(self, text_content: str) -> Dict[str, Any]:
        """
        フォールバック：テキストプロンプトでのスキーマ指定
        """
        prompt = f"""
以下の議事録テキストから、転職に関する情報を構造化して抽出してください。

【テキスト内容】
{text_content}

以下のJSONスキーマに従って回答してください：

{{
  "transfer_activity_status": "情報収集中（転職意欲高）" | "情報収集中（転職意欲低）" | "他社エージェント面談済み" | "企業打診済み ~ 一次選考フェーズ" | "最終面接待ち ~ 内定済み",
  "agent_count": "エージェント数",
  "current_agents": "利用中エージェント名",
  "transfer_reasons": ["転職理由1", "転職理由2"],
  "desired_timing": "すぐにでも" | "3ヶ月以内" | "6ヶ月以内" | "1年以内" | "1年以上先",
  "current_salary": 数値,
  "desired_first_year_salary": 数値,
  "experience_industry": "業界名",
  "desired_position": ["希望職種1", "希望職種2"],
  "career_vision": ["キャリアビジョン1", "キャリアビジョン2"]
}}

記載がない項目はnullとしてください。構造化されたJSONで回答してください。
"""
        
        try:
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config={
                    "temperature": 0.1,
                    "max_output_tokens": 8192
                }
            )
            
            # レスポンスからJSONを抽出
            response_text = response.text.strip()
            if response_text.startswith('```json'):
                response_text = response_text[7:-3]
            elif response_text.startswith('```'):
                response_text = response_text[3:-3]
            
            return json.loads(response_text)
            
        except Exception as e:
            print(f"フォールバック処理エラー: {e}")
            return {}
    
    def save_json_output(self, data: Dict[str, Any], output_path: str):
        """JSONファイルとして保存"""
        with open(output_path, 'w', encoding='utf-8') as file:
            json.dump(data, file, ensure_ascii=False, indent=2)
    
    def process_text_file(self, text_file_path: str, output_json_path: str = None) -> Dict[str, Any]:
        """
        テキストファイルの処理メイン関数
        
        Args:
            text_file_path: 入力テキストファイルのパス
            output_json_path: 出力JSONファイルのパス（省略時は自動生成）
            
        Returns:
            抽出された構造化データ
        """
        if output_json_path is None:
            text_path = Path(text_file_path)
            output_json_path = text_path.parent / f"{text_path.stem}_extracted_json_schema.json"
        
        print(f"テキストファイルを読み込み中: {text_file_path}")
        text_content = self.read_text_file(text_file_path)
        
        print("Gemini 2.5でJSON Schema構造化データを抽出中...")
        extracted_data = self.extract_structured_data(text_content)
        
        print(f"結果をJSONファイルに保存中: {output_json_path}")
        self.save_json_output(extracted_data, str(output_json_path))
        
        print("処理完了!")
        return extracted_data


def main():
    """メイン実行関数"""
    import sys
    
    if len(sys.argv) < 2:
        text_file = input("処理するテキストファイルのパスを入力してください: ").strip()
        if not text_file:
            current_dir = Path(__file__).parent
            sample_text = """
転職活動について相談があります。現在情報収集中で転職意欲は高い状態です。
これまでに3名のエージェントと面談しました。利用しているエージェントはA社とB社です。
他社から紹介された求人は人材業界の営業職で、年収アップが期待できる点が魅力的です。
ただし、残業時間が長そうな点が懸念材料です。

転職を検討している理由は、現在の職場では給与が低く昇給も見込めないためです。
また、社内の雰囲気が悪く人間関係にも悩んでいます。
スキルアップもしたいと考えています。
転職希望時期は3ヶ月以内を考えています。

現在の年収は400万円で、希望年収は500万円以上です。
経験業界はサービス業で、人材業界での経験もあります。
人材業界での経験領域は総合型です。
現職での担当業務は法人営業です。

現職企業の良いところは同僚との関係が良好なことです。
悪いところは給与水準が低いことと成長機会が少ないことです。
これまでの仕事で楽しかったのはお客様から感謝されることでした。
辛かったのは厳しいノルマを課せられることでした。

希望業界は人材業界を中心に考えています。
理由は経験を活かせるからです。
希望職種は法人営業です。
新規開拓と既存顧客対応の比率は6:4程度を希望します。

事業構想としては拡大・成長している企業を希望します。
従業員数は150-300名程度の企業が良いです。
キャリアビジョンとしてはマネージャーを目指したいです。
"""
            sample_file = current_dir / "sample_interview_json_schema.txt"
            with open(sample_file, 'w', encoding='utf-8') as f:
                f.write(sample_text)
            text_file = str(sample_file)
            print(f"サンプルファイルを作成しました: {text_file}")
    else:
        text_file = sys.argv[1]
    
    try:
        extractor = GeminiStructuredExtractorJsonSchema()
        result = extractor.process_text_file(text_file)
        
        print("\n=== 抽出結果のサマリー ===")
        print(f"転職活動状況: {result.get('transfer_activity_status', 'N/A')}")
        print(f"エージェント数: {result.get('agent_count', 'N/A')}")
        print(f"転職検討理由: {result.get('transfer_reasons', 'N/A')}")
        print(f"転職希望時期: {result.get('desired_timing', 'N/A')}")
        print(f"現年収: {result.get('current_salary', 'N/A')}")
        print(f"希望年収: {result.get('desired_first_year_salary', 'N/A')}")
        print(f"希望業界: {result.get('desired_industry', 'N/A')}")
        print(f"希望職種: {result.get('desired_position', 'N/A')}")
        print(f"キャリアビジョン: {result.get('career_vision', 'N/A')}")
        
    except Exception as e:
        print(f"エラーが発生しました: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()