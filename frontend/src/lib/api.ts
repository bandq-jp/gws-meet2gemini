// BFF プロキシ経由でバックエンドAPI接続
const API_BASE_URL = '/api/proxy';

export interface ZohoSyncStatus {
  status: string | null;  // success | failed | auth_error | field_mapping_error | error | null
  error: string | null;
  synced_at: string | null;
  fields_count: number | null;
}

export interface MeetingSummary {
  id: string;
  doc_id: string;
  title: string;
  meeting_datetime: string;
  organizer_email: string;
  organizer_name?: string;
  document_url?: string;
  invited_emails: string[];
  is_structured?: boolean;
  zoho_sync_status?: string | null;  // Zoho sync status from structured_outputs
  created_at: string;
  updated_at: string;
}

export interface Meeting extends MeetingSummary {
  text_content?: string;
  metadata?: Record<string, unknown>;
}

export interface MeetingListResponse {
  items: MeetingSummary[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  has_next: boolean;
  has_previous: boolean;
}

export interface StructuredData {
  meeting_id: string;
  data: Record<string, unknown>;
  zoho_candidate?: {
    candidate_id?: string;
    record_id?: string;
    candidate_name?: string;
    candidate_email?: string;
  };
  zoho_sync?: ZohoSyncStatus | null;  // DB保存された同期ステータス
  custom_schema_id?: string;
  schema_version?: string;
  created_at?: string;
  updated_at?: string;
}

export interface StructuredDataOnly {
  meeting_id: string;
  data: Record<string, unknown>;
  custom_schema_id?: string;
  schema_version?: string;
}

export interface ZohoSyncResult {
  meeting_id: string;
  zoho_candidate: {
    candidate_id?: string;
    record_id?: string;
    candidate_name?: string;
    candidate_email?: string;
  };
  zoho_sync_result: {
    status: string;
    message: string;
    updated_fields_count?: number;
    updated_fields?: string[];
    zoho_response?: Record<string, unknown>;
    error?: string;
    attempted_data_count?: number;
  };
  synced_data_fields: string[];
}

export interface ZohoCandidate {
  record_id: string;
  candidate_id: string;
  candidate_name: string;
  candidate_email?: string;
}

export interface GeminiSettings {
  gemini_enabled: boolean;
  gemini_model: string;
  gemini_max_tokens: number;
  gemini_temperature: number;
}

export interface SettingsResponse {
  gemini: GeminiSettings;
}

// Image Generation interfaces
export function getImageGenImageUrl(bucket: string, storagePath: string): string {
  return `${API_BASE_URL}/image-gen/images/${bucket}/${storagePath}`;
}

export function getRefImageUrl(storagePath: string): string {
  return getImageGenImageUrl('image-gen-references', storagePath);
}

export interface ImageGenReference {
  id: string;
  template_id: string;
  filename: string;
  storage_path: string;
  mime_type?: string;
  size_bytes?: number;
  sort_order: number;
  label: string;
  created_at?: string;
}

export interface ImageGenTemplate {
  id: string;
  name: string;
  description?: string;
  category?: string;
  aspect_ratio: string;
  image_size: string;
  system_prompt?: string;
  thumbnail_url?: string;
  visibility: string;
  created_by?: string;
  created_by_email?: string;
  image_gen_references?: ImageGenReference[];
  created_at?: string;
  updated_at?: string;
}

export interface ImageGenMessage {
  id: string;
  session_id: string;
  role: string;
  text_content?: string;
  image_url?: string;
  storage_path?: string;
  metadata?: Record<string, unknown>;
  created_at?: string;
}

export interface ImageGenSession {
  id: string;
  template_id?: string;
  title?: string;
  aspect_ratio: string;
  image_size: string;
  created_by?: string;
  created_by_email?: string;
  messages?: ImageGenMessage[];
  created_at?: string;
  updated_at?: string;
}

// Candidate interfaces
export interface CandidateSummary {
  record_id: string;
  name: string;
  status: string | null;
  channel: string | null;
  registration_date: string | null;
  modified_time: string | null;
  pic: string | null;
  linked_meetings_count: number;
}

export interface CandidateListResponse {
  items: CandidateSummary[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  has_next: boolean;
  has_previous: boolean;
  filters: {
    statuses: string[];
    channels: string[];
  };
}

export interface LinkedMeeting {
  meeting_id: string;
  title: string | null;
  meeting_datetime: string | null;
  organizer_email: string | null;
  is_structured: boolean;
}

export interface StructuredOutputBrief {
  meeting_id: string;
  data: Record<string, unknown>;
  created_at: string | null;
}

export interface CandidateDetail {
  record_id: string;
  zoho_record: Record<string, unknown>;
  structured_outputs: StructuredOutputBrief[];
  linked_meetings: LinkedMeeting[];
}

export interface JobMatch {
  jd_id: string | null;
  job_name: string;
  company_name: string;
  match_score: number;
  recommendation_reason: string | null;
  appeal_points: string[];
  concerns: string[];
  salary_range: string | null;
  location: string | null;
  remote: string | null;
  position: string | null;
  hiring_appetite: string | null;
  source: string;
}

export interface JDDetail {
  id: string;
  name: string | null;
  company: string | null;
  company_id: string | null;
  salary_min: number | null;
  salary_max: number | null;
  expected_salary: string | null;
  incentive: string | null;
  location: string | null;
  remote: string | null;
  is_remote: boolean | null;
  flex: string | null;
  is_flex: boolean | null;
  overtime: string | null;
  age_max: number | null;
  education: string | null;
  exp_count_max: number | null;
  hr_experience: string | null;
  job_details: string | null;
  ideal_candidate: string | null;
  hiring_background: string | null;
  org_structure: string | null;
  after_career: string | null;
  category: string | null;
  position: string | null;
  hiring_appetite: string | null;
  benefits: string | null;
  holiday: string | null;
  annual_days_off: string | null;
  is_open: boolean | null;
  fee: string | null;
  jd_manager: string | null;
  company_features: string | null;
  modified_time: string | null;
  module_version: string | null;
}

export interface LineMessageRequest {
  job_name: string;
  company_name: string;
  appeal_points: string[];
  recommendation_reason?: string | null;
  salary_range?: string | null;
  location?: string | null;
  remote?: string | null;
  candidate_name?: string | null;
  candidate_desires?: string | null;
}

export interface LineMessageResponse {
  message: string;
  char_count: number;
}

export interface JobMatchResult {
  candidate_profile: Record<string, unknown>;
  recommended_jobs: JobMatch[];
  total_found: number;
  analysis_text: string | null;
  data_sources_used: string[];
  jd_module_version: string | null;
}

// Custom Schema interfaces
export interface EnumOption {
  id?: string;
  value: string;
  label?: string;
  display_order: number;
}

export interface ValidationRules {
  minimum?: number;
  maximum?: number;
  min_length?: number;
  max_length?: number;
  pattern?: string;
}

export interface SchemaField {
  id?: string;
  field_key: string;
  field_label: string;
  field_description?: string;
  field_type: string; // string, number, integer, array, boolean, object
  is_required: boolean;
  array_item_type?: string;
  group_name: string;
  display_order: number;
  validation_rules?: ValidationRules;
  enum_options: EnumOption[];
}

export interface SchemaGroup {
  name: string;
  description: string;
}

export interface CustomSchema {
  id?: string;
  name: string;
  description?: string;
  is_default: boolean;
  is_active: boolean;
  created_by?: string;
  base_schema_version?: string;
  schema_groups: SchemaGroup[];
  fields: SchemaField[];
  created_at?: string;
  updated_at?: string;
}



export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

class ApiClient {
  private async request<T>(
    endpoint: string, 
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${API_BASE_URL}${endpoint}`;
    
    // Prepare headers - BFFプロキシが認証を処理
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
    };

    const response = await fetch(url, {
      headers,
      ...options,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      console.error('API Error:', {
        url,
        status: response.status,
        statusText: response.statusText,
        error
      });

      // Provide helpful error messages for common issues
      if (response.status === 401) {
        throw new ApiError('API認証が必要です。バックエンドの設定を確認してください。', response.status);
      } else if (response.status === 404) {
        throw new ApiError('APIエンドポイントが見つかりません。バックエンドが起動しているか確認してください。', response.status);
      } else if (response.status === 500) {
        // 500エラーは外部サービス（Zoho等）の問題として扱う
        throw new ApiError(error.detail || 'サービスが一時的に利用できません。', response.status);
      } else if (response.status >= 500) {
        throw new ApiError('サーバーエラーが発生しました。バックエンドのログを確認してください。', response.status);
      }

      throw new ApiError(error.detail || response.statusText, response.status);
    }

    return response.json();
  }

  // Meeting endpoints
  async getMeetings(
    page = 1,
    pageSize = 40,
    accounts?: string[],
    structured?: boolean,
    search?: string,
    zohoSyncFailed?: boolean
  ): Promise<MeetingListResponse> {
    const params = new URLSearchParams();
    params.set('page', page.toString());
    params.set('page_size', pageSize.toString());

    if (accounts && accounts.length > 0) {
      accounts.forEach(account => params.append('accounts', account));
    }

    if (structured !== undefined) {
      params.set('structured', structured.toString());
    }

    if (search && search.trim()) {
      params.set('search', search.trim());
    }

    if (zohoSyncFailed !== undefined) {
      params.set('zoho_sync_failed', zohoSyncFailed.toString());
    }

    return this.request<MeetingListResponse>(`/meetings/?${params.toString()}`);
  }

  async getMeetingsLegacy(accounts?: string[]): Promise<Meeting[]> {
    const params = new URLSearchParams();
    if (accounts && accounts.length > 0) {
      accounts.forEach(account => params.append('accounts', account));
    }
    const queryString = params.toString();
    const endpoint = `/meetings/legacy${queryString ? `?${queryString}` : ''}`;
    
    return this.request<Meeting[]>(endpoint);
  }

  async getMeeting(id: string): Promise<Meeting> {
    return this.request<Meeting>(`/meetings/${encodeURIComponent(id)}`);
  }

  async updateTranscript(
    meetingId: string,
    payload: { text_content: string; transcript_provider?: string; delete_structured?: boolean }
  ): Promise<Meeting> {
    return this.request<Meeting>(`/meetings/${encodeURIComponent(meetingId)}/transcript`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    });
  }

  async collectMeetings(
    accounts?: string[], 
    includeStructure = false, 
    forceUpdate = false
  ): Promise<{ stored: number }> {
    const params = new URLSearchParams();
    if (accounts && accounts.length > 0) {
      accounts.forEach(account => params.append('accounts', account));
    }
    params.set('include_structure', includeStructure.toString());
    params.set('force_update', forceUpdate.toString());
    
    return this.request<{ stored: number }>(`/meetings/collect?${params.toString()}`, {
      method: 'POST',
    });
  }

  async getAvailableAccounts(): Promise<{ accounts: string[] }> {
    return this.request<{ accounts: string[] }>('/meetings/accounts');
  }

  // Structured data endpoints
  async getStructuredData(meetingId: string): Promise<StructuredData> {
    return this.request<StructuredData>(`/structured/${encodeURIComponent(meetingId)}`);
  }

  async processStructuredData(
    meetingId: string,
    candidateData: {
      zoho_candidate_id?: string;
      zoho_record_id?: string;
      zoho_candidate_name?: string;
      zoho_candidate_email?: string;
      custom_schema_id?: string;
    }
  ): Promise<StructuredData> {
    return this.request<StructuredData>(`/structured/process/${encodeURIComponent(meetingId)}`, {
      method: 'POST',
      body: JSON.stringify(candidateData),
    });
  }

  async extractStructuredDataOnly(
    meetingId: string,
    requestData: {
      custom_schema_id?: string;
    } = {}
  ): Promise<StructuredDataOnly> {
    return this.request<StructuredDataOnly>(`/structured/extract-only/${encodeURIComponent(meetingId)}`, {
      method: 'POST',
      body: JSON.stringify(requestData),
    });
  }

  async syncStructuredDataToZoho(
    meetingId: string,
    candidateData: {
      zoho_candidate_id?: string;
      zoho_record_id: string;
      zoho_candidate_name?: string;
      zoho_candidate_email?: string;
    }
  ): Promise<ZohoSyncResult> {
    return this.request<ZohoSyncResult>(`/structured/sync-to-zoho/${encodeURIComponent(meetingId)}`, {
      method: 'POST',
      body: JSON.stringify(candidateData),
    });
  }

  // Zoho CRM endpoints
  async searchZohoCandidates(name: string, limit = 10): Promise<{
    items: ZohoCandidate[];
    count: number;
  }> {
    const params = new URLSearchParams({ name, limit: limit.toString() });
    return this.request<{ items: ZohoCandidate[]; count: number }>(
      `/zoho/app-hc/search?${params.toString()}`
    );
  }

  async getZohoCandidateDetail(recordId: string): Promise<{
    record: Record<string, unknown>;
    record_id: string;
  }> {
    return this.request<{ record: Record<string, unknown>; record_id: string }>(
      `/zoho/app-hc/${encodeURIComponent(recordId)}`
    );
  }

  // Settings endpoints
  async getSettings(): Promise<SettingsResponse> {
    return this.request<SettingsResponse>('/settings');
  }


  async getGeminiModels(): Promise<{ models: Array<{ value: string; label: string; description: string }> }> {
    return this.request<{ models: Array<{ value: string; label: string; description: string }> }>('/settings/gemini/models');
  }

  // Custom Schema endpoints
  async getAllSchemas(includeInactive = false): Promise<CustomSchema[]> {
    const params = new URLSearchParams();
    if (includeInactive) {
      params.set('include_inactive', 'true');
    }
    const queryString = params.toString();
    return this.request<CustomSchema[]>(`/custom-schemas${queryString ? `?${queryString}` : ''}`);
  }

  async getDefaultSchema(): Promise<CustomSchema | null> {
    try {
      return await this.request<CustomSchema>('/custom-schemas/default');
    } catch (error) {
      if (error instanceof ApiError && error.status === 404) {
        return null;
      }
      throw error;
    }
  }

  async getDefaultSchemaDefinition(): Promise<CustomSchema> {
    return this.request<CustomSchema>('/custom-schemas/default-definition');
  }

  async initializeDefaultSchema(): Promise<CustomSchema> {
    return this.request<CustomSchema>('/custom-schemas/init-default', {
      method: 'POST',
    });
  }

  async getSchema(schemaId: string): Promise<CustomSchema> {
    return this.request<CustomSchema>(`/custom-schemas/${encodeURIComponent(schemaId)}`);
  }

  async createSchema(schemaData: {
    name: string;
    description?: string;
    is_default?: boolean;
    schema_groups: SchemaGroup[];
    fields: SchemaField[];
  }): Promise<CustomSchema> {
    return this.request<CustomSchema>('/custom-schemas', {
      method: 'POST',
      body: JSON.stringify(schemaData),
    });
  }

  async updateSchema(
    schemaId: string,
    schemaData: {
      name: string;
      description?: string;
      is_default?: boolean;
      is_active?: boolean;
      schema_groups: SchemaGroup[];
      fields: SchemaField[];
    }
  ): Promise<CustomSchema> {
    return this.request<CustomSchema>(`/custom-schemas/${encodeURIComponent(schemaId)}`, {
      method: 'PUT',
      body: JSON.stringify(schemaData),
    });
  }

  async deleteSchema(schemaId: string): Promise<void> {
    await this.request<void>(`/custom-schemas/${encodeURIComponent(schemaId)}`, {
      method: 'DELETE',
    });
  }

  async setDefaultSchema(schemaId: string): Promise<{ message: string }> {
    return this.request<{ message: string }>(`/custom-schemas/${encodeURIComponent(schemaId)}/set-default`, {
      method: 'POST',
    });
  }

  async duplicateSchema(schemaId: string, newName: string): Promise<CustomSchema> {
    return this.request<CustomSchema>(`/custom-schemas/${encodeURIComponent(schemaId)}/duplicate`, {
      method: 'POST',
      body: JSON.stringify({ new_name: newName }),
    });
  }

  // ── Image Generation endpoints ──

  async listImageGenTemplates(createdBy?: string): Promise<ImageGenTemplate[]> {
    const params = new URLSearchParams();
    if (createdBy) params.set('created_by', createdBy);
    const qs = params.toString();
    return this.request<ImageGenTemplate[]>(`/image-gen/templates${qs ? `?${qs}` : ''}`);
  }

  async getImageGenTemplate(id: string): Promise<ImageGenTemplate> {
    return this.request<ImageGenTemplate>(`/image-gen/templates/${id}`);
  }

  async createImageGenTemplate(data: Omit<ImageGenTemplate, 'id' | 'created_at' | 'updated_at' | 'image_gen_references'>): Promise<ImageGenTemplate> {
    return this.request<ImageGenTemplate>('/image-gen/templates', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateImageGenTemplate(id: string, data: Partial<ImageGenTemplate>): Promise<ImageGenTemplate> {
    return this.request<ImageGenTemplate>(`/image-gen/templates/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async deleteImageGenTemplate(id: string): Promise<void> {
    await this.request<void>(`/image-gen/templates/${id}`, { method: 'DELETE' });
  }

  async uploadImageGenReference(templateId: string, file: File, label: string = 'style'): Promise<ImageGenReference> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('label', label);
    const url = `${API_BASE_URL}/image-gen/templates/${templateId}/references`;
    const response = await fetch(url, {
      method: 'POST',
      body: formData,
      // Do NOT set Content-Type header - let browser set it with boundary for multipart
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new ApiError(error.detail || response.statusText, response.status);
    }
    return response.json();
  }

  async deleteImageGenReference(id: string): Promise<void> {
    await this.request<void>(`/image-gen/references/${id}`, { method: 'DELETE' });
  }

  async reorderImageGenReferences(templateId: string, referenceIds: string[]): Promise<void> {
    await this.request<void>(`/image-gen/templates/${templateId}/references/order`, {
      method: 'PUT',
      body: JSON.stringify({ reference_ids: referenceIds }),
    });
  }

  async listImageGenSessions(createdBy?: string): Promise<ImageGenSession[]> {
    const params = new URLSearchParams();
    if (createdBy) params.set('created_by', createdBy);
    const qs = params.toString();
    return this.request<ImageGenSession[]>(`/image-gen/sessions${qs ? `?${qs}` : ''}`);
  }

  async getImageGenSession(id: string): Promise<ImageGenSession> {
    return this.request<ImageGenSession>(`/image-gen/sessions/${id}`);
  }

  async createImageGenSession(data: {
    template_id?: string;
    title?: string;
    aspect_ratio?: string;
    image_size?: string;
    created_by?: string;
    created_by_email?: string;
  }): Promise<ImageGenSession> {
    return this.request<ImageGenSession>('/image-gen/sessions', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async generateImage(sessionId: string, data: {
    prompt: string;
    aspect_ratio?: string;
    image_size?: string;
  }): Promise<ImageGenMessage> {
    return this.request<ImageGenMessage>(`/image-gen/sessions/${sessionId}/generate`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getImageGenUsage(): Promise<{
    used: number;
    limit: number;
    remaining: number | null;
    is_unlimited: boolean;
    period: string;
  }> {
    return this.request(`/image-gen/usage`);
  }

  // ── Candidate endpoints ──

  async getCandidates(
    page = 1,
    pageSize = 20,
    search?: string,
    status?: string,
    channel?: string,
    sortBy?: string,
    dateFrom?: string,
    dateTo?: string,
  ): Promise<CandidateListResponse> {
    const params = new URLSearchParams();
    params.set('page', page.toString());
    params.set('page_size', pageSize.toString());
    if (search?.trim()) params.set('search', search.trim());
    if (status) params.set('status', status);
    if (channel) params.set('channel', channel);
    if (sortBy) params.set('sort_by', sortBy);
    if (dateFrom) params.set('date_from', dateFrom);
    if (dateTo) params.set('date_to', dateTo);
    return this.request<CandidateListResponse>(`/candidates?${params.toString()}`);
  }

  async getCandidateDetail(recordId: string): Promise<CandidateDetail> {
    return this.request<CandidateDetail>(`/candidates/${encodeURIComponent(recordId)}`);
  }

  async getCandidateMeetings(recordId: string): Promise<{ items: LinkedMeeting[]; total: number }> {
    return this.request<{ items: LinkedMeeting[]; total: number }>(
      `/candidates/${encodeURIComponent(recordId)}/meetings`
    );
  }

  async matchCandidateJobs(
    recordId: string,
    overrides?: { transfer_reasons?: string; desired_salary?: number; desired_locations?: string[]; limit?: number; jd_module_version?: string }
  ): Promise<JobMatchResult> {
    return this.request<JobMatchResult>(`/candidates/${encodeURIComponent(recordId)}/job-match`, {
      method: 'POST',
      body: JSON.stringify(overrides || {}),
    });
  }

  async getJDDetail(jdId: string, version?: string): Promise<JDDetail> {
    const params = new URLSearchParams();
    if (version) params.set('version', version);
    const qs = params.toString();
    return this.request<JDDetail>(`/candidates/jd/${encodeURIComponent(jdId)}${qs ? `?${qs}` : ''}`);
  }

  async generateLineMessage(data: LineMessageRequest): Promise<LineMessageResponse> {
    return this.request<LineMessageResponse>('/candidates/line-message/generate', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

}

export const apiClient = new ApiClient();

// Utility functions for candidate name matching
export function extractNamesFromTitle(title: string): string[] {
  // Parse meeting title to extract potential candidate names
  // Formats to handle:
  // - JP12:45~川嶋 拓海様_初回面談
  // - JP13:00_谷合 理央様_初回面談
  // - 田中太郎様_面談
  const patterns = [
    // JP時間~名前様 pattern
    /JP\d{1,2}:\d{2}[~_](.+?)様/g,
    // JP時間_名前様_その他 pattern
    /JP\d{1,2}:\d{2}_(.+?)様_/g,
    // JP時間_名前_その他 pattern (様なし)
    /JP\d{1,2}:\d{2}_(.+?)_/g,
    // 名前様 pattern (JPなし)
    /([一-龯々ーァ-ヺ\s]+)様/g,
    // 一般的な日本語の姓名パターン
    /([一-龯々ーァ-ヺ]{1,4})\s+([一-龯々ーァ-ヺ]{1,4})/g,
  ];

  const names: string[] = [];
  
  for (const pattern of patterns) {
    let match;
    // Reset pattern index for global patterns
    pattern.lastIndex = 0;
    
    while ((match = pattern.exec(title)) !== null) {
      let name = '';
      
      // Handle different match groups
      if (pattern.source.includes('([一-龯々ーァ-ヺ]{1,4})\\s+([一-龯々ーァ-ヺ]{1,4})')) {
        // Two-group Japanese name pattern
        if (match[1] && match[2]) {
          name = `${match[1]} ${match[2]}`;
        }
      } else {
        // Single group pattern
        name = match[1]?.trim() || '';
      }
      
      if (name && name.length > 1 && !names.includes(name)) {
        // Clean up the name - remove extra whitespace
        name = name.replace(/\s+/g, ' ').trim();
        
        // Skip if it contains time patterns or non-name content
        if (!/\d{1,2}:\d{2}|初回|面談|面接|ミーティング/.test(name)) {
          names.push(name);
          
          // Add name variations
          if (name.includes(' ')) {
            // Add version without space
            names.push(name.replace(/\s+/g, ''));
          }
        }
      }
    }
  }

  // Remove duplicates and sort by length (longer names first)
  const uniqueNames = [...new Set(names)]
    .filter(name => name.length > 1)
    .sort((a, b) => b.length - a.length);

  return uniqueNames;
}

export function createCandidateSearchVariations(names: string[]): string[] {
  const variations: string[] = [];
  
  for (const name of names) {
    // Add original name
    variations.push(name);
    
    // Add name without spaces
    variations.push(name.replace(/\s+/g, ''));
    
    // Add name parts separately
    const parts = name.split(/\s+/);
    if (parts.length > 1) {
      variations.push(...parts.filter(part => part.length > 0));
    }
    
    // Add reversed name (surname first vs given name first)
    if (parts.length === 2) {
      variations.push(`${parts[1]} ${parts[0]}`);
      variations.push(`${parts[1]}${parts[0]}`);
    }
  }

  return [...new Set(variations)].filter(v => v.length > 1);
}
