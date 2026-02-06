/**
 * Agent Showcase - Static Data
 *
 * 11 sub-agents with tool definitions, descriptions, and UI metadata.
 * Tool counts and names sourced from backend agent/tool files.
 */

import type { LucideIcon } from "lucide-react";
import {
  BarChart3,
  TrendingUp,
  Megaphone,
  FileText,
  Users,
  Brain,
  Database,
  Globe,
  Code2,
  Mail,
  Search,
  Calendar,
} from "lucide-react";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type AgentCategory = "marketing" | "crm" | "support" | "utility";

export type AgentToolInfo = {
  name: string;
  label: string;
};

export type AgentTier = {
  name: string;
  tools: AgentToolInfo[];
};

export type AgentInfo = {
  id: string;
  displayName: string;
  tagline: string;
  description: string;
  icon: LucideIcon;
  category: AgentCategory;
  services: string[];
  toolCount: number;
  isMcp?: boolean;
  tiers?: AgentTier[];
  tools: AgentToolInfo[];
  highlights: string[];
  exampleQuery: string;
};

export const AGENT_CATEGORIES: Record<
  AgentCategory,
  { label: string; description: string }
> = {
  marketing: {
    label: "マーケティング",
    description: "GA4・SEO・広告・WordPress",
  },
  crm: { label: "CRM・採用", description: "Zoho CRM・候補者分析" },
  support: { label: "CA支援", description: "企業DB・統合支援" },
  utility: {
    label: "ユーティリティ",
    description: "検索・コード実行・Workspace",
  },
};

// ---------------------------------------------------------------------------
// Agent Definitions
// ---------------------------------------------------------------------------

export const AGENTS: AgentInfo[] = [
  // ── Marketing ──────────────────────────────────────────────────────────
  {
    id: "analytics",
    displayName: "Analytics",
    tagline: "GA4 + Search Console",
    description:
      "Google Analytics 4とSearch Consoleのデータを横断分析。トラフィック推移、検索クエリ、ページパフォーマンス、URLインデックス状況まで包括的にカバー。",
    icon: BarChart3,
    category: "marketing",
    services: ["Google Analytics 4", "Search Console"],
    toolCount: 12,
    isMcp: true,
    tools: [],
    tiers: [
      {
        name: "GA4",
        tools: [
          { name: "run_report", label: "カスタムレポート取得" },
          { name: "run_realtime_report", label: "リアルタイムデータ取得" },
          { name: "get_account_summaries", label: "アカウント概要" },
          { name: "get_property_details", label: "プロパティ詳細" },
          { name: "get_custom_dimensions", label: "カスタムディメンション" },
          { name: "list_google_ads_links", label: "Google Ads連携" },
        ],
      },
      {
        name: "Search Console",
        tools: [
          { name: "get_search_analytics", label: "検索パフォーマンス分析" },
          { name: "get_performance_overview", label: "サマリー＋日次トレンド" },
          { name: "compare_search_periods", label: "2期間比較" },
          { name: "get_search_by_page_query", label: "ページ別クエリ分析" },
          { name: "inspect_url_enhanced", label: "URLインデックス検査" },
          { name: "batch_url_inspection", label: "一括URL検査" },
        ],
      },
    ],
    highlights: [
      "セッション・PV・直帰率のトレンド分析",
      "検索クエリ×ページの掛け合わせ分析",
      "URLインデックス状況の一括チェック",
    ],
    exampleQuery: "今週のGA4セッション数と前週比を分析して",
  },
  {
    id: "seo",
    displayName: "SEO",
    tagline: "Ahrefs",
    description:
      "Ahrefsのデータを活用したSEO分析。ドメインレーティング、被リンク、オーガニックキーワード、競合サイト比較、コンテンツギャップの発見まで対応。",
    icon: TrendingUp,
    category: "marketing",
    services: ["Ahrefs"],
    toolCount: 20,
    isMcp: true,
    tools: [
      { name: "domain_rating", label: "ドメインレーティング取得" },
      { name: "site_metrics", label: "サイト指標取得" },
      { name: "organic_keywords", label: "オーガニックキーワード調査" },
      { name: "top_pages", label: "トップページ分析" },
      { name: "pages_by_traffic", label: "トラフィック順ページ" },
      { name: "organic_competitors", label: "競合ドメイン分析" },
      { name: "backlinks_stats", label: "被リンク統計" },
      { name: "refdomains", label: "参照ドメイン分析" },
      { name: "all_backlinks", label: "全被リンク一覧" },
      { name: "anchors", label: "アンカーテキスト分析" },
      { name: "keywords_overview", label: "キーワード概要" },
      { name: "related_terms", label: "関連キーワード" },
      { name: "matching_terms", label: "マッチングキーワード" },
      { name: "volume_history", label: "検索ボリューム推移" },
      { name: "search_suggestions", label: "サジェストキーワード" },
      { name: "site_audit_issues", label: "サイト監査の課題" },
      { name: "page_explorer", label: "ページエクスプローラー" },
      { name: "rank_tracker", label: "ランキング追跡" },
      { name: "batch_analysis", label: "バッチ分析" },
      { name: "usage_limits", label: "API使用量確認" },
    ],
    highlights: [
      "ドメインレーティングと被リンク分析",
      "キーワードボリュームと競合度の調査",
      "サイト監査で技術的SEO課題を特定",
    ],
    exampleQuery:
      "hitocareer.comのドメインレーティングと競合サイトを比較して",
  },
  {
    id: "adplatform",
    displayName: "Meta Ads",
    tagline: "Facebook / Instagram 広告",
    description:
      "Meta広告（Facebook・Instagram）のキャンペーン分析。CTR・CPM・CPA・ROASの分析、インタレストターゲティング調査、オーディエンスサイズ推定が可能。",
    icon: Megaphone,
    category: "marketing",
    services: ["Meta Ads"],
    toolCount: 20,
    isMcp: true,
    tools: [
      { name: "get_ad_accounts", label: "広告アカウント一覧" },
      { name: "get_account_info", label: "アカウント情報" },
      { name: "get_campaigns", label: "キャンペーン一覧" },
      { name: "get_campaign_details", label: "キャンペーン詳細" },
      { name: "get_adsets", label: "広告セット一覧" },
      { name: "get_adset_details", label: "広告セット詳細" },
      { name: "get_ads", label: "広告一覧" },
      { name: "get_ad_details", label: "広告詳細" },
      { name: "get_ad_creatives", label: "クリエイティブ取得" },
      { name: "get_ad_image", label: "広告画像取得" },
      { name: "get_insights", label: "パフォーマンス指標" },
      { name: "search_interests", label: "インタレスト検索" },
      { name: "get_interest_suggestions", label: "インタレスト提案" },
      { name: "estimate_audience_size", label: "オーディエンスサイズ推定" },
      { name: "validate_interests", label: "インタレスト検証" },
      { name: "search_behaviors", label: "ビヘイビア検索" },
      { name: "search_demographics", label: "デモグラフィック検索" },
      { name: "search_geo_locations", label: "地域ターゲティング" },
      { name: "get_account_pages", label: "連携ページ一覧" },
      { name: "search_pages", label: "ページ検索" },
    ],
    highlights: [
      "キャンペーン・広告セットのROAS分析",
      "インタレスト×デモグラの掛け合わせ調査",
      "オーディエンスサイズ推定でリーチ予測",
    ],
    exampleQuery: "Meta広告のキャンペーン別CPAとROASを比較して",
  },
  {
    id: "wordpress",
    displayName: "WordPress",
    tagline: "hitocareer / achievehr",
    description:
      "WordPressサイトの記事管理・分析。記事一覧の取得、ブロック構造分析、SEO要件チェック、記事のドラフト作成・編集・公開まで対応。2サイト同時管理。",
    icon: FileText,
    category: "marketing",
    services: ["hitocareer.com", "achievehr.jp"],
    toolCount: 25,
    isMcp: true,
    tools: [
      { name: "get_posts_by_category", label: "カテゴリ別記事取得" },
      { name: "get_post_raw_content", label: "記事コンテンツ取得" },
      { name: "get_post_block_structure", label: "ブロック構造分析" },
      { name: "analyze_format_patterns", label: "フォーマット分析" },
      { name: "extract_used_blocks", label: "使用ブロック抽出" },
      { name: "get_theme_styles", label: "テーマスタイル取得" },
      { name: "get_block_patterns", label: "ブロックパターン取得" },
      { name: "get_reusable_blocks", label: "再利用ブロック" },
      { name: "get_article_regulations", label: "記事レギュレーション" },
      { name: "create_draft_post", label: "ドラフト記事作成" },
      { name: "update_post_content", label: "記事コンテンツ更新" },
      { name: "update_post_meta", label: "メタ情報更新" },
      { name: "publish_post", label: "記事公開" },
      { name: "delete_post", label: "記事削除" },
      { name: "validate_block_content", label: "ブロック検証" },
      { name: "check_regulation", label: "レギュレーションチェック" },
      { name: "check_seo_requirements", label: "SEO要件チェック" },
      { name: "get_media_library", label: "メディアライブラリ" },
      { name: "upload_media", label: "メディアアップロード" },
      { name: "set_featured_image", label: "アイキャッチ設定" },
      { name: "get_categories", label: "カテゴリ一覧" },
      { name: "get_tags", label: "タグ一覧" },
      { name: "create_term", label: "タクソノミー作成" },
      { name: "get_site_info", label: "サイト情報" },
      { name: "get_post_types", label: "投稿タイプ一覧" },
    ],
    highlights: [
      "2サイト同時の記事管理・編集",
      "ブロックエディタ構造の分析・検証",
      "SEOレギュレーション自動チェック",
    ],
    exampleQuery:
      "hitocareerの最新記事5件のSEO要件チェック結果を教えて",
  },

  // ── CRM・採用 ──────────────────────────────────────────────────────────
  {
    id: "zohocrm",
    displayName: "Zoho CRM",
    tagline: "全58モジュール動的アクセス",
    description:
      "Zoho CRM全モジュールに動的アクセス。スキーマ探索からCOQLクエリ、チャネル別ファネル分析、担当者パフォーマンス比較まで、3層アーキテクチャで柔軟に対応。",
    icon: Users,
    category: "crm",
    services: ["Zoho CRM"],
    toolCount: 12,
    tools: [],
    tiers: [
      {
        name: "メタデータ発見",
        tools: [
          { name: "list_crm_modules", label: "CRMモジュール一覧" },
          { name: "get_module_schema", label: "フィールド構造取得" },
          { name: "get_module_layout", label: "レイアウト取得" },
        ],
      },
      {
        name: "汎用クエリ",
        tools: [
          { name: "query_crm_records", label: "COQLレコード検索" },
          { name: "aggregate_crm_data", label: "GROUP BY集計" },
          { name: "get_record_detail", label: "全フィールド取得" },
          { name: "get_related_records", label: "関連リスト取得" },
        ],
      },
      {
        name: "専門分析",
        tools: [
          { name: "analyze_funnel_by_channel", label: "チャネル別ファネル" },
          { name: "trend_analysis_by_period", label: "月次/週次トレンド" },
          { name: "compare_channels", label: "チャネル比較" },
          { name: "get_pic_performance", label: "担当者ランキング" },
          { name: "get_conversion_metrics", label: "全チャネルKPI" },
        ],
      },
    ],
    highlights: [
      "全58モジュールのスキーマを自律探索",
      "COQLクエリで任意の検索・集計",
      "ファネル分析でボトルネック自動特定",
    ],
    exampleQuery: "直近3ヶ月のチャネル別CVRファネルを分析して",
  },
  {
    id: "candidate_insight",
    displayName: "Candidate Insight",
    tagline: "候補者リスク・緊急度分析",
    description:
      "候補者の競合リスク分析、緊急度スコアリング、転職パターン可視化。Zoho CRMと議事録構造化データを統合した高度なインサイト生成。",
    icon: Brain,
    category: "crm",
    services: ["Zoho CRM", "構造化データ"],
    toolCount: 5,
    tools: [
      { name: "analyze_competitor_risk", label: "競合エージェントリスク分析" },
      { name: "assess_candidate_urgency", label: "緊急度スコアリング" },
      { name: "analyze_transfer_patterns", label: "転職パターン可視化" },
      { name: "generate_candidate_briefing", label: "面談ブリーフィング生成" },
      { name: "get_candidate_summary", label: "候補者サマリー一括取得" },
    ],
    highlights: [
      "他社オファー状況から競合リスクを特定",
      "転職理由と希望時期で緊急度を自動算出",
      "面談準備ブリーフィングをワンクリック生成",
    ],
    exampleQuery: "候補者の田中さんの競合リスクと緊急度を分析して",
  },

  // ── CA支援 ─────────────────────────────────────────────────────────────
  {
    id: "company_db",
    displayName: "企業DB",
    tagline: "セマンティック検索 + 325社マスタ",
    description:
      "企業情報のベクトル検索・厳密検索・マッチング。候補者の転職理由から最適企業を自動推薦。訴求ポイント生成やメールからの非公開情報補完にも対応。",
    icon: Database,
    category: "support",
    services: ["企業マスタDB", "pgvector", "Gmail"],
    toolCount: 14,
    tools: [],
    tiers: [
      {
        name: "セマンティック検索",
        tools: [
          { name: "semantic_search_companies", label: "自然言語で企業検索" },
          {
            name: "find_companies_for_candidate",
            label: "転職理由→最適企業マッチ",
          },
        ],
      },
      {
        name: "厳密検索",
        tools: [
          { name: "search_companies", label: "条件フィルタ検索" },
          { name: "get_company_detail", label: "企業詳細取得" },
          { name: "get_company_requirements", label: "採用要件取得" },
          { name: "get_appeal_by_need", label: "ニーズ別訴求ポイント" },
          { name: "match_candidate_to_companies", label: "スコアリングマッチ" },
          { name: "get_pic_recommended", label: "担当者別推奨企業" },
          { name: "compare_companies", label: "2-5社の並列比較表" },
          { name: "get_company_definitions", label: "マスタ定義一覧" },
        ],
      },
      {
        name: "メール補完",
        tools: [
          { name: "search_gmail", label: "企業関連メール検索" },
          { name: "get_email_detail", label: "メール本文取得" },
          { name: "get_email_thread", label: "スレッド全体追跡" },
          { name: "get_recent_emails", label: "直近メール一覧" },
        ],
      },
    ],
    highlights: [
      "ベクトル検索で「ワークライフバランス重視」等の曖昧な要望にも対応",
      "325社のマスタDBから条件マッチ・比較表を即座に生成",
      "Gmailから非公開の採用担当やり取り情報を補完",
    ],
    exampleQuery:
      "ワークライフバランスを重視する30代エンジニアに合う企業を探して",
  },
  {
    id: "ca_support",
    displayName: "CA支援",
    tagline: "クロスドメイン統合分析",
    description:
      "CRM・議事録・企業DB・Gmail・セマンティック検索を統合した、キャリアアドバイザー業務の包括支援エージェント。面談準備から企業提案まで一気通貫。",
    icon: Users,
    category: "support",
    services: ["Zoho CRM", "議事録", "企業DB", "Gmail", "pgvector"],
    toolCount: 35,
    tools: [
      { name: "query_crm_records", label: "CRMレコード検索" },
      { name: "get_record_detail", label: "レコード詳細" },
      { name: "analyze_funnel", label: "ファネル分析" },
      { name: "get_candidate_summary", label: "候補者サマリー" },
      { name: "analyze_competitor_risk", label: "競合リスク分析" },
      { name: "search_meetings", label: "議事録検索" },
      { name: "get_meeting_transcript", label: "議事録本文" },
      { name: "get_candidate_full_profile", label: "統合プロファイル" },
      { name: "semantic_search", label: "セマンティック企業検索" },
      { name: "find_companies", label: "最適企業マッチング" },
      { name: "compare_companies", label: "企業比較表" },
      { name: "search_gmail", label: "メール検索" },
    ],
    highlights: [
      "候補者1名に対するCRM+議事録+企業DBの統合分析",
      "面談準備資料をワンクエリで自動生成",
      "全35ツールで提案〜リスク分析まで一気通貫",
    ],
    exampleQuery:
      "田中太郎さんの面談準備資料を作って。CRM情報と議事録、合いそうな企業も含めて",
  },

  // ── ユーティリティ ──────────────────────────────────────────────────────
  {
    id: "google_search",
    displayName: "Google検索",
    tagline: "リアルタイムWeb情報",
    description:
      "Google検索でリアルタイムのWeb情報を取得。最新ニュース、業界動向、競合情報、事実確認に活用。他エージェントの分析結果を補完する調査ツール。",
    icon: Globe,
    category: "utility",
    services: ["Google Search"],
    toolCount: 1,
    tools: [{ name: "google_search", label: "Google検索" }],
    highlights: [
      "最新の業界ニュースやトレンドを即座に取得",
      "競合企業の最新動向を調査",
      "他エージェントの分析を外部情報で裏付け",
    ],
    exampleQuery: "人材紹介業界の2026年最新トレンドを調べて",
  },
  {
    id: "code_execution",
    displayName: "コード実行",
    tagline: "Python サンドボックス",
    description:
      "Pythonコードを安全なサンドボックス環境で実行。統計計算、データ変換、CSV加工、数式処理など、他エージェントの分析結果をさらに深掘り。",
    icon: Code2,
    category: "utility",
    services: ["Python Sandbox"],
    toolCount: 1,
    tools: [{ name: "code_executor", label: "Pythonコード実行" }],
    highlights: [
      "統計分析・回帰分析・仮説検定をその場で実行",
      "CSVデータのクレンジング・変換処理",
      "複雑な数値計算やシミュレーション",
    ],
    exampleQuery:
      "GA4の月次セッションデータから成長率の線形回帰を計算して",
  },
  {
    id: "workspace",
    displayName: "Workspace",
    tagline: "Gmail + Google Calendar",
    description:
      "ユーザーのGmailとGoogleカレンダーに読み取りアクセス。メール検索・閲覧、今日の予定確認、期間指定のイベント一覧、会議リンクの取得などに対応。",
    icon: Mail,
    category: "utility",
    services: ["Gmail", "Google Calendar"],
    toolCount: 8,
    tools: [],
    tiers: [
      {
        name: "Gmail",
        tools: [
          { name: "search_gmail", label: "メール検索" },
          { name: "get_email_detail", label: "メール本文取得" },
          { name: "get_email_thread", label: "スレッド全体表示" },
          { name: "get_recent_emails", label: "直近メール一覧" },
        ],
      },
      {
        name: "Calendar",
        tools: [
          { name: "get_today_events", label: "今日の予定" },
          { name: "list_calendar_events", label: "期間指定イベント一覧" },
          { name: "search_calendar_events", label: "イベント検索" },
          { name: "get_event_detail", label: "イベント詳細" },
        ],
      },
    ],
    highlights: [
      "Gmail検索構文（from:, subject:, newer_than:）フルサポート",
      "今日の予定をワンクエリで確認",
      "会議リンク・参加者情報の即座取得",
    ],
    exampleQuery: "今日の予定と、未読の重要メールを教えて",
  },
];
