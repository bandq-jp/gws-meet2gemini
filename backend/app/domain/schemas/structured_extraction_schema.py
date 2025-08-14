"""
構造化データ抽出用のスキーマ定義

DDD/オニオンアーキテクチャに従い、ビジネスロジックに関わる
スキーマ定義をドメイン層に配置。
技術的な実装詳細からビジネスルールを分離し、
再利用性と保守性を向上させる。
"""
from __future__ import annotations
from typing import Dict, Any, List


class StructuredExtractionSchema:
    """構造化データ抽出用のスキーマ定義クラス
    
    議事録から抽出するべき構造化データの定義を管理する。
    6つのグループに分けて大きなスキーマを扱いやすくしている。
    """

    @staticmethod
    def get_group1_schema() -> Dict[str, Any]:
        """グループ1: 転職活動状況・エージェント関連"""
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

    @staticmethod
    def get_group2_schema() -> Dict[str, Any]:
        """グループ2: 転職理由・希望時期・メモ・転職軸"""
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

    @staticmethod
    def get_group3_schema() -> Dict[str, Any]:
        """グループ3: 職歴・経験（自由記述系）"""
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

    @staticmethod
    def get_group4_schema() -> Dict[str, Any]:
        """グループ4: 業界・職種（選択肢拡張）"""
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

    @staticmethod
    def get_group5_schema() -> Dict[str, Any]:
        """グループ5: 年収・待遇・働き方"""
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

    @staticmethod
    def get_group6_schema() -> Dict[str, Any]:
        """グループ6: 会社カルチャー・規模・キャリア"""
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

    @classmethod
    def get_all_schema_groups(cls) -> List[tuple[Dict[str, Any], str]]:
        """すべてのスキーマグループを取得する
        
        Returns:
            List[tuple]: (スキーマ, グループ名)のタプルリスト
        """
        return [
            (cls.get_group1_schema(), "転職活動状況・エージェント関連"),
            (cls.get_group2_schema(), "転職理由・希望条件"),
            (cls.get_group3_schema(), "職歴・経験"),
            (cls.get_group4_schema(), "希望業界・職種"),
            (cls.get_group5_schema(), "年収・待遇条件"),
            (cls.get_group6_schema(), "企業文化・キャリアビジョン"),
        ]