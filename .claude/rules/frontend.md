# Frontend Routes

| Path | 概要 |
|------|------|
| `/` | ダッシュボード (サービスカード) |
| `/hitocari` | 議事録一覧 (ページネーション, フィルタ) |
| `/hitocari/[id]` | 議事録詳細 (トランスクリプト, 構造化データ) |
| `/hitocari/candidates` | 候補者一覧 (Zoho CRM, ページネーション, フィルタ) |
| `/hitocari/candidates/[id]` | 候補者詳細 (Zohoデータ, 面談データ, AIマッチング) |
| `/hitocari/mypage` | マイページ |
| `/hitocari/settings` | 設定 |
| `/marketing` | マーケティングAIチャット (ChatKit) |
| `/marketing/[threadId]` | チャットスレッド詳細 |
| `/marketing/dashboard` | 会話一覧 |
| `/marketing/image-gen` | 画像生成UI |
| `/marketing-v2` | b&q エージェント (ADK + Gemini) |
| `/marketing-v2/[threadId]` | エージェントスレッド詳細 |
| `/feedback` | FBレビューダッシュボード (KPI, 一覧, エクスポート) |
| `/sign-in`, `/sign-up` | Clerk認証 |
| `/unauthorized` | アクセス拒否 |
