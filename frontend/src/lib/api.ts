// BFF プロキシ経由でバックエンドAPI接続
const API_BASE_URL = '/api/proxy';

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

// AI Cost interfaces
export interface AiCostSummary {
  total_cost_usd: string;
  total_meetings: number;
  total_api_calls: number;
  total_tokens: number;
  total_prompt_tokens: number;
  total_output_tokens: number;
  average_cost_per_call: string;
}

export interface CostBreakdown {
  input_cost: string;
  output_cost: string;
  cache_cost: string;
}

export interface MeetingCost {
  meeting_id: string;
  meeting_title: string;
  total_cost: string;
  total_tokens: number;
  api_calls_count: number;
  created_at: string;
  note?: string;
}

export interface AiCostOverview {
  summary: AiCostSummary;
  cost_breakdown: CostBreakdown;
  recent_meetings: MeetingCost[];
  last_updated?: string;
}

export interface ApiCallDetail {
  id: string;
  group_name: string;
  model: string;
  prompt_tokens: number;
  output_tokens: number;
  cached_tokens: number;
  input_cost: string;
  output_cost: string;
  cache_cost: string;
  total_cost: string;
  pricing_tier: string;
  latency_ms: number;
  created_at: string;
}

export interface MeetingCostDetail {
  meeting_id: string;
  meeting_title: string;
  summary: {
    total_cost: string;
    total_prompt_tokens: number;
    total_output_tokens: number;
    total_cached_tokens: number;
    api_calls_count: number;
    input_cost: string;
    output_cost: string;
    cache_cost: string;
  };
  call_details: ApiCallDetail[];
  created_at: string;
}

export interface PricingInfo {
  model: string;
  currency: string;
  pricing_per_million_tokens: {
    input: {
      standard: string;
      high_volume: string;
    };
    output: {
      standard: string;
      high_volume: string;
    };
    context_cache: {
      standard: string;
      high_volume: string;
    };
  };
  thresholds: {
    high_volume_threshold: number;
  };
  notes: string[];
  calculation_example: {
    description: string;
    input_cost: string;
    output_cost: string;
    total_cost: string;
  };
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
    search?: string
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

  // AI Cost endpoints
  async getAiCostSummary(limit = 1000): Promise<AiCostOverview> {
    const params = new URLSearchParams({ limit: limit.toString() });
    return this.request<AiCostOverview>(`/ai-costs/summary?${params.toString()}`);
  }

  async getMeetingCostDetail(meetingId: string): Promise<MeetingCostDetail> {
    return this.request<MeetingCostDetail>(`/ai-costs/meeting/${encodeURIComponent(meetingId)}`);
  }

  async getPricingInfo(): Promise<PricingInfo> {
    return this.request<PricingInfo>('/ai-costs/pricing-info');
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
