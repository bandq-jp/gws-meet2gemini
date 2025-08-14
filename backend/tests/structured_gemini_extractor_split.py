#!/usr/bin/env python3
"""
Gemini 2.5 Pro構造化出力プログラム（分割処理版）
大きなスキーマを複数の小さなスキーマに分割して処理することで
INVALID_ARGUMENTエラーを回避する
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Any
from google import genai
import dotenv
import time
import concurrent.futures
from functools import partial

dotenv.load_dotenv()

class GeminiStructuredExtractorSplit:
    """Gemini 2.5 Proを使用した構造化データ抽出器（分割処理版）"""
    
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
    
    def _get_schema_group1(self) -> Dict[str, Any]:
        """転職活動状況・エージェント関連のスキーマ"""
        return {
            "type": "object",
            "properties": {
                "transfer_activity_status": {
                    "type": "string",
                    "enum": [
                        "情報収集中（転職意欲高）",
                        "情報収集中（転職意欲低）",
                        "他社エージェント面談済み",
                        "企業打診済み ~ 一次選考フェーズ",
                        "最終面接待ち ~ 内定済み"
                    ],
                    "description": "転職活動状況"
                },
                "agent_count": {
                    "type": "string",
                    "description": "何名のエージェントと話したか"
                },
                "current_agents": {
                    "type": "string",
                    "description": "すでに利用しているエージェントの社名"
                },
                "introduced_jobs": {
                    "type": "string",
                    "description": "他社エージェントに紹介された求人"
                },
                "job_appeal_points": {
                    "type": "string",
                    "description": "紹介求人の魅力点"
                },
                "job_concerns": {
                    "type": "string",
                    "description": "紹介求人の懸念点"
                },
                "companies_in_selection": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "すでに選考中の企業名/フェーズ"
                },
                "other_offer_salary": {
                    "type": "string",
                    "description": "他社オファー年収見込み"
                },
                "other_company_intention": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "他社意向度及び見込み"
                }
            },
            "required": []
        }
    
    def _get_schema_group2(self) -> Dict[str, Any]:
        """転職理由・希望条件のスキーマ"""
        return {
            "type": "object",
            "properties": {
                "transfer_reasons": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "給与が低い・昇給が見込めない",
                            "社内の雰囲気が悪い",
                            "人間関係が悪い",
                            "尊敬できる人がいない",
                            "評価制度に対する不満",
                            "肉体的または精神的に辛い",
                            "社員を育てる環境がない",
                            "意見が言いにいく/通らない",
                            "昇進・キャリアアップが望めない",
                            "ハラスメント",
                            "労働時間に不満（残業が多い / 休日出勤がある）",
                            "スキルアップしたい",
                            "離職率が高い",
                            "業界・会社の先行きが不安",
                            "キャリアチェンジしたい"
                        ]
                    },
                    "description": "転職検討理由（複数選択可）"
                },
                "transfer_trigger": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "転職検討理由 / きっかけ"
                },
                "desired_timing": {
                    "type": "string",
                    "enum": [
                        "すぐにでも",
                        "3ヶ月以内",
                        "6ヶ月以内",
                        "1年以内",
                        "1年以上先"
                    ],
                    "description": "転職希望の時期"
                },
                "timing_details": {
                    "type": "string",
                    "description": "転職希望時期の詳細"
                },
                "current_job_status": {
                    "type": "string",
                    "enum": [
                        "離職中",
                        "離職確定",
                        "離職未確定"
                    ],
                    "description": "現職状況"
                },
                "transfer_status_memo": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "フリーメモ（転職状況）"
                },
                "transfer_priorities": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "転職軸（オープン）"
                }
            },
            "required": []
        }
    
    def _get_schema_group3(self) -> Dict[str, Any]:
        """職歴・経験のスキーマ"""
        return {
            "type": "object",
            "properties": {
                "career_history": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "職歴"
                },
                "current_duties": {
                    "type": "string",
                    "description": "現職での担当業務"
                },
                "company_good_points": {
                    "type": "string",
                    "description": "現職企業の良いところ"
                },
                "company_bad_points": {
                    "type": "string",
                    "description": "現職企業の悪いところ"
                },
                "enjoyed_work": {
                    "type": "string",
                    "description": "これまでの仕事で楽しかったこと/好きだったこと"
                },
                "difficult_work": {
                    "type": "string",
                    "description": "これまでの仕事で辛かったこと/嫌だったこと"
                }
            },
            "required": []
        }
    
    def _get_schema_group4(self) -> Dict[str, Any]:
        """希望業界・職種のスキーマ（短縮版）"""
        return {
            "type": "object",
            "properties": {
                "experience_industry": {
                    "type": "string",
                    "enum": [
                        "こだわりなし",
                        "サービス：人材（人材紹介）",
                        "サービス：人材（人材紹介以外）",
                        "IT・通信：ソフトウェア・SaaS",
                        "IT・通信：その他",
                        "メーカー",
                        "商社",
                        "金融：銀行",
                        "金融：証券",
                        "金融：保険",
                        "金融：その他",
                        "サービス：コンサルティング",
                        "サービス：その他サービス",
                        "建設・不動産",
                        "流通・小売",
                        "広告・メディア",
                        "運輸・物流",
                        "エネルギー・インフラ",
                        "専門職：士業",
                        "官公庁・公社・団体"
                    ],
                    "description": "経験業界"
                },
                "experience_field_hr": {
                    "type": "string",
                    "enum": [
                        "特になし",
                        "物流",
                        "工場",
                        "医療福祉",
                        "若手・第二新卒",
                        "新卒",
                        "ITエンジニア",
                        "士業",
                        "メーカー",
                        "不動産",
                        "建設",
                        "総合型",
                        "コンサル",
                        "金融",
                        "営業職",
                        "バックオフィス・人事",
                        "その他"
                    ],
                    "description": "経験領域（人材）"
                },
                "desired_industry": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "希望業界（自由記述）"
                },
                "industry_reason": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "業界希望理由"
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
                    },
                    "description": "希望職種"
                },
                "position_industry_reason": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "職種・業界希望理由"
                }
            },
            "required": []
        }
    
    def _get_schema_group5(self) -> Dict[str, Any]:
        """年収・待遇条件のスキーマ"""
        return {
            "type": "object",
            "properties": {
                "current_salary": {
                    "type": "integer",
                    "description": "現年収（数字のみ）"
                },
                "salary_breakdown": {
                    "type": "string",
                    "description": "現年収内訳"
                },
                "desired_first_year_salary": {
                    "type": "number",
                    "description": "初年度希望年収（数字）"
                },
                "base_incentive_ratio": {
                    "type": "string",
                    "description": "基本給・インセンティブ比率"
                },
                "max_future_salary": {
                    "type": "string",
                    "description": "将来的な年収の最大値"
                },
                "salary_memo": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "フリーメモ（給与）"
                },
                "remote_time_memo": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "フリーメモ（リモート・時間）"
                },
                "ca_ra_focus": {
                    "type": "string",
                    "description": "CA起点/RA起点"
                },
                "customer_acquisition": {
                    "type": "string",
                    "description": "集客方法/比率"
                },
                "new_existing_ratio": {
                    "type": "string",
                    "description": "新規/既存の比率"
                }
            },
            "required": []
        }
    
    def _get_schema_group6(self) -> Dict[str, Any]:
        """企業文化・キャリアビジョンのスキーマ"""
        return {
            "type": "object",
            "properties": {
                "business_vision": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "拡大・成長",
                            "IPO",
                            "少数精鋭",
                            "長期安定",
                            "こだわりなし"
                        ]
                    },
                    "description": "事業構想"
                },
                "desired_employee_count": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "-30",
                            "30-150",
                            "150-300",
                            "300-"
                        ]
                    },
                    "description": "希望従業員数"
                },
                "culture_scale_memo": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "フリーメモ（会社カルチャー・規模）"
                },
                "career_vision": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "プレイヤー",
                            "マネージャー/企画/事業責任者",
                            "安定/WLB",
                            "人事（採用)",
                            "人事（組織開発）",
                            "事業開発/立ち上げ",
                            "人事組織コンサル",
                            "採用コンサル",
                            "独立"
                        ]
                    },
                    "description": "キャリアビジョン"
                }
            },
            "required": []
        }
    
    def read_text_file(self, file_path: str) -> str:
        """テキストファイルを読み込み"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read()
        except UnicodeDecodeError:
            with open(file_path, 'r', encoding='shift_jis') as file:
                return file.read()
    
    def extract_structured_data_group(self, text_content: str, schema: Dict[str, Any], group_name: str, max_retries: int = 3) -> Dict[str, Any]:
        """
        指定されたスキーマグループでの構造化データ抽出（リトライ機能付き）
        
        Args:
            text_content: 抽出対象のテキスト
            schema: 使用するスキーマ
            group_name: グループ名（ログ用）
            max_retries: 最大リトライ回数
            
        Returns:
            抽出された構造化データ
        """
        prompt = f"""
以下の議事録テキストから、{group_name}に関する情報を構造化して抽出してください。

【テキスト内容】
{text_content}

【抽出ルール】
1. テキストに明確に記載されている情報のみを抽出してください
2. 推測や補完は行わず、記載がない項目はnullとしてください。不明な情報は必ずnullとしてください。
3. 複数選択可能な項目は配列形式で記載してください
4. 選択リストの場合は、提供された選択肢の中から最も適切なものを選んでください
5. 数値項目は適切な型（整数・小数）で記載してください
6. 年収などの数値は数字のみを抽出してください（「万円」などの単位は除く）

{group_name}の情報のみを構造化されたJSONで回答してください。
"""
        
        for attempt in range(max_retries):
            try:
                response = self.client.models.generate_content(
                    model="gemini-2.5-pro",
                    contents=prompt,
                    config={
                        "response_mime_type": "application/json",
                        "response_schema": schema,
                        "temperature": 0.1,
                        "max_output_tokens": 20000
                    }
                )
                
                if response and response.text:
                    return json.loads(response.text)
                else:
                    print(f"{group_name}: レスポンスが空です (試行 {attempt + 1}/{max_retries})")
                    if attempt < max_retries - 1:
                        time.sleep(1)  # 1秒待機してリトライ
                        continue
                
            except json.JSONDecodeError as e:
                print(f"{group_name}: JSON解析エラー (試行 {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(1)
                    continue
            except Exception as e:
                print(f"{group_name}: API呼び出しエラー (試行 {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(2)  # エラー時は少し長めに待機
                    continue
        
        print(f"{group_name}: 全ての試行が失敗しました")
        return {}
    
    def extract_all_structured_data(self, text_content: str, use_parallel: bool = True) -> Dict[str, Any]:
        """
        全スキーマグループでの構造化データ抽出（並列処理対応）
        
        Args:
            text_content: 抽出対象のテキスト
            use_parallel: 並列処理を使用するかどうか
            
        Returns:
            全グループの結合された構造化データ
        """
        schema_groups = [
            (self._get_schema_group1(), "転職活動状況・エージェント関連"),
            (self._get_schema_group2(), "転職理由・希望条件"),
            (self._get_schema_group3(), "職歴・経験"),
            (self._get_schema_group4(), "希望業界・職種"),
            (self._get_schema_group5(), "年収・待遇条件"),
            (self._get_schema_group6(), "企業文化・キャリアビジョン")
        ]
        
        combined_result = {}
        
        if use_parallel:
            # 並列処理で実行
            extract_func = partial(self._extract_group_wrapper, text_content)
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                # 全グループを並列で処理
                future_to_group = {}
                for schema, group_name in schema_groups:
                    print(f"{group_name}を処理中...")
                    future = executor.submit(extract_func, schema, group_name)
                    future_to_group[future] = group_name
                
                # 結果を収集
                for future in concurrent.futures.as_completed(future_to_group):
                    group_name = future_to_group[future]
                    try:
                        group_result = future.result()
                        combined_result.update(group_result)
                    except Exception as e:
                        print(f"{group_name}の並列処理エラー: {e}")
        else:
            # 順次処理で実行
            for schema, group_name in schema_groups:
                print(f"{group_name}を処理中...")
                group_result = self.extract_structured_data_group(text_content, schema, group_name)
                combined_result.update(group_result)
        
        return combined_result
    
    def _extract_group_wrapper(self, text_content: str, schema: Dict[str, Any], group_name: str) -> Dict[str, Any]:
        """
        並列処理用のラッパー関数
        """
        return self.extract_structured_data_group(text_content, schema, group_name)
    
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
            output_json_path = text_path.parent / f"{text_path.stem}_extracted_split.json"
        
        print(f"テキストファイルを読み込み中: {text_file_path}")
        text_content = self.read_text_file(text_file_path)
        
        print("Gemini 2.5 proで構造化データを抽出中（分割処理・並列実行）...")
        extracted_data = self.extract_all_structured_data(text_content, use_parallel=True)
        
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
            sample_file = current_dir / "sample_interview_split.txt"
            with open(sample_file, 'w', encoding='utf-8') as f:
                f.write(sample_text)
            text_file = str(sample_file)
            print(f"サンプルファイルを作成しました: {text_file}")
    else:
        text_file = sys.argv[1]
    
    try:
        extractor = GeminiStructuredExtractorSplit()
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