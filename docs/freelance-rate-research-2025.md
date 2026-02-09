# フリーランス業務委託 時給相場調査レポート（2025-2026年）

> **調査日**: 2026-02-09
> **調査方法**: 4つの専門AIエージェント（Opus x1, Sonnet x3）による並列Web調査
> **調査対象**: 日本のフリーランス・業務委託・準委任エンジニア市場
> **対象スキルセット**: フルスタック（Python FastAPI + Next.js/React/TS + AI/LLM + GCP + 外部API統合）

---

## 目次

1. [コードベースの実測規模](#1-コードベースの実測規模)
2. [技術レベル判定](#2-技術レベル判定)
3. [日本市場の一般的なフリーランス相場](#3-日本市場の一般的なフリーランス相場)
4. [技術スキル別の単価相場](#4-技術スキル別の単価相場)
5. [AI/LLMエンジニア特化の相場](#5-aillmエンジニア特化の相場)
6. [海外市場との比較](#6-海外市場との比較)
7. [正社員年収との比較](#7-正社員年収との比較)
8. [契約形態による相場差](#8-契約形態による相場差)
9. [フリーランスエージェント経由の単価とマージン](#9-フリーランスエージェント経由の単価とマージン)
10. [本案件スキルセットの希少性評価](#10-本案件スキルセットの希少性評価)
11. [結論: 妥当な時給レンジ](#11-結論-妥当な時給レンジ)
12. [情報ソース一覧](#12-情報ソース一覧)

---

## 1. コードベースの実測規模

b&q Hub（一人開発のAIプラットフォーム）の実測値:

| 区分 | ファイル数 | 行数 |
|------|-----------|------|
| Backend (Python/FastAPI) | 142 | 33,578 |
| Frontend (Next.js/React/TS) | 115 | 24,419 |
| SQL Migration | 22 | 1,135 |
| **合計** | **279** | **約59,000行** |

- 外部API統合: **15+サービス**（Zoho CRM, Google Drive/Gmail/Calendar, Slack, Meta Ads, GA4, GSC, Supabase, OpenAI, Gemini, Phoenix/OTel, Ahrefs, WordPress MCP等）
- ADK関連だけで約11,500行
- 開発期間: 約6ヶ月（2025年8月〜2026年2月）
- コミット数: 363

### 主要機能（全て一人で実装）
- 10+サブエージェントのマルチエージェントオーケストレーション（Google ADK）
- セマンティック検索（pgvector + Gemini embedding）
- MCP (Model Context Protocol) サーバー統合管理
- ADKイベント→SSE→フロントエンドの完全なリアルタイムストリーミング
- カスタムプラグインシステム（SubAgentStreaming, MCPResponseOptimizer）
- Gemini Context Caching（入力トークン90%コスト削減）
- OTel + Phoenix テレメトリ計装
- W3C Web Annotation Data Model準拠のフィードバック・アノテーションシステム
- マルチモーダル対応（ファイルアップロード、広告画像分析）
- Zoho CRM 58モジュール動的アクセス（COQL）

---

## 2. 技術レベル判定

**判定: シニアエンジニア上位〜リードエンジニア相当**

通常のチーム構成なら **4〜5名で3〜4ヶ月** の開発規模。

### 高評価ポイント
- ADKのSDK内部実装を解析した上での独自ワークアラウンド
- 10+外部サービス統合を一人で完遂した実行力
- コスト最適化の定量成果（Context Cache 90%削減、MCPレスポンス圧縮60-70%削減）
- ドメイン知識（人材紹介業）とエンジニアリングの融合

### 割引評価ポイント（客観的弱点）
- 自動テスト（pytest等）が確認できない
- CI/CDパイプラインの記述が不明
- 一人開発のためコードレビュープロセスがない（バス係数=1）
- AI支援コーディング（Claude Code）への依存度が高い
- チーム開発・マネジメント実績が見えない

---

## 3. 日本市場の一般的なフリーランス相場

### 時給相場（全体）
- **平均時給**: 4,000〜5,000円
- **一般的な範囲**: 2,000〜6,000円
- **高単価帯**: 6,000円以上

### 月額単価（全体平均）
- **全体平均**: 月額76〜78万円
- **経験年数別**:
  - 未経験〜1年未満: 月30万円
  - 中堅レベル: 月60〜100万円
  - 高スキル・豊富な経験: 月100万円以上

### 職種別の月額単価

| 職種 | 月額単価相場 |
|------|------------|
| プロジェクトマネージャー（PM）/ ITアーキテクト | 80〜150万円 |
| システムコンサルタント | 100〜200万円 |
| Webエンジニア / アプリケーションエンジニア | 60〜100万円 |
| テストエンジニア / プログラマー | 30〜60万円 |
| システムエンジニア（SE） | 50〜80万円 |
| PM・PMO人材 | 60〜90万円 |

**情報ソース**:
- [レバテック - フリーランスの時給相場を解説](https://levtech.jp/partner/guide/article/detail/389/)
- [techbiz - フリーランスエンジニアの単価相場と年収実態（2025年最新版）](https://techbiz.com/media/column/money2)
- [ジンジブ - フリーランスエンジニアの平均年収（2025年最新版）](https://jinjib.co.jp/job-change/freelance-se-average-salary)
- [セルプロゲート - フリーランスエンジニアの単価相場まとめ](https://freelance.cellpromote.biz/free_lance_engineer_unit_price/)
- [エン・フリーランススタート定点調査レポート（2025年10月度）](https://corp.en-japan.com/newsrelease/2025/43645.html)

---

## 4. 技術スキル別の単価相場

### 4-1. Python（FastAPI）バックエンド開発

| 指標 | 金額 |
|------|------|
| 月額平均（直近10ヶ月） | 80万円前後 |
| FastAPI + Flask/Django | 月60〜75万円 |
| API設計 + インフラ構築込み | 月80万円以上 |
| エージェント別最高値 | 月90〜112万円 |

**情報ソース**:
- [フリーランススタート - Pythonフリーランスの単価・案件動向（2025年版）](https://freelance-start.com/articles/1165)
- [テクフリ - Pythonフリーランスの単価相場・案件例（2025年版）](https://freelance.techcareer.jp/articles/wp/skills/python/detail/25038/)
- [SOKUDAN - Pythonエンジニア平均年収、案件数（2025年）](https://magazine.sokudan.work/post/XQ-H13PI)
- [フリーランスHub - Python × バックエンドエンジニアの案件](https://freelance-hub.jp/project/cross/227/)
- [FLEXY - Pythonエンジニアの年収が高い理由](https://flxy.jp/media/article/23447)

### 4-2. Next.js / React / TypeScript フロントエンド

| 指標 | 金額 |
|------|------|
| Next.js 月額平均（2025年10月度） | 93.9万円 |
| WorkX | 114.1万円 |
| Findy Freelance | 107.7万円 |
| React 平均 | 77.9万円 |
| JavaScript全般 | 平均60〜71.5万円 |

**情報ソース**:
- [BIGDATA NAVI - Next.jsスキルでフリーランスになるには？](https://www.bigdata-navi.com/aidrops/7892/)
- [エン - 2025年10月度フリーランスエンジニア月額平均単価78.3万円](https://corp.en-japan.com/newsrelease/2025/43645.html)
- [テクフリ - JavaScriptフリーランスの単価相場（2025年版）](https://freelance.techcareer.jp/articles/wp/detail/25046/)
- [SOKUDAN - Next.jsエンジニア平均年収、案件数（2025年）](https://magazine.sokudan.work/post/xR7pkALH)

### 4-3. Google Cloud（Cloud Run、Cloud Tasks）

| 指標 | 金額 |
|------|------|
| GCPエンジニア月額平均 | 80〜100万円 |
| 平均年収 | 900〜1,200万円 |

**情報ソース**:
- [フリーランススタート - インフラエンジニア案件の単価相場と市場動向](https://freelance-start.com/articles/67)
- [BIGDATA NAVI - GCPエンジニアのフリーランス求人案件](https://www.bigdata-navi.com/special/13813/)
- [フリーランススタート - Google Cloud Platformのフリーランス案件](https://freelance-start.com/jobs/skill-236)
- [ProConsul - GCPエンジニアが稼げるフリーランス案件](https://freeconsul.co.jp/cs/freelance-gcp-engineer/)

### 4-4. フルスタックエンジニア

| 指標 | 金額 |
|------|------|
| 月額単価相場 | 80〜120万円 |
| 平均月収 | 82.1万円 |
| 平均年収 | 985.2万円 |
| Freelance Port | 105.5万円 |
| Findy Freelance | 96.5万円 |
| 高単価ケース | 月150万円以上 |

**情報ソース**:
- [ITプロマガジン - フリーランスエンジニアの単価相場は？](https://itpropartners.com/blog/449/)
- [リラコム - フルスタックエンジニアは年収1000万円を超える？（2025年最新）](https://comm.relance.jp/blog/fullstack-engineer-salary-roadmap/)
- [フリーランスHub - フルスタックエンジニアのフリーランス案件](https://freelance-hub.jp/project/job/73/)
- [FLEXY - フルスタックエンジニアとは？年収相場](https://flxy.jp/media/article/28612)

---

## 5. AI/LLMエンジニア特化の相場

### AIエンジニア全般

| 指標 | 金額 |
|------|------|
| 月額平均 | 85.3万円 |
| 中央値 | 80万円 |
| 一般相場（週5常駐） | 70〜90万円 |
| 最高単価 | 285万円 |
| Webエンジニアとの差 | **+20〜50%** |

### LLM/生成AI開発

| 指標 | 金額 |
|------|------|
| 月額単価 | 70〜150万円 |
| 高度人材 | 月額150万円超 |
| プロンプトエンジニア平均 | 月93万円 |
| プロンプトエンジニア時給 | 5,000〜15,000円 |

### 経験レベル別（プロンプトエンジニア）

| レベル | 年収 |
|--------|------|
| エントリー（0-2年） | 500〜700万円 |
| ミドル（3-5年） | 700〜1,000万円 |
| シニア（5年以上） | 1,000〜1,600万円 |
| リード（チーム統括） | 1,400〜2,000万円 |

### Google ADK/LangChain等の経験者プレミアム
- 一般AI開発者に対して **+30〜50%の単価上乗せ**
- 実務経験者は国内推定3,000〜4,000名のみ（経済産業省2024年調査）

**情報ソース**:
- [フリーランススタート - AIエンジニアのフリーランス案件（2025年最新）](https://freelance-start.com/articles/1215)
- [FLEXY - AIエンジニアの平均年収は？](https://flxy.jp/media/article/28622)
- [KOTORA JOURNAL - AIエンジニアの案件単価徹底解説](https://www.kotora.jp/c/57482/)
- [Relance - フリーランスAIエンジニアは稼げるの？](https://relance.jp/blog/ai-engineer-earn-money/)
- [プロンプターズ求人 - プロンプトエンジニアの報酬実態2025](https://kyuujin.prompters.jp/career-guide/prompt-engineer-salary/)
- [レバテックフリーランス - AIエンジニア単価相場](https://freelance.levtech.jp/guide/detail/875/)
- [BIGDATA NAVI - LangChain副業案件](https://www.bigdata-navi.com/aidrops/9957/)
- [セルプロゲート - AIエンジニアのフリーランス案件・単価相場・年収](https://cellpromote.biz/column/ai-engineer-free-lance/)
- [BIGDATA NAVI - 機械学習エンジニア案件の単価は高い？](https://www.bigdata-navi.com/aidrops/7423/)
- [生成AI総合研究所 - AIエンジニア向けフリーランス案件サイト（2026年版）](https://www.generativeai.tokyo/media/ai_engineer_freelance_sites/)
- [ContactEARTH for Expert - AI案件とは？案件単価や高単価案件獲得のコツ](https://dx-consultant.co.jp/ai-engineer-matter/)

---

## 6. 海外市場との比較

### 米国市場

| レベル | 時給（USD） | 時給（JPY換算） |
|--------|-----------|----------------|
| Junior（0-2年） | $50-80 | 7,500〜12,000円 |
| Mid-level（2-5年） | $80-120 | 12,000〜18,000円 |
| Senior（5-10年） | $120-200 | 18,000〜30,000円 |
| Staff/Principal（10年+） | $200-300+ | 30,000〜45,000円+ |
| LLM専門家 | $150-250 | 22,500〜37,500円 |

### プラットフォーム別
- **Upwork** ML Engineer中央値: $100/h
- **Toptal**: $60-150/h（上位3%のみ）

### 欧州市場
- **西欧（英独仏）**: $70-150/h
- **東欧**: $40-90/h

### 日本 vs 海外の単価比率

| レベル | 日本（時給換算） | 米国 | 日本/米国比 |
|--------|----------------|------|-----------|
| 一般AI/ML | $35-42 | $80-120 | **35-40%** |
| Senior | $50-63 | $120-200 | **40-45%** |
| LLM専門家 | $70-80 | $150-250 | **45-50%** |

**結論**: 日本のAI/LLMエンジニア単価は米国の約35〜50%、西欧の約50〜60%。

### 市場トレンド
- 2024年初頭→2025年で **15-20%のレート上昇**
- AI/ML開発者は一般ソフトウェア開発者に対して **40-60%のプレミアム**
- LLM専門家はさらに **+30-50%の追加プレミアム**

**情報ソース**:
- [Upwork - Machine Learning Engineer Hourly Rates](https://www.upwork.com/hire/machine-learning-experts/cost/)
- [Index.dev - Freelance Developer Rates 2025: Web, Software & AI Engineer Hourly Rates by Country](https://www.index.dev/blog/freelance-developer-rates-by-country)
- [Index.dev - LLM Developer Hourly Rates in 2025: CEE, LATAM & Asia](https://www.index.dev/blog/llm-developer-hourly-rates)
- [Jobbers - Best Platforms to Hire AI/ML Freelancers in 2026](https://www.jobbers.io/best-platforms-to-hire-ai-ml-freelancers-in-2026-complete-guide/)
- [Rise - Average Contractor Rates by Role and Country (2026)](https://www.riseworks.io/blog/average-contractor-rates-by-role-and-country-2025)
- [RemotelyTalents - AI Engineer Salaries: US vs Europe vs Latin America](https://www.remotelytalents.com/blog/ai-engineer-salaries-in-2025-us-vs-europe-vs-latin-america)

---

## 7. 正社員年収との比較

### 日本のAIエンジニア正社員年収

| 企業タイプ | 年収 |
|-----------|------|
| 一般企業 | 平均571万円 |
| 国内メガベンチャー（メンバー） | 600〜900万円 |
| 国内メガベンチャー（リーダー） | 900〜1,200万円 |
| 外資系企業 | 1,200〜2,000万円 |
| LLM専門家（転職市場） | 1,700万円以上 |

### フリーランス vs 正社員の倍率

| ケース | 正社員年収 | フリーランス年収 | 倍率 |
|--------|-----------|-----------------|------|
| 一般企業AI | 571万円 | 720〜1,080万円 | **1.3〜1.9倍** |
| メガベンチャー | 900万円 | 1,020〜1,500万円 | **1.1〜1.7倍** |
| 外資系 | 1,500万円 | 1,500〜1,800万円 | **1.0〜1.2倍** |

**情報ソース**:
- [MIRAIE - AIエンジニアの平均年収ランキング（2025年版）](https://miraie-group.jp/sees/article/detail/AI_engineer_nenshu)
- [レバテック - 機械学習エンジニアの年収・海外との違い](https://freelance.levtech.jp/guide/detail/1384/)
- [リラコム - 年収2000万円を目指すAIエンジニアへ](https://comm.relance.jp/blog/ai-engineer-career-strategy-20m-jpy/)
- [Tech Job Finder - LLM活用転職術で年収1700万円](https://www.tech-job-finder.co.jp/articles/llm-ai-engineer-career-strategy/)

---

## 8. 契約形態による相場差

### マージン率の構造

| 契約形態 | マージン率 | エンジニア手取り比率 |
|---------|-----------|-------------------|
| 直接契約 | 0〜10% | 90〜100% |
| 低マージンエージェント（Midworks, PE-BANK） | 10〜15% | 85〜90% |
| 一般エージェント | 20〜30% | 70〜80% |
| SES多重下請け | 40〜50% | 50〜60% |

### 準委任 vs 請負

| 契約形態 | 特徴 | 単価傾向 |
|---------|------|---------|
| 準委任（時間型） | 時間精算、安定性高い | 月50〜90万円 |
| 請負（成果物型） | 品質・納期リスクを負う | 準委任の+20〜40% |

### 稼働日数による時給プレミアム

| 稼働日数 | 月額単価の目安 | 時給プレミアム |
|---------|--------------|-------------|
| 週5日 | 70〜90万円 | ベースライン |
| 週4日 | 60〜75万円 | +7〜10% |
| 週3日 | 45〜60万円 | +10〜15% |
| 週2日 | 30〜45万円 | +15〜25% |

**情報ソース**:
- [コエテコキャリア - フリーランスエージェントの中間マージン相場](https://coeteco.jp/articles/14312)
- [sakufuri - マージンが低いフリーランスエージェント3選+8選](https://sakufuri.jp/media/freelance-agent-margin/)
- [フリマド - フリーランスエージェントのマージン相場・仕組み](https://mobilinkinfinity.com/freelance-agent-margin/)
- [テクニケーション - SESの単価相場と単価アップ方法](https://www.technication.co.jp/blog/ses-unit-price-market-price/)
- [Workship - 準委任契約とSES契約の違い](https://enterprise.goworkship.com/lp/engineer/ses-contract)
- [Zenn - ソフトウェアエンジニアの単価について](https://zenn.dev/manase/scraps/ca7b3215364f65)

---

## 9. フリーランスエージェント経由の単価とマージン

### 主要エージェント比較

| エージェント | マージン | 特徴 |
|------------|--------|------|
| **Midworks** | 10〜15% | 幅広い案件、100万円以上の高単価案件多数 |
| **PE-BANK** | 8〜15% | 30年以上の実績、全国対応、福利厚生充実 |
| **レバテックフリーランス** | 推定20%前後 | 業界最大級の案件数 |
| **ギークスジョブ** | 非公開 | 上場企業運営、平均年収892万円以上 |
| **Findy Freelance** | - | 時給4,000円+案件豊富、約80%フルリモート |
| **FLEXY** | - | 約98%リモート、CTO・技術顧問案件あり |

**情報ソース**:
- [ITプロマガジン - フリーランスエージェントおすすめ31選（2025年最新版）](https://itpropartners.com/blog/14129/)
- [レバテックフリーランス - 単価相場](https://freelance.levtech.jp/project/marketprice/)
- [Findy Freelance公式](https://freelance.findy-code.io/lp02)
- [FLEXY - エージェント情報](https://freelance-start.com/agents/179)
- [やまもとりゅうけん - レバテックのマージン率は高い？](https://www.ryukke.com/?p=6564)
- [フリーランスデビューNavi - フリーランスエージェントの中間マージン相場](https://freelance-debut.net/freelance-agent-margin/)

---

## 10. 本案件スキルセットの希少性評価

| スキル | 市場供給 | 備考 |
|--------|---------|------|
| FastAPI + Python | 豊富 | 一般的なWeb開発スキル |
| Next.js + React + TypeScript | 豊富 | フロントエンド標準スキル |
| **Google ADK マルチエージェント** | **極めて希少** | 2025年リリースの新技術、日本で本番運用事例ごく少数 |
| **MCP複数サーバー統合管理** | **希少** | 2024年末登場の新プロトコル |
| **Gemini Context Caching** | **希少** | @experimental機能 |
| Zoho CRM API（COQL/全モジュール） | **希少** | Salesforceと比較してZoho専門人材は日本で少ない |
| **全スタック一人で設計・実装** | **非常に希少** | フルスタック+AI+外部API+インフラの全域カバーは上位数% |

---

## 11. 結論: 妥当な時給レンジ

### 全調査統合結果

| | 月額 | 時給（160h/月） | 年収換算 |
|--|------|---------------|---------|
| **下限** | 100万円 | **6,200円** | 1,200万円 |
| **中央値** | 115万円 | **7,200円** | 1,380万円 |
| **上限** | 130万円 | **8,100円** | 1,560万円 |

### レンジの根拠

**上限を130万円/8,100円とする理由**:
- テスト・CI/CD不在、コードレビュー不在
- AI支援コーディングへの依存度
- 150万円クラスのアーキテクトは通常、チームマネジメント・品質保証設計まで含む
- 一人開発の属人化リスクが高い

**下限を100万円/6,200円とする理由**:
- 10+外部API統合の実装力は平均シニア（85-90万円）を明確に上回る
- ADK内部解析に基づく独自最適化は高度
- Context Cache 90%コスト削減等の定量成果
- 6ヶ月で本番稼働レベルのシステムを一人で構築した生産性

### 単価向上の余地

テスト追加・CI/CD構築・技術ドキュメント整備の実績が加われば **130〜150万円帯（時給8,100〜9,400円）** への引き上げは十分に根拠がある技術レベル。

---

## 12. 情報ソース一覧

### フリーランス市場全体の相場
1. [レバテック - フリーランスの時給相場を解説](https://levtech.jp/partner/guide/article/detail/389/)
2. [techbiz - フリーランスエンジニアの単価相場と年収実態（2025年最新版）](https://techbiz.com/media/column/money2)
3. [ジンジブ - フリーランスエンジニアの平均年収（2025年最新版）](https://jinjib.co.jp/job-change/freelance-se-average-salary)
4. [セルプロゲート - フリーランスエンジニアの単価相場まとめ](https://freelance.cellpromote.biz/free_lance_engineer_unit_price/)
5. [エン - 2025年10月度フリーランスエンジニア定点調査レポート](https://corp.en-japan.com/newsrelease/2025/43645.html)
6. [エン - 2025年9月度フリーランスエンジニア定点調査レポート](https://corp.en-japan.com/newsrelease/2025/43398.html)
7. [リラコム - フリーランスエンジニアの年収はいくら？（2025年最新）](https://comm.relance.jp/blog/freelance-engineer-salary/)
8. [エンジニアスタイル - フリーランスエンジニアの時給相場](https://engineer-style.jp/articles/5697)

### 業務委託・準委任契約
9. [Zenn - ソフトウェアエンジニアの単価について](https://zenn.dev/manase/scraps/ca7b3215364f65)
10. [レバテック - 企業がエンジニアに業務委託するメリット](https://levtech.jp/partner/guide/article/detail/162/)
11. [インディバース - エンジニアの業務委託は稼げる？](https://freelance.indieverse.co.jp/media/outsourcing/engineer-outsourcing)
12. [Workship - 業務委託に関連するコストはいくら？](https://enterprise.goworkship.com/lp/consignment/cost-howmuch)
13. [Qiita - エンジニア200人に聞いて業務委託単価表を作りました](https://qiita.com/sagae_twins_developper/items/f6f89820021e7ed0050a)

### Python / FastAPI
14. [フリーランススタート - Pythonフリーランスの単価・案件動向（2025年版）](https://freelance-start.com/articles/1165)
15. [テクフリ - Pythonフリーランスの単価相場・案件例（2025年版）](https://freelance.techcareer.jp/articles/wp/skills/python/detail/25038/)
16. [SOKUDAN - Pythonエンジニア平均年収、案件数（2025年）](https://magazine.sokudan.work/post/XQ-H13PI)
17. [フリーランスHub - Python × バックエンドエンジニアの案件](https://freelance-hub.jp/project/cross/227/)
18. [FLEXY - Pythonエンジニアの年収が高い理由](https://flxy.jp/media/article/23447)
19. [PR TIMES - Pythonエンジニア案件2025年最新](https://prtimes.jp/main/html/rd/p/000000064.000116595.html)

### Next.js / React / TypeScript
20. [BIGDATA NAVI - Next.jsスキルでフリーランスになるには？](https://www.bigdata-navi.com/aidrops/7892/)
21. [テクフリ - JavaScriptフリーランスの単価相場（2025年版）](https://freelance.techcareer.jp/articles/wp/detail/25046/)
22. [SOKUDAN - Next.jsエンジニア平均年収、案件数（2025年）](https://magazine.sokudan.work/post/xR7pkALH)
23. [インディバース - Next.jsの業務委託は稼げる？](https://freelance.indieverse.co.jp/media/outsourcing/nextjs-outsourcing)

### AI/機械学習・LLM
24. [フリーランススタート - AIエンジニアのフリーランス案件（2025年最新）](https://freelance-start.com/articles/1215)
25. [FLEXY - AIエンジニアの平均年収は？](https://flxy.jp/media/article/28622)
26. [KOTORA JOURNAL - AIエンジニアの案件単価徹底解説](https://www.kotora.jp/c/57482/)
27. [Relance - フリーランスAIエンジニアは稼げるの？](https://relance.jp/blog/ai-engineer-earn-money/)
28. [プロンプターズ求人 - プロンプトエンジニアの報酬実態2025](https://kyuujin.prompters.jp/career-guide/prompt-engineer-salary/)
29. [レバテックフリーランス - AIエンジニア単価相場](https://freelance.levtech.jp/guide/detail/875/)
30. [BIGDATA NAVI - LangChain副業案件](https://www.bigdata-navi.com/aidrops/9957/)
31. [セルプロゲート - AIエンジニアのフリーランス案件・単価相場・年収](https://cellpromote.biz/column/ai-engineer-free-lance/)
32. [BIGDATA NAVI - 機械学習エンジニア案件の単価は高い？](https://www.bigdata-navi.com/aidrops/7423/)
33. [生成AI総合研究所 - AIエンジニア向けフリーランス案件サイト（2026年版）](https://www.generativeai.tokyo/media/ai_engineer_freelance_sites/)
34. [ContactEARTH - AI案件とは？案件単価や高単価案件獲得のコツ](https://dx-consultant.co.jp/ai-engineer-matter/)
35. [エンジニアスタイル - AIエンジニアフリーランス案件動向](https://engineer-style.jp/articles/7401)

### フルスタックエンジニア
36. [ITプロマガジン - フリーランスエンジニアの単価相場は？](https://itpropartners.com/blog/449/)
37. [リラコム - フルスタックエンジニアは年収1000万円を超える？（2025年最新）](https://comm.relance.jp/blog/fullstack-engineer-salary-roadmap/)
38. [フリーランスHub - フルスタックエンジニアのフリーランス案件](https://freelance-hub.jp/project/job/73/)
39. [FLEXY - フルスタックエンジニアとは？年収相場](https://flxy.jp/media/article/28612)
40. [エンジニアファクトリー - フルスタックエンジニアの年収](https://www.engineer-factory.com/media/career/3714/)

### Google Cloud / インフラ
41. [フリーランススタート - インフラエンジニア案件の単価相場と市場動向](https://freelance-start.com/articles/67)
42. [BIGDATA NAVI - GCPエンジニアのフリーランス求人案件](https://www.bigdata-navi.com/special/13813/)
43. [フリーランススタート - Google Cloud Platformのフリーランス案件](https://freelance-start.com/jobs/skill-236)
44. [ProConsul - GCPエンジニアが稼げるフリーランス案件](https://freeconsul.co.jp/cs/freelance-gcp-engineer/)

### エージェント・マージン
45. [ITプロマガジン - フリーランスエージェントおすすめ31選（2025年最新版）](https://itpropartners.com/blog/14129/)
46. [sakufuri - マージンが低いフリーランスエージェント3選+8選](https://sakufuri.jp/media/freelance-agent-margin/)
47. [コエテコキャリア - フリーランスエージェントの中間マージン相場](https://coeteco.jp/articles/14312)
48. [フリマド - フリーランスエージェントのマージン相場・仕組み](https://mobilinkinfinity.com/freelance-agent-margin/)
49. [レバテックフリーランス - 単価相場](https://freelance.levtech.jp/project/marketprice/)
50. [Findy Freelance公式](https://freelance.findy-code.io/lp02)

### 海外市場
51. [Upwork - Machine Learning Engineer Hourly Rates](https://www.upwork.com/hire/machine-learning-experts/cost/)
52. [Index.dev - Freelance Developer Rates 2025 by Country](https://www.index.dev/blog/freelance-developer-rates-by-country)
53. [Index.dev - LLM Developer Hourly Rates in 2025](https://www.index.dev/blog/llm-developer-hourly-rates)
54. [Jobbers - Best Platforms to Hire AI/ML Freelancers in 2026](https://www.jobbers.io/best-platforms-to-hire-ai-ml-freelancers-in-2026-complete-guide/)
55. [Rise - Average Contractor Rates by Role and Country (2026)](https://www.riseworks.io/blog/average-contractor-rates-by-role-and-country-2025)
56. [RemotelyTalents - AI Engineer Salaries: US vs Europe vs Latin America](https://www.remotelytalents.com/blog/ai-engineer-salaries-in-2025-us-vs-europe-vs-latin-america)

### 正社員年収比較
57. [MIRAIE - AIエンジニアの平均年収ランキング（2025年版）](https://miraie-group.jp/sees/article/detail/AI_engineer_nenshu)
58. [レバテック - 機械学習エンジニアの年収・海外との違い](https://freelance.levtech.jp/guide/detail/1384/)
59. [リラコム - 年収2000万円を目指すAIエンジニアへ](https://comm.relance.jp/blog/ai-engineer-career-strategy-20m-jpy/)
60. [Tech Job Finder - LLM活用転職術で年収1700万円](https://www.tech-job-finder.co.jp/articles/llm-ai-engineer-career-strategy/)

### その他参考
61. [フリーランスコンシェルジュ - 単価相場2025](https://freelance-concierge.jp/articles/detail/87/)
62. [アイレット - ADK活用AI Agent導入支援サービス](https://www.iret.co.jp/news/20251029.html)
63. [レバテック - エンジニアの単価相場（企業向け）](https://levtech.jp/partner/guide/article/detail/344/)
64. [Workship - エンジニアの時給単価と相場](https://enterprise.goworkship.com/lp/engineer/hourlywage-average)
65. [hblab - エンジニア一人月にかかる費用の相場](https://hblab.co.jp/blog/cost-engineer-per-month/)
66. [Another Works - 業務委託契約における単価相場表（PDF）](https://talent.aw-anotherworks.com/price_sheet.pdf)

---

> **免責事項**: 本レポートはWeb上の公開情報を元にAIエージェントが収集・分析したものです。実際の単価は個人の経験・スキル・交渉力・案件内容・クライアントの予算等により大きく異なります。
