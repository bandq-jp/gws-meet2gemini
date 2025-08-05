#!/usr/bin/env python3
"""
Gemini 2.5 Pro構造化出力プログラム
テキストファイルを読み取り、structure.csvで定義された構造に基づいて
OpenAPI 3.0スキーマを使用してJSON形式で構造化出力を行う
"""

import json
import csv
import os
from pathlib import Path
from typing import Dict, List, Any
from google import genai
import dotenv

dotenv.load_dotenv()

class GeminiStructuredExtractor:
    """Gemini 2.5 Proを使用した構造化データ抽出器"""
    
    def __init__(self, api_key: str = None):
        """
        初期化
        
        Args:
            api_key: Gemini API キー（環境変数GOOGLE_API_KEYからも取得可能）
        """
        if api_key:
            genai.configure(api_key=api_key)
        else:
            # 環境変数から取得を試行
            if not os.getenv('GOOGLE_API_KEY'):
                raise ValueError("Gemini API key is required. Set GOOGLE_API_KEY environment variable or pass api_key parameter.")
            genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))
        
        self.model = genai.GenerativeModel('gemini-2.5-pro')
        self.schema = self._build_openapi_schema()
    
    def _build_openapi_schema(self) -> Dict[str, Any]:
        """
        structure.csvの構造に基づいてOpenAPI 3.0スキーマを構築
        項目種類に応じて適切に型を設定：
        - 選択リスト → enum（単一選択）
        - 複数選択リスト → array of enums（複数選択）
        - 配列 → array of strings（自由記述配列）
        - 1行 → string（単一文字列）
        - 長整数 → integer
        - 数値 → number
        
        Returns:
            OpenAPI 3.0スキーマオブジェクト
        """
        return {
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
                    ],
                    "description": "転職活動状況"
                },
                
                # 何名のエージェントと話したか（1行）
                "agent_count": {
                    "type": "string",
                    "description": "何名のエージェントと話したか"
                },
                
                # すでに利用しているエージェントの社名（1行）
                "current_agents": {
                    "type": "string",
                    "description": "すでに利用しているエージェントの社名"
                },
                
                # 他社エージェントに紹介された求人（1行）
                "introduced_jobs": {
                    "type": "string",
                    "description": "他社エージェントに紹介された求人"
                },
                
                # 紹介求人の魅力点（1行）
                "job_appeal_points": {
                    "type": "string",
                    "description": "紹介求人の魅力点"
                },
                
                # 紹介求人の懸念点（1行）
                "job_concerns": {
                    "type": "string",
                    "description": "紹介求人の懸念点"
                },
                
                # すでに選考中の企業名/フェーズ（配列）
                "companies_in_selection": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "すでに選考中の企業名/フェーズ"
                },
                
                # 他社オファー年収見込み（1行）
                "other_offer_salary": {
                    "type": "string",
                    "description": "他社オファー年収見込み"
                },
                
                # 他社意向度及び見込み（配列）
                "other_company_intention": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "他社意向度及び見込み"
                },
                
                # 転職検討理由（複数選択リスト）
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
                            "キャリアチェンジしたい",
                            "働き方に柔軟性がない（リモートワーク不可など）",
                            "不規則な勤務を辞めたい / 土日祝休にしたい",
                            "個人の成果で評価されない",
                            "家庭環境の変化",
                            "顧客志向性の高い仕事がしたい",
                            "売上目標やノルマが厳しい",
                            "裁量権がない",
                            "倒産 / リストラ / 契約期間の満了",
                            "人と関わる仕事をした"
                        ]
                    },
                    "description": "転職検討理由（複数選択可）"
                },
                
                # 転職検討理由 / きっかけ（配列）
                "transfer_trigger": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "転職検討理由 / きっかけ"
                },
                
                # 転職希望の時期（選択リスト）
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
                
                # 転職希望時期の詳細（1行）
                "timing_details": {
                    "type": "string",
                    "description": "転職希望時期の詳細"
                },
                
                # 現職状況（選択リスト）
                "current_job_status": {
                    "type": "string",
                    "enum": [
                        "離職中",
                        "離職確定",
                        "離職未確定"
                    ],
                    "description": "現職状況"
                },
                
                # フリーメモ（転職状況）（配列）
                "transfer_status_memo": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "フリーメモ（転職状況）"
                },
                
                # 転職軸（オープン）（配列）
                "transfer_priorities": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "転職軸（オープン）"
                },
                
                # 職歴（配列）
                "career_history": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "職歴"
                },
                
                # 経験業界（選択リスト）
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
                        "金融：銀行（メガバンク、地方銀行、信用金庫など）",
                        "金融：証券",
                        "金融：保険（生命保険、損害保険）",
                        "金融：アセットマネジメント・投資信託",
                        "金融：リース・クレジット",
                        "金融：フィンテック",
                        "金融：不動産金融",
                        "金融：M&A",
                        "サービス：戦略コンサルティング",
                        "サービス：コンサルティング（戦略以外）",
                        "サービス：教育・研修",
                        "サービス：医療・福祉（病院、介護施設、調剤薬局など）",
                        "サービス：美容・エステ",
                        "サービス：ブライダル",
                        "サービス：旅行・観光",
                        "サービス：ホテル・旅館",
                        "サービス：飲食・外食",
                        "サービス：エンターテイメント（出版、音楽、映像、ゲーム、レジャーなど）",
                        "サービス：スポーツ",
                        "サービス：警備・清掃・ビルメンテナンス",
                        "サービス：その他サービス",
                        "建設・不動産：総合建設（ゼネコン）",
                        "建設・不動産：専門工事（設備、内装、電気など）",
                        "建設・不動産：不動産デベロッパー",
                        "建設・不動産：不動産売買",
                        "建設・不動産：不動産仲介",
                        "建設・不動産：不動産管理",
                        "建設・不動産：建築設計・デザイン",
                        "建設・不動産：都市開発",
                        "流通・小売",
                        "広告・メディア",
                        "運輸・物流",
                        "エネルギー・インフラ",
                        "専門職：士業（弁護士、公認会計士、税理士、弁理士など）",
                        "官公庁・公社・団体"
                    ],
                    "description": "経験業界"
                },
                
                # 経験領域（人材）（選択リスト）
                "experience_field_hr": {
                    "type": "string",
                    "enum": [
                        "特になし",
                        "物流",
                        "工場",
                        "医療福祉",
                        "若手・第二新卒",
                        "新卒",
                        "非正規雇用",
                        "ITエンジニア",
                        "士業",
                        "メーカー",
                        "不動産",
                        "建設",
                        "飲食",
                        "総合型",
                        "M&A",
                        "コンサル",
                        "金融",
                        "営業職",
                        "外資",
                        "薬剤師",
                        "美容師",
                        "保育",
                        "バックオフィス・人事",
                        "デザイナー",
                        "スタートアップ",
                        "牧場、農場",
                        "医師",
                        "教育",
                        "その他（エッセンシャル）",
                        "その他（ミドル）",
                        "エグゼクティブ"
                    ],
                    "description": "経験領域（人材）"
                },
                
                # 現職での担当業務（1行）
                "current_duties": {
                    "type": "string",
                    "description": "現職での担当業務"
                },
                
                # 現職企業の良いところ（1行）
                "company_good_points": {
                    "type": "string",
                    "description": "現職企業の良いところ"
                },
                
                # 現職企業の悪いところ（1行）
                "company_bad_points": {
                    "type": "string",
                    "description": "現職企業の悪いところ"
                },
                
                # これまでの仕事で楽しかったこと/好きだったこと（1行）
                "enjoyed_work": {
                    "type": "string",
                    "description": "これまでの仕事で楽しかったこと/好きだったこと"
                },
                
                # これまでの仕事で辛かったこと/嫌だったこと（1行）
                "difficult_work": {
                    "type": "string",
                    "description": "これまでの仕事で辛かったこと/嫌だったこと"
                },
                
                # 希望業界（複数選択リスト）
                "desired_industry": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "こだわりなし",
                            "サービス：人材（人材紹介）",
                            "サービス：人材（人材紹介以外）",
                            "IT・通信：ソフトウェア・SaaS",
                            "IT・通信：その他",
                            "メーカー",
                            "商社",
                            "金融：銀行（メガバンク、地方銀行、信用金庫など）",
                            "金融：証券",
                            "金融：保険（生命保険、損害保険）",
                            "金融：アセットマネジメント・投資信託",
                            "金融：リース・クレジット",
                            "金融：フィンテック",
                            "金融：不動産金融",
                            "金融：M&A",
                            "サービス：戦略コンサルティング",
                            "サービス：コンサルティング（戦略以外）",
                            "サービス：教育・研修",
                            "サービス：医療・福祉（病院、介護施設、調剤薬局など）",
                            "サービス：美容・エステ",
                            "サービス：ブライダル",
                            "サービス：旅行・観光",
                            "サービス：ホテル・旅館",
                            "サービス：飲食・外食",
                            "サービス：エンターテイメント（出版、音楽、映像、ゲーム、レジャーなど）",
                            "サービス：スポーツ",
                            "サービス：警備・清掃・ビルメンテナンス",
                            "サービス：その他サービス",
                            "建設・不動産：総合建設（ゼネコン）",
                            "建設・不動産：専門工事（設備、内装、電気など）",
                            "建設・不動産：不動産デベロッパー",
                            "建設・不動産：不動産売買",
                            "建設・不動産：不動産仲介",
                            "建設・不動産：不動産管理",
                            "建設・不動産：建築設計・デザイン",
                            "建設・不動産：都市開発",
                            "流通・小売",
                            "広告・メディア",
                            "運輸・物流",
                            "エネルギー・インフラ",
                            "専門職：士業（弁護士、公認会計士、税理士、弁理士など）",
                            "官公庁・公社・団体"
                        ]
                    },
                    "description": "希望業界"
                },
                
                # 業界希望理由（配列）
                "industry_reason": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "業界希望理由"
                },
                
                # 希望職種（複数選択リスト）
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
                
                # CA起点/RA起点（1行）
                "ca_ra_focus": {
                    "type": "string",
                    "description": "CA起点/RA起点"
                },
                
                # 集客方法/比率（1行）
                "customer_acquisition": {
                    "type": "string",
                    "description": "集客方法/比率"
                },
                
                # 新規/既存の比率（1行）
                "new_existing_ratio": {
                    "type": "string",
                    "description": "新規/既存の比率"
                },
                
                # 職種・業界希望理由（配列）
                "position_industry_reason": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "職種・業界希望理由"
                },
                
                # 現年収（数字のみ）（長整数）
                "current_salary": {
                    "type": "integer",
                    "description": "現年収（数字のみ）"
                },
                
                # 現年収内訳（1行）
                "salary_breakdown": {
                    "type": "string",
                    "description": "現年収内訳"
                },
                
                # 初年度希望年収（数字）（数値）
                "desired_first_year_salary": {
                    "type": "number",
                    "description": "初年度希望年収（数字）"
                },
                
                # 基本給・インセンティブ比率（1行）
                "base_incentive_ratio": {
                    "type": "string",
                    "description": "基本給・インセンティブ比率"
                },
                
                # 将来的な年収の最大値（1行）
                "max_future_salary": {
                    "type": "string",
                    "description": "将来的な年収の最大値"
                },
                
                # フリーメモ（給与）（配列）
                "salary_memo": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "フリーメモ（給与）"
                },
                
                # フリーメモ（リモート・時間）（配列）
                "remote_time_memo": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "フリーメモ（リモート・時間）"
                },
                
                # 事業構想（複数選択リスト）
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
                
                # 希望従業員数（複数選択リスト）
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
                
                # フリーメモ（会社カルチャー・規模）（配列）
                "culture_scale_memo": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "フリーメモ（会社カルチャー・規模）"
                },
                
                # キャリアビジョン（複数選択リスト）
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
            "required": []  # すべてのフィールドを任意とする
        }
    
    def read_text_file(self, file_path: str) -> str:
        """
        テキストファイルを読み込み
        
        Args:
            file_path: テキストファイルのパス
            
        Returns:
            ファイルの内容
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read()
        except UnicodeDecodeError:
            # UTF-8で読めない場合はShift_JISを試行
            with open(file_path, 'r', encoding='shift_jis') as file:
                return file.read()
    
    def extract_structured_data(self, text_content: str) -> Dict[str, Any]:
        """
        構造化データを抽出
        
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
            response = self.model.generate_content(
                prompt,
                generation_config={
                    "response_mime_type": "application/json",
                    "response_schema": self.schema,
                    "temperature": 0.1,
                    "max_output_tokens": 65536
                }
            )
            
            return json.loads(response.text)
            
        except Exception as e:
            print(f"構造化出力エラー: {e}")
            raise
    
    def save_json_output(self, data: Dict[str, Any], output_path: str):
        """
        JSONファイルとして保存
        
        Args:
            data: 抽出されたデータ
            output_path: 出力ファイルパス
        """
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
        # 出力パスが指定されていない場合は自動生成
        if output_json_path is None:
            text_path = Path(text_file_path)
            output_json_path = text_path.parent / f"{text_path.stem}_extracted.json"
        
        print(f"テキストファイルを読み込み中: {text_file_path}")
        text_content = self.read_text_file(text_file_path)
        
        print("Gemini 2.5 Proで構造化データを抽出中...")
        extracted_data = self.extract_structured_data(text_content)
        
        print(f"結果をJSONファイルに保存中: {output_json_path}")
        self.save_json_output(extracted_data, str(output_json_path))
        
        print("処理完了!")
        return extracted_data


def main():
    """メイン実行関数"""
    import sys
    
    # コマンドライン引数の処理
    if len(sys.argv) < 2:
        text_file = input("処理するテキストファイルのパスを入力してください: ").strip()
        if not text_file:
            # サンプルファイルを作成
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
            sample_file = current_dir / "sample_interview.txt"
            with open(sample_file, 'w', encoding='utf-8') as f:
                f.write(sample_text)
            text_file = str(sample_file)
            print(f"サンプルファイルを作成しました: {text_file}")
    else:
        text_file = sys.argv[1]
    
    try:
        extractor = GeminiStructuredExtractor()
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