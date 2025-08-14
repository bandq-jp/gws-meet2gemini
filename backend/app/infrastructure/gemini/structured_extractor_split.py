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
    """Gemini を使用した構造化データ抽出器（分割処理版）"""

    def __init__(self, api_key: str | None = None, model: str | None = None, temperature: float | None = None, max_tokens: int | None = None):
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
                    "description": "転職活動状況：現在の転職活動の状況。",
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
                    "description": "今選考中の企業名と、各企業の選考フェーズ（書類選考・一次面接・最終面接など）",
                },
                "other_offer_salary": {
                    "type": "string",
                    "description": "選考中の企業では、どれくらいのオファー年収提示が見込まれるか。",
                },
                "other_company_intention": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "選考中の企業のうち、意向度が高い企業低い企業",
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
                    "description": "転職検討理由（複数選択可）：今回転職活動を始めようと思ったきっかけ",
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
                    "description": "転職希望時期の詳細：具体的には何月ごろか",
                },
                "current_job_status": {
                    "type": "string",
                    "enum": ["離職中", "離職確定", "離職未確定"],
                    "description": "現職状況：現職を退職することは確定しているか？未確定か？現在離職中か？",
                },
                "transfer_status_memo": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "フリーメモ（転職状況）",
                },
                "transfer_axis_primary": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "転職軸（最重要）：今回転職する上での軸（最重要）を自由に記載",
                },
                "transfer_priorities": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "転職軸（オープン）：今回転職する上での軸をオープンに答えてください",
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
                    "description": "職歴：これまでの業界・職種、在籍年数、転職回数など",
                },
                "current_duties": {
                    "type": "string",
                    "description": "現職ではどのような業務を担当しているか",
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
                    "description": "経験業界：これまでに経験した業界",
                },
                "experience_field_hr": {
                    "type": "string",
                    "enum": experience_fields_hr_long,
                    "description": "経験領域（人材）：人材紹介業の経験がある場合に担当した領域（業界）。特化していない場合は総合型",
                },
                "desired_industry": {
                    "type": "array",
                    "items": {"type": "string", "enum": industries_long},
                    "description": "希望業界：今回の転職活動で興味を持っている業界",
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
                    "description": "希望職種：今回の転職活動で興味を持っている職種",
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
                    "description": "現年収（数字のみ）：4桁の整数（例: 600=600万円）",
                },
                "salary_breakdown": {
                    "type": "string",
                    "description": "現年収内訳：基本給・賞与・インセンティブ",
                },
                "desired_first_year_salary": {
                    "type": "number",
                    "description": "初年度希望年収（数字）",
                },
                "base_incentive_ratio": {
                    "type": "string",
                    "description": "基本給・インセンティブ比率：初年度希望年収のうち、基本給が高い方が良いか、インセンティブで稼ぎたいか",
                },
                "max_future_salary": {
                    "type": "string",
                    "description": "将来的な年収の最大値：将来的にはいくらくらいまで年収を上げていきたいか",
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
                "ca_ra_focus": {"type": "string", "description": "CA起点/RA起点：人材紹介を希望する場合、CA起点（求職者支援が主軸）かRA起点（企業の採用課題への貢献が主軸）か"},
                "customer_acquisition": {"type": "string", "description": "集客方法/比率：集客の要望や内訳・比率（スカウト媒体、広告、リファラル、Web、YouTube等）"},
                "new_existing_ratio": {"type": "string", "description": "新規/既存の比率：新規開拓と既存関係強化の希望比率"},
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
                    "description": "事業構想：どのような事業計画・ビジョンを持っている企業で働きたいか。どのようなフェーズ、どのような規模感の会社に入りたいか",
                },
                "desired_employee_count": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["-30", "30-150", "150-300", "300-"],
                    },
                    "description": "希望従業員数：どれくらいの従業員数がいる会社で働きたいか",
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
        candidate_name: str | None = None,
        agent_name: str | None = None,
        max_retries: int = 3,
    ) -> Dict[str, Any]:
        # 話者情報の構築
        speaker_info = ""
        if candidate_name and agent_name:
            speaker_info = f"""
【話者情報】
- 求職者名: {candidate_name} (注意: Google Meetでの表示名のため、議事録内では異なる名前で表記されている可能性があります)
- エージェント名: {agent_name} (注意: 議事録内では異なる名前で表記されている可能性があります)
- 基本的にエージェント以外の発言は求職者によるものです
- エージェントの発言は、主催者({agent_name})の発言として識別してください
"""
        elif candidate_name:
            speaker_info = f"""
【話者情報】
- 求職者名: {candidate_name} (注意: Google Meetでの表示名のため、議事録内では異なる名前で表記されている可能性があります)
- 基本的にエージェント以外の発言は求職者によるものです
"""
        elif agent_name:
            speaker_info = f"""
【話者情報】  
- エージェント名: {agent_name} (注意: 議事録内では異なる名前で表記されている可能性があります)
- エージェントの発言は、主催者({agent_name})の発言として識別してください
- 基本的にエージェント以外の発言は求職者によるものです
"""

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

        for attempt in range(max_retries):
            try:
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config={
                        "response_mime_type": "application/json",
                        "response_schema": schema,
                        "temperature": self.temperature,
                        "max_output_tokens": self.max_tokens,
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
        self, text_content: str, candidate_name: str | None = None, 
        agent_name: str | None = None, use_parallel: bool = True
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
            extract_func = partial(self._extract_group_wrapper, text_content, candidate_name, agent_name)
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
                    self.extract_structured_data_group(text_content, schema, group_name, candidate_name, agent_name)
                )
        return combined_result

    def _extract_group_wrapper(
        self, text_content: str, candidate_name: str | None, agent_name: str | None, 
        schema: Dict[str, Any], group_name: str
    ) -> Dict[str, Any]:
        return self.extract_structured_data_group(text_content, schema, group_name, candidate_name, agent_name)
