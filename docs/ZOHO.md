# Zoho CRM 連携（読み取り専用）

このドキュメントは、Zoho CRM のカスタムモジュール「APP-hc（CustomModule1）」から求職者名・求職者IDを読み取り、会議名の人物と照合するための手順をまとめたものです。書き込み処理は行いません。

## 前提設定
- データセンター（日本）:
  - 認可: `https://accounts.zoho.jp`
  - API: `https://www.zohoapis.jp`
- `.env`（必須）:
  - `ZOHO_CLIENT_ID`, `ZOHO_CLIENT_SECRET`, `ZOHO_REFRESH_TOKEN`
  - `ZOHO_ACCOUNTS_BASE_URL=https://accounts.zoho.jp`
  - `ZOHO_API_BASE_URL=https://www.zohoapis.jp`
  - `ZOHO_APP_HC_MODULE=CustomModule1`（既定値）
  - 失敗時の補助: `ZOHO_APP_HC_NAME_FIELD_API`（求職者名）, `ZOHO_APP_HC_ID_FIELD_API`（求職者ID）
- スコープ（同意時）:
  - `ZohoCRM.modules.custom.READ,ZohoCRM.settings.fields.READ,offline_access`

## トークン取得（概要）
1) 認可URL（JP）を開いて code を取得
- `https://accounts.zoho.jp/oauth/v2/auth?response_type=code&client_id=<CLIENT_ID>&scope=ZohoCRM.modules.custom.READ,ZohoCRM.settings.fields.READ,offline_access&redirect_uri=http%3A%2F%2Flocalhost%3A8000%2Foauth%2Fzoho%2Fcallback&access_type=offline&prompt=consent`
2) 交換（curl）で `refresh_token` を取得
- `curl -X POST "https://accounts.zoho.jp/oauth/v2/token" -d "grant_type=authorization_code&client_id=<CLIENT_ID>&client_secret=<CLIENT_SECRET>&redirect_uri=http://localhost:8000/oauth/zoho/callback&code=<CODE>"`
3) `.env` に `ZOHO_REFRESH_TOKEN` を保存し、サーバを再起動

## 検索API（このリポジトリ）
- エンドポイント: `GET /api/v1/zoho/app-hc/search?name=<日本語可>&limit=5`
- 目的: APP-hc の「求職者名」ラベルのフィールドで部分一致検索し、以下を返却
  - `record_id`（ZohoレコードID）, `candidate_name`（求職者名）, `candidate_id`（求職者ID）
- 例（ローカル）:
```
curl --http1.1 "http://localhost:8000/api/v1/zoho/app-hc/search?name=伊藤&limit=5"
```
- 備考:
  - フィールドの API 名は自動解決（`/crm/v2/settings/fields?module=CustomModule1`）します。
  - 自動解決に失敗する場合は `.env` に API 名を明示してください。

## モジュール/フィールドの発見（表示ラベルとAPI名の対応を確認）
- モジュール一覧:
```
curl --http1.1 "http://localhost:8000/api/v1/zoho/modules"
```
- フィールド一覧（例: `CustomModule1` → 実環境の `api_name` に置き換え）:
```
curl --http1.1 "http://localhost:8000/api/v1/zoho/fields?module=CustomModule1"
```
- 上記の出力から、求職者名/求職者IDに対応する `api_name` を特定し、必要なら `.env` に設定:
  - `ZOHO_APP_HC_NAME_FIELD_API=...`
  - `ZOHO_APP_HC_ID_FIELD_API=...`

## トラブルシュート
- 401/400: `ZOHO_REFRESH_TOKEN` 未設定または無効。認可フローをやり直してください（`offline_access` 必須）。
- `redirect_uri 無効`: Zohoコンソールの登録値・認可URL・交換時の全てを完全一致させる（http/https, 末尾スラッシュ, host を統一）。
- フィールドが見つからない: 表示ラベルと API 名の差異がある場合、`.env` で `ZOHO_APP_HC_NAME_FIELD_API` / `ZOHO_APP_HC_ID_FIELD_API` を設定。
