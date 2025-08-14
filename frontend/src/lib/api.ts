// Direct connection to backend API
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000/api/v1';

export interface Meeting {
  id: string;
  doc_id: string;
  title: string;
  meeting_datetime: string;
  organizer_email: string;
  organizer_name?: string;
  document_url?: string;
  invited_emails: string[];
  text_content?: string;
  metadata?: Record<string, unknown>;
  created_at: string;
  updated_at: string;
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
  created_at?: string;
  updated_at?: string;
}

export interface ZohoCandidate {
  record_id: string;
  candidate_id: string;
  candidate_name: string;
  candidate_email?: string;
}

export interface ApiError {
  detail: string;
  status: number;
}

class ApiClient {
  private async request<T>(
    endpoint: string, 
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${API_BASE_URL}${endpoint}`;
    
    // Prepare headers - add token if available
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
    };

    // Add API token if provided in environment
    if (typeof window !== 'undefined') {
      // Client-side: read from environment variable
      const apiToken = process.env.NEXT_PUBLIC_API_TOKEN;
      if (apiToken && apiToken.trim()) {
        headers['Authorization'] = `Bearer ${apiToken}`;
        console.log('Using API token for authentication');
      }
    }

    const response = await fetch(url, {
      headers,
      mode: 'cors', // Enable CORS for cross-origin requests
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
      } else if (response.status >= 500) {
        throw new ApiError('サーバーエラーが発生しました。バックエンドのログを確認してください。', response.status);
      }

      throw new ApiError(error.detail || response.statusText, response.status);
    }

    return response.json();
  }

  // Meeting endpoints
  async getMeetings(accounts?: string[]): Promise<Meeting[]> {
    const params = new URLSearchParams();
    if (accounts && accounts.length > 0) {
      accounts.forEach(account => params.append('accounts', account));
    }
    const queryString = params.toString();
    const endpoint = `/meetings${queryString ? `?${queryString}` : ''}`;
    
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
    }
  ): Promise<StructuredData> {
    return this.request<StructuredData>(`/structured/process/${encodeURIComponent(meetingId)}`, {
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
}

export const apiClient = new ApiClient();

// Utility functions for candidate name matching
export function extractNamesFromTitle(title: string): string[] {
  // Parse meeting title to extract potential candidate names
  // Format: JP13:00_谷合 理央様_初回面談
  const patterns = [
    /JP\d+:\d+_(.+?)様_/g,
    /JP\d+:\d+_(.+?)_/g,
    /(.+?)様/g,
    /([一-龯々ーァ-ヺ]+)\s*([一-龯々ーァ-ヺ]+)/g, // Japanese name pattern
  ];

  const names: string[] = [];
  
  for (const pattern of patterns) {
    let match;
    while ((match = pattern.exec(title)) !== null) {
      const name = match[1].trim();
      if (name && name.length > 1 && !names.includes(name)) {
        names.push(name);
        // Also add name variations (with/without space)
        if (name.includes(' ')) {
          names.push(name.replace(/\s+/g, ''));
        } else if (name.length > 2) {
          // Try to insert space in middle for Japanese names
          const mid = Math.floor(name.length / 2);
          const spacedName = name.slice(0, mid) + ' ' + name.slice(mid);
          names.push(spacedName);
        }
      }
    }
  }

  return names;
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