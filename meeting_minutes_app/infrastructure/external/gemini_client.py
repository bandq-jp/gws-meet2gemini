import json
import time
import asyncio
from typing import Dict, Any, List, Tuple
from concurrent.futures import ThreadPoolExecutor
from functools import partial

from google import genai
from ..config.settings import settings


class GeminiClient:
    """Gemini API クライアント（構造化データ抽出用）"""
    
    def __init__(self):
        self._client = None
        self._executor = ThreadPoolExecutor(max_workers=settings.max_workers)
        self._init_client()
    
    def _init_client(self):
        """Gemini クライアントを初期化"""
        api_key = settings.get_gemini_api_key()
        self._client = genai.Client(api_key=api_key)
    
    async def extract_structured_data(self, text_content: str) -> Dict[str, Any]:
        """
        テキストから構造化データを抽出（分割処理・並列実行）
        
        Args:
            text_content: 抽出対象のテキスト
            
        Returns:
            抽出された構造化データ
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._executor,
            self._extract_all_structured_data_sync,
            text_content,
            True  # 並列処理を使用
        )
    
    def _extract_all_structured_data_sync(
        self, 
        text_content: str, 
        use_parallel: bool = True
    ) -> Dict[str, Any]:
        """全スキーマグループでの構造化データ抽出（並列処理対応）"""
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
            
            with ThreadPoolExecutor(max_workers=3) as executor:
                # 全グループを並列で処理
                future_to_group = {}
                for schema, group_name in schema_groups:
                    future = executor.submit(extract_func, schema, group_name)
                    future_to_group[future] = group_name
                
                # 結果を収集
                for future in future_to_group:
                    group_name = future_to_group[future]
                    try:
                        group_result = future.result()
                        combined_result.update(group_result)
                    except Exception as e:
                        print(f"{group_name}の並列処理エラー: {e}")
        else:
            # 順次処理で実行
            for schema, group_name in schema_groups:
                group_result = self._extract_structured_data_group(
                    text_content, schema, group_name
                )
                combined_result.update(group_result)
        
        return combined_result
    
    def _extract_group_wrapper(
        self, 
        text_content: str, 
        schema: Dict[str, Any], 
        group_name: str
    ) -> Dict[str, Any]:
        """並列処理用のラッパー関数"""
        return self._extract_structured_data_group(text_content, schema, group_name)
    
    def _extract_structured_data_group(
        self, 
        text_content: str, 
        schema: Dict[str, Any], 
        group_name: str, 
        max_retries: int = None
    ) -> Dict[str, Any]:
        """指定されたスキーマグループでの構造化データ抽出（リトライ機能付き）"""
        
        if max_retries is None:
            max_retries = settings.max_retries
        
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
                response = self._client.models.generate_content(
                    model=settings.gemini_model,
                    contents=prompt,
                    config={
                        "response_mime_type": "application/json",
                        "response_schema": schema,
                        "temperature": settings.gemini_temperature,
                        "max_output_tokens": settings.gemini_max_output_tokens
                    }
                )
                
                if response and response.text:
                    return json.loads(response.text)
                else:
                    print(f"{group_name}: レスポンスが空です (試行 {attempt + 1}/{max_retries})")
                    if attempt < max_retries - 1:
                        time.sleep(settings.retry_delay_seconds)
                        continue
                
            except json.JSONDecodeError as e:
                print(f"{group_name}: JSON解析エラー (試行 {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(settings.retry_delay_seconds)
                    continue
                    
            except Exception as e:
                print(f"{group_name}: API呼び出しエラー (試行 {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(settings.retry_delay_seconds * 2)  # エラー時は少し長めに待機
                    continue
        
        print(f"{group_name}: 全ての試行が失敗しました")
        return {}
    
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
        """希望業界・職種のスキーマ"""
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
    
    def __del__(self):
        """デストラクタ：ExecutorPoolを適切にシャットダウン"""
        if hasattr(self, '_executor'):
            self._executor.shutdown(wait=False)