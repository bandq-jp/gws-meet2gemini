# Database Tables (Supabase PostgreSQL)

## ひとキャリ関連
| テーブル | 概要 |
|---------|------|
| `meeting_documents` | 議事録メタデータ・本文 (doc_id, title, meeting_datetime, text_content) |
| `structured_outputs` | Gemini抽出結果 (meeting_id FK, data JSONB) |
| `zoho_candidate_links` | 議事録→Zoho候補者マッピング (zoho_sync_status, sync_error) |
| `custom_schemas` | ユーザー定義抽出スキーマ |
| `schema_fields` | スキーマフィールド定義 |
| `field_enum_options` | フィールド列挙値 |
| `ai_usage_logs` | AI API トークン使用量追跡 |

## マーケティングAI関連
| テーブル | 概要 |
|---------|------|
| `marketing_conversations` | ChatKitスレッドメタデータ (owner_email, status, pinned_insights) |
| `marketing_messages` | メッセージ (role, content JSONB, tool_calls JSONB) |
| `marketing_attachments` | ファイルアップロード |
| `marketing_articles` | 記事キャンバス (title, outline, body_markdown) |
| `marketing_model_assets` | モデルプリセット (model_id, reasoning_effort, web_search等) |
| `chat_shares` | スレッド共有権限 |

## 画像生成関連
| テーブル | 概要 |
|---------|------|
| `image_gen_templates` | スタイルテンプレート |
| `image_gen_references` | リファレンス画像 |
| `image_gen_sessions` | 生成セッション |
| `image_gen_messages` | セッション内メッセージ |

## 企業DB（セマンティック検索）
| テーブル | 概要 |
|---------|------|
| `company_chunks` | ベクトル化された企業データ (vector(768), pgvector + IVFFlat) |
| `pic_recommendations` | 担当者別推奨企業 |

### company_chunks スキーマ
- `company_name`: 企業名
- `chunk_type`: overview / requirements / salary / growth / wlb / culture
- `chunk_text`: 埋め込み対象テキスト
- `embedding`: vector(768) — Gemini embedding-001
- `metadata`: JSONB (age_limit, max_salary, locations, remote等)
- `content_hash`: 変更検知用ハッシュ

### 検索RPC
- `search_company_chunks(query_embedding, match_chunk_types, filter_max_age, filter_min_salary, filter_locations, match_count, similarity_threshold)`
