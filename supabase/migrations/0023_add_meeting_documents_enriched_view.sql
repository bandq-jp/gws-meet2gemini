-- meeting_documents にstructured_outputs の情報を結合したビュー
-- 全タブ(全て・構造化・未処理・同期失敗)で1クエリでフィルタ+ページネーション可能
CREATE OR REPLACE VIEW meeting_documents_enriched AS
SELECT
  md.id,
  md.doc_id,
  md.title,
  md.meeting_datetime,
  md.organizer_email,
  md.organizer_name,
  md.document_url,
  md.invited_emails,
  md.created_at,
  md.updated_at,
  EXISTS (SELECT 1 FROM structured_outputs so WHERE so.meeting_id = md.id) AS is_structured,
  (SELECT so.zoho_sync_status FROM structured_outputs so WHERE so.meeting_id = md.id LIMIT 1) AS zoho_sync_status
FROM meeting_documents md;
