# MCPツール一覧と拡張候補（hitocareer / achieve 共通）

このドキュメントは、現在両サイトで利用できる MCP ツールと、追加で定義・利用が可能なツール候補をまとめたものです。コード変更のない読み物として配置しています。

## 1. 現在有効な MCP ツール
両サイト共通で、以下の MCP サーバーに同じツールが載っています。
- エンドポイント
  - hitocareer: `https://hitocareer.com/wp-json/mcp/mcp-adapter-default-server`
  - achieveHR: `https://achievehr.jp/cms/wp-json/mcp/mcp-adapter-default-server`

### 1-1. MCP Adapter 組み込みツール（3 つ）
| 名前 | 役割 | 主な入力 | 出力 | 備考 |
| --- | --- | --- | --- | --- |
| `mcp-adapter-discover-abilities` | すべての WordPress アビリティ一覧 | なし | `abilities[]` | アビリティ→MCPツールの対応を確認するために使用 |
| `mcp-adapter-get-ability-info` | 指定アビリティの詳細 | `ability_name` | 入出力スキーマなど | スキーマ確認に便利 |
| `mcp-adapter-execute-ability` | 任意アビリティ実行 | `ability_name`, `parameters` | `success`, `data` | 実行の入口となる汎用ツール |

### 1-2. カスタム公開ツール（readonly-ability-plugin）
| MCPツール名 (= Ability名) | 概要 | 主な入力 | 出力 | 補足 |
| --- | --- | --- | --- | --- |
| `readonly-plugin/get-latest-posts` | 最新投稿/固定/column をシンプル取得 | `limit (1-20)`, `post_type`(post/page/column/any) | `[{ID,title,permalink,date}]` | ステータス: publish のみ |
| `readonly-plugin/list-articles` | ページング可能な記事リスト | `limit`,`offset`,`order`,`orderby`,`fields`,`with_total`,`post_type` | `items[]`, `total?` | ステータス: publish のみ。fields で返却項目を選択 |
| `readonly-plugin/get-article` | 単一記事の詳細取得（HTML可） | `id` or `slug`, `include_fields`, `post_type` | `article{...}` | 公開記事 + 非公開/下書きも `read_post` 権限があれば取得可 |
| `readonly-plugin/seo-quick-audit` | 簡易SEOチェック | `id` or `slug`, `checks[]`, `post_type` | `checks{...}` | 非公開/下書きも `read_post` 権限で可 |
| `readonly-plugin/list-trending` | 人気/最新記事リスト | `limit`,`metric`,`post_type` | `items[]` | WPP 有効なら人気順、無ければ最新。publish のみ |
| `readonly-plugin/keyword-gap-hints` | キーワードに近い記事候補 | `keyword`, `limit`, `post_type` | `items[]` | WP検索ベース。publish のみ |

### ステータス別の挙動まとめ
- リスト系（list-articles / get-latest-posts / list-trending / keyword-gap-hints）…`post_status=publish` 固定。
- 単品系（get-article / seo-quick-audit）…`publish` 以外でも、リクエストユーザーに `read_post` 権限があれば返却。

## 2. 追加で定義・利用できるツール候補（アイデア）
以下は WordPress Abilities API で定義可能な例です。現状は未実装です。

- 投稿・固定・カスタム投稿の CRUD 系
  - create/update/delete post
  - 下書き一覧、承認待ち一覧、リビジョン取得
- メディア系
  - 画像アップロード（base64 or URL）、メディア一覧
- タクソノミー系
  - カテゴリ/タグの作成・付与・削除、ターム検索
- コメント／ユーザー
  - コメント一覧・モデレーション、ユーザー情報取得・権限チェック
- サイト情報・設定参照
  - サイト基本情報、メニュー構造、ウィジェット、オプション値の参照
- パフォーマンス／ログ
  - 最近のエラー・イベント簡易取得、ヘルスチェック結果取得
- SEO補助
  - サイトマップURL通知、構造化データの簡易検証、内部リンク自動提案の強化版
- カスタム CPT 向け
  - `column` 以外の CPT 対応版リスト・詳細（例：製品、事例など）

※ これらは Abilities API に新しい ability を登録すれば、MCP 側には自動でツールとして露出します。

## 5. 追加で定義できるツール候補（詳細案・網羅版）
実装イメージを付けたより具体的な候補です。すべて Abilities API で ability を追加すれば MCP に自動公開されます。

### 5-1. コンテンツ作成・編集系
- `content/create-post`：新規投稿/固定/CPT 作成（title, content, status, post_type, categories, tags, featured_image_id）。戻り値: 新規 ID とパーマリンク。
- `content/update-post`：本文・タイトル・ステータス・公開日時・アイキャッチ等を更新。差分入力のみで OK。
- `content/duplicate-post`：既存記事を下書きコピーして ID を返す（下書き量産・A/B テストに便利）。
- `content/schedule-post`：予約投稿にステータス変更 + 予約日時設定。
- `content/list-revisions`：指定 ID のリビジョン一覧を返す。
- `content/restore-revision`：リビジョン ID を指定して本文を復元。
- `content/excerpt-generate`：本文から抜粋を自動生成して保存（AI なし、WP 標準 `wp_trim_words`）。

### 5-2. メディア系
- `media/upload-from-url`：画像 URL をダウンロードしメディア登録（MIME チェック付き）。戻り値: attachment ID, URL。
- `media/upload-base64`：base64 画像を受け取り登録。
- `media/list`：件数・offset でメディア一覧、種別/投稿日フィルタ対応。
- `media/alt-autofill`：指定 attachment に alt テキストを一括設定（入力で受け取る）。

### 5-3. タクソノミー・階層データ
- `taxonomy/create-term`：カテゴリ/タグ/任意タクソノミーの term 追加。
- `taxonomy/assign-terms`：投稿に複数 term を付与（上書き or 追記を選択）。
- `taxonomy/list-terms`：タクソノミー別の term 一覧（階層/件数フィルタ）。

### 5-4. コメント・コンタクト
- `comment/list`：投稿 ID でコメント一覧、status フィルタ（hold/approve/spam）。
- `comment/moderate`：approve/spam/trash 操作を一括実行。
- `comment/reply`：管理者として返信コメントを投稿。
（コンタクトフォーム系はプラグイン依存が大きいので、必要時に個別実装推奨）

### 5-5. ユーザー・権限
- `user/get`：ID/メール/ログイン名でユーザー情報と capabilities を返す。
- `user/list`：ロール/検索ワードで一覧。
- `user/check-cap`：任意 capability を評価して true/false を返す。
- `user/create-application-password`：対象ユーザーにアプリパスを発行（WP 6.2+）。

### 5-6. サイト構造・設定参照（読み取り専用）
- `site/info`：サイト名、URL、バージョン、テーマ、PHP/WP バージョン、タイムゾーンなど。
- `menu/list`：ナビゲーションメニュー構造を返す（ラベル/URL/階層）。
- `widget/list`：ウィジェットエリアとウィジェットの配置を返す。
- `option/get`：指定 option 名を返す（安全なホワイトリストのみ）。

### 5-7. パフォーマンス／メンテ
- `health/status`：Site Health API から概要（good/recommended/critical 件数と説明）を返す。
- `cron/list`：登録 cron イベントと次回実行時刻を返す。
- `cache/purge-url`：特定 URL のキャッシュパージ（キャッシュ系プラグインのフックが必要）。
- `transient/cleanup`：期限切れ transients の削除をトリガー。

### 5-8. SEO／コンテンツ品質
- `seo/meta-inspect`：指定記事の title/meta description/OG/Twitterカードを抽出して返す。
- `seo/broken-link-scan`：本文の内部リンクを走査し 404/リダイレクトを検知（件数多い場合は範囲指定）。
- `seo/sitemap-submit`：主要検索エンジンに sitemap ping（シンプルな HTTP リクエスト）。
- `seo/internal-link-suggest`：既存 `keyword-gap-hints` の強化版。キーワード＋カテゴリでフィルタし、記事のスコアを返す。

### 5-9. サイト固有（CPT/ビジネスロジック）
- `column/*` 以外のカスタム投稿専用リスト・詳細（例: 事例、製品、FAQ）。
- `form/lead-export`：特定 CPT を CSV/JSON でエクスポート（カラムは設定で指定）。
- `inventory/update`：在庫や求人ステータスなど、ビジネス固有メタの更新。

### 5-10. テスト・安全装置
- すべての「書き込み系」ability には permission_callback でロール制限（例: `manage_options`）を必ず付与。
- `dry_run` フラグを入力に置き、更新せずにバリデーションだけ返す実装パターンも有効。


## 3. 利用時の注意
- 認証: Basic (Application Password) でアクセスし、まず `initialize` → `Mcp-Session-Id` を取得してから `tools/list` / `tools/call` を行ってください。
- エンドポイント: hitocareer は `/wp-json/mcp/...`、achieveHR は `/cms/wp-json/mcp/...` とサブディレクトリが異なります。
- post_type: `any` を指定すると `post/page/column` を対象に検索します。
- 非公開取得: `get-article` / `seo-quick-audit` は `read_post` 権限必須。

## 4. 用語メモ
- Ability: WordPress 側で登録する機能単位。MCP Adapter がこれを MCP の tool/resource/prompt に自動マッピングします。
- Tool: MCP クライアントが呼び出すエンドポイント。ここではすべて tool として公開。
