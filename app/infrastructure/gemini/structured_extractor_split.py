from __future__ import annotations
"""
Gemini 2.5 Pro 構造化出力（分割処理版）

tests/structured_gemini_extractor_split.py をアプリ内に移行し、
API キーの解決のみ環境変数ベースに調整。
本実装では、要求された全項目を網羅するようスキーマを拡張し、
大きなスキーマはグループ分割して安定抽出を行う。
"""
import json
import os
from typing import Dict, Any
from google import genai
import dotenv
import time
import concurrent.futures
from functools import partial

dotenv.load_dotenv()


class GeminiStructuredExtractorSplit:
    """Gemini 2.5 Proを使用した構造化データ抽出器（分割処理版）"""

    def __init__(self, api_key: str | None = None):
        if api_key:
            self.client = genai.Client(api_key=api_key)
        else:
            gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
            if not gemini_key:
                raise ValueError(
                    "Gemini API key is required. Set GEMINI_API_KEY or GOOGLE_API_KEY."
                )
            self.client = genai.Client(api_key=gemini_key)

    # グループ1: 転職活動状況・エージェント関連
    def _get_schema_group1(self) -> Dict[str, Any]:
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
                        "最終面接待ち ~ 内定済み",
                    ],
                    "description": "転職活動状況",
                },
                "agent_count": {
                    "type": "string",
                    "description": "何名のエージェントと話したか",
                },
                "current_agents": {
                    "type": "string",
                    "description": "すでに利用しているエージェントの社名",
                },
                "introduced_jobs": {
                    "type": "string",
                    "description": "他社エージェントに紹介された求人",
                },
                "job_appeal_points": {
                    "type": "string",
                    "description": "紹介求人の魅力点",
                },
                "job_concerns": {
                    "type": "string",
                    "description": "紹介求人の懸念点",
                },
                "companies_in_selection": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "すでに選考中の企業名/フェーズ",
                },
                "other_offer_salary": {
                    "type": "string",
                    "description": "他社オファー年収見込み",
                },
                "other_company_intention": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "他社意向度及び見込み",
                },
            },
            "required": [],
        }

    # グループ2: 転職理由・希望時期・メモ・転職軸
    def _get_schema_group2(self) -> Dict[str, Any]:
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
                            "意見が言いにくい/通らない",
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
                            "人と関わる仕事をした",
                        ],
                    },
                    "description": "転職検討理由（複数選択可）",
                },
                "transfer_trigger": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "転職検討理由 / きっかけ",
                },
                "desired_timing": {
                    "type": "string",
                    "enum": [
                        "すぐにでも",
                        "3ヶ月以内",
                        "6ヶ月以内",
                        "1年以内",
                        "1年以上先",
                        "まだわからない",
                    ],
                    "description": "転職希望の時期",
                },
                "timing_details": {
                    "type": "string",
                    "description": "転職希望時期の詳細",
                },
                "current_job_status": {
                    "type": "string",
                    "enum": ["離職中", "離職確定", "離職未確定"],
                    "description": "現職状況",
                },
                "transfer_status_memo": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "フリーメモ（転職状況）",
                },
                "transfer_axis_primary": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "転職軸（最重要）",
                },
                "transfer_priorities": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "転職軸（オープン）",
                },
            },
            "required": [],
        }

    # グループ3: 職歴・経験（自由記述系）
    def _get_schema_group3(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "career_history": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "職歴",
                },
                "current_duties": {
                    "type": "string",
                    "description": "現職での担当業務",
                },
                "company_good_points": {
                    "type": "string",
                    "description": "現職企業の良いところ",
                },
                "company_bad_points": {
                    "type": "string",
                    "description": "現職企業の悪いところ",
                },
                "enjoyed_work": {
                    "type": "string",
                    "description": "これまでの仕事で楽しかったこと/好きだったこと",
                },
                "difficult_work": {
                    "type": "string",
                    "description": "これまでの仕事で辛かったこと/嫌だったこと",
                },
            },
            "required": [],
        }

    # グループ4: 業界・職種（選択肢拡張）
    def _get_schema_group4(self) -> Dict[str, Any]:
        industries_long = [
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
            "官公庁・公社・団体",
        ]
        experience_fields_hr_long = [
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
            "エグゼクティブ",
        ]
        return {
            "type": "object",
            "properties": {
                "experience_industry": {
                    "type": "string",
                    "enum": industries_long,
                    "description": "経験業界",
                },
                "experience_field_hr": {
                    "type": "string",
                    "enum": experience_fields_hr_long,
                    "description": "経験領域（人材）",
                },
                "desired_industry": {
                    "type": "array",
                    "items": {"type": "string", "enum": industries_long},
                    "description": "希望業界",
                },
                "industry_reason": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "業界希望理由",
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
                            "こだわりなし",
                        ],
                    },
                    "description": "希望職種",
                },
                "position_industry_reason": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "職種・業界希望理由",
                },
            },
            "required": [],
        }

    # グループ5: 年収・待遇・働き方
    def _get_schema_group5(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "current_salary": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 9999,
                    "description": "現年収（4桁の数字のみ／例: 600=600万円）",
                },
                "salary_breakdown": {
                    "type": "string",
                    "description": "現年収内訳（基本給・賞与・インセンティブ）",
                },
                "desired_first_year_salary": {
                    "type": "number",
                    "description": "初年度希望年収（数字）",
                },
                "base_incentive_ratio": {
                    "type": "string",
                    "description": "基本給・インセンティブ比率",
                },
                "max_future_salary": {
                    "type": "string",
                    "description": "将来的な年収の最大値",
                },
                "salary_memo": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "フリーメモ（給与）",
                },
                "remote_time_memo": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "フリーメモ（リモート・時間）",
                },
                "ca_ra_focus": {"type": "string", "description": "CA起点/RA起点"},
                "customer_acquisition": {"type": "string", "description": "集客方法/比率"},
                "new_existing_ratio": {"type": "string", "description": "新規/既存の比率"},
            },
            "required": [],
        }

    # グループ6: 会社カルチャー・規模・キャリア
    def _get_schema_group6(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "business_vision": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["拡大・成長", "IPO", "少数精鋭", "長期安定", "こだわりなし"],
                    },
                    "description": "事業構想",
                },
                "desired_employee_count": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["-30", "30-150", "150-300", "300-"],
                    },
                    "description": "希望従業員数",
                },
                "culture_scale_memo": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "フリーメモ（会社カルチャー・規模）",
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
                            "独立",
                        ],
                    },
                    "description": "キャリアビジョン",
                },
            },
            "required": [],
        }

    # 共通ユーティリティ
    def read_text_file(self, file_path: str) -> str:
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                return file.read()
        except UnicodeDecodeError:
            with open(file_path, "r", encoding="shift_jis") as file:
                return file.read()

    def extract_structured_data_group(
        self,
        text_content: str,
        schema: Dict[str, Any],
        group_name: str,
        max_retries: int = 3,
    ) -> Dict[str, Any]:
        prompt = f"""
以下の議事録テキストから、{group_name}に関する情報を構造化して抽出してください。

【テキスト内容】
{text_content}

【抽出ルール】
1. テキストに明確に記載されている情報のみを抽出してください。
2. 推測や補完は行わず、記載がない項目はnullとしてください。不明な情報は必ずnullとしてください。
3. 複数選択可能な項目は配列形式で記載してください。
4. 選択リストの場合は、提供された選択肢の中から最も適切なものを選んでください。
5. 数値項目は適切な型（整数・小数）で記載してください。
6. 年収などの数値は数字のみを抽出してください（「万円」などの単位は除く）。

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
                        "max_output_tokens": 8192,
                    },
                )

                if response and getattr(response, "text", None):
                    return json.loads(response.text)
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
        self, text_content: str, use_parallel: bool = True
    ) -> Dict[str, Any]:
        schema_groups = [
            (self._get_schema_group1(), "転職活動状況・エージェント関連"),
            (self._get_schema_group2(), "転職理由・希望条件"),
            (self._get_schema_group3(), "職歴・経験"),
            (self._get_schema_group4(), "希望業界・職種"),
            (self._get_schema_group5(), "年収・待遇条件"),
            (self._get_schema_group6(), "企業文化・キャリアビジョン"),
        ]

        combined_result: Dict[str, Any] = {}
        if use_parallel:
            extract_func = partial(self._extract_group_wrapper, text_content)
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
                    self.extract_structured_data_group(text_content, schema, group_name)
                )
        return combined_result

    def _extract_group_wrapper(
        self, text_content: str, schema: Dict[str, Any], group_name: str
    ) -> Dict[str, Any]:
        return self.extract_structured_data_group(text_content, schema, group_name)

