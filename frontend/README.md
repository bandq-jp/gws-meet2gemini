# b&q Hub - 統合管理システム

Next.js、React、TypeScript、shadcn/ui を使用して開発された b&q 社内統合管理システムのフロントエンドアプリケーションです。

## ✨ 実装済み機能

### 🔐 認証システム
- **Clerk を使用した Google 認証**
- **@bandq.jp ドメイン制限**: 許可されたドメインのみアクセス可能
- **日本語ローカライゼーション**: 認証UIの日本語対応
- **自動リダイレクト**: 未認証ユーザーの適切な処理

### 🎨 レスポンシブデザイン
- **モバイルファースト**: スマートフォンに最適化されたUI/UX
- **タブレット・PC対応**: 全デバイスでの快適な操作性
- **shadcn/ui コンポーネント**: 統一された美しいデザインシステム
- **ダークモード対応**: システム設定に応じた自動切り替え

### 🧭 ナビゲーション
- **サイドバーナビゲーション**: 
  - ひとキャリ（利用可能）
  - モノテック（準備中）
  - AchieveHR（準備中）
- **モバイル対応**: スワイプジェスチャー対応のコンパクトナビ
- **アクセス制御**: 利用可能・準備中状態の視覚的表示

### 📋 ひとキャリ機能（メイン機能）

#### 議事録管理
- **Google Drive連携**: ワンクリックでの議事録取得
- **リアルタイム検索**: タイトル、参加者、内容での高速検索
- **アカウントフィルタ**: 自分の議事録のみ表示/全アカウント表示の切り替え
- **タブ分類**:
  - 全て: すべての議事録
  - 構造化済み: AI処理完了済み
  - 未処理: 処理待ちの議事録

#### 🤖 自動候補者マッチング
- **会議名解析**: JP形式の会議名から候補者名を自動抽出
  - 例: `JP13:00_谷合 理央様_初回面談` → "谷合 理央" を抽出
- **名前バリエーション生成**: 
  - スペースあり/なし
  - 姓名の順序入れ替え
  - 部分マッチング
- **Zoho CRM検索**: 抽出された名前でのスマート検索
- **信頼度スコア**: マッチング精度の可視化
- **候補者提案**: "もしかして〇〇様ですか？" 形式での提案

#### 🔍 手動候補者検索
- **高機能検索ダイアログ**: 
  - 漢字、ひらがな、カタカナ、ローマ字対応
  - 部分マッチング
  - リアルタイム検索結果表示
- **詳細情報表示**: 
  - 候補者名、ID、メールアドレス
  - Record ID情報
- **選択状態管理**: 視覚的な選択フィードバック

#### ⚡ AI構造化処理
- **候補者選択後の自動処理**: Gemini AIによるデータ抽出
- **構造化データ表示**: 整理された項目別データ表示
- **処理状況の可視化**: ローディング状態とプログレス表示

#### 📄 議事録プレビュー
- **テキスト内容表示**: 原文プレビュー機能
- **外部リンク**: Google Docs へのダイレクトアクセス
- **メタデータ表示**: 日時、主催者、参加者情報

## 🛠️ 技術スタック

### フロントエンド
- **Next.js 15.4.6**: App Router、React Server Components
- **React 19**: 最新機能を活用
- **TypeScript**: 型安全性の確保
- **Tailwind CSS 4**: 効率的なスタイリング
- **shadcn/ui**: 高品質なUIコンポーネント
- **Lucide React**: 美しいアイコンライブラリ
- **date-fns**: 日本語対応の日時処理

### 認証・状態管理
- **Clerk**: 現代的な認証システム
- **React Hooks**: 効率的な状態管理
- **Next.js Middleware**: ルート保護

### 開発ツール
- **Bun**: 高速パッケージマネージャー
- **ESLint**: コード品質管理
- **Prettier**: コードフォーマット

## 🚀 セットアップ方法

### 1. 依存関係のインストール
```bash
cd frontend
bun install
```

### 2. 環境変数の設定
`.env.local` ファイルを作成し、以下を設定：

```env
# Clerk Authentication Keys
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_YOUR_PUBLISHABLE_KEY_HERE
CLERK_SECRET_KEY=sk_test_YOUR_SECRET_KEY_HERE

# Clerk Configuration
NEXT_PUBLIC_CLERK_SIGN_IN_URL=/sign-in
NEXT_PUBLIC_CLERK_SIGN_UP_URL=/sign-up
NEXT_PUBLIC_CLERK_AFTER_SIGN_IN_URL=/
NEXT_PUBLIC_CLERK_AFTER_SIGN_UP_URL=/

# Backend API
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

### 3. Clerk ダッシュボード設定

1. [Clerk Dashboard](https://dashboard.clerk.dev/) でアプリケーションを作成
2. **Restrictions** で以下を設定：
   - Email domains: `bandq.jp` を許可ドメインに追加
   - Block email subaddresses: 無効
   - Block disposable email addresses: 有効

3. **Social Connections** で Google を有効化

### 4. 開発サーバーの起動
```bash
bun dev
```

アプリケーションは `http://localhost:3000` で起動します。

## 📱 レスポンシブデザイン対応

### モバイル（～768px）
- **コンパクトサイドバー**: タッチフレンドリーなナビゲーション
- **単一列レイアウト**: 縦方向スクロールでの快適な操作
- **大きなタッチターゲット**: 指での操作に最適化されたボタンサイズ
- **スワイプジェスチャー**: 直感的な操作

### タブレット（768px～1024px）
- **ハイブリッドレイアウト**: デスクトップとモバイルの中間デザイン
- **柔軟なグリッド**: コンテンツに応じたレスポンシブグリッド
- **適切な余白**: 画面サイズに最適化されたスペーシング

### デスクトップ（1024px～）
- **サイドバー + メインエリア**: 効率的な2カラムレイアウト
- **詳細表示**: 豊富な情報を一画面で表示
- **ホバー効果**: マウス操作に対応したインタラクション

## 🧩 コンポーネント構造

### 主要コンポーネント
- **AppShell**: アプリケーション全体のレイアウト
- **CandidateSearchDialog**: 候補者検索用モーダル
- **Meeting Cards**: 議事録表示カード
- **Auth Pages**: サインイン・サインアップページ

### ユーティリティ
- **API Client**: バックエンドとの通信管理
- **Name Matching**: 候補者名マッチングロジック
- **Date Formatting**: 日本語日時フォーマット

## 🔄 データフロー

1. **認証**: Clerk → ドメイン検証 → アプリアクセス許可
2. **議事録取得**: Google Drive API → Supabase → フロントエンド
3. **候補者マッチング**: 会議名解析 → Zoho CRM検索 → マッチング結果表示
4. **構造化処理**: 候補者選択 → Gemini AI処理 → 結果表示

## 🎯 今後の拡張予定

### モノテック機能
- 技術系人材サービス管理
- スキルマッチング機能
- プロジェクト管理

### AchieveHR機能  
- 人事・採用統合管理
- 面接スケジューリング
- 採用パイプライン管理

### 共通機能
- **分析ダッシュボード**: データ可視化・レポート生成
- **通知システム**: リアルタイム更新通知
- **アクセス権限管理**: ロールベースアクセス制御
- **API拡張**: GraphQL対応、リアルタイム同期

## 🐛 既知の制限事項

- バックエンドAPIが起動している必要があります
- Clerk アプリケーションの設定が必要です
- Google Drive、Zoho CRM、Gemini API の認証情報が必要です

## 📚 参考資料

- [Next.js Documentation](https://nextjs.org/docs)
- [shadcn/ui](https://ui.shadcn.com)
- [Clerk Documentation](https://clerk.com/docs)
- [Tailwind CSS](https://tailwindcss.com)
- [Backend API Documentation](../backend/docs/ENDPOINTS.md)
