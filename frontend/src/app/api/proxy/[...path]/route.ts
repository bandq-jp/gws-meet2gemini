import { auth, currentUser } from '@clerk/nextjs/server';
import { NextRequest, NextResponse } from 'next/server';
import { GoogleAuth } from 'google-auth-library';

// 環境設定
const USE_LOCAL_BACKEND = process.env.USE_LOCAL_BACKEND === 'true';
const LOCAL_API_BASE_URL = process.env.DEV_BACKEND_BASE || 'http://localhost:8000';
const CLOUD_RUN_BASE_URL = process.env.CLOUD_RUN_BASE || '';
const GCP_SA_JSON = process.env.GCP_SA_JSON || '';

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const resolvedParams = await params;
  return handleRequest(request, resolvedParams, 'GET');
}

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const resolvedParams = await params;
  return handleRequest(request, resolvedParams, 'POST');
}

export async function PUT(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const resolvedParams = await params;
  return handleRequest(request, resolvedParams, 'PUT');
}

export async function DELETE(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const resolvedParams = await params;
  return handleRequest(request, resolvedParams, 'DELETE');
}

export async function PATCH(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const resolvedParams = await params;
  return handleRequest(request, resolvedParams, 'PATCH');
}

async function handleRequest(
  request: NextRequest,
  params: { path: string[] },
  method: string
) {
  try {
    // Clerk認証チェック
    const { userId } = await auth();
    if (!userId) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    // 本番環境での社内ドメイン制限（ローカル開発では無効）
    const IS_LOCAL_DEV = process.env.NODE_ENV === 'development';
    if (!IS_LOCAL_DEV) {
      const user = await currentUser();
      const ALLOWED_DOMAINS = process.env.ALLOWED_EMAIL_DOMAINS?.split(',') || ['@bandq.jp'];
      
      if (user) {
        const userEmails = user.emailAddresses?.map(email => email.emailAddress) || [];
        const hasAllowedEmail = userEmails.some(email => 
          ALLOWED_DOMAINS.some(domain => email.endsWith(domain))
        );
        
        if (!hasAllowedEmail) {
          console.warn(`[Proxy] Access denied for user ${userId}. Email domains: ${userEmails.join(', ')}`);
          return NextResponse.json({ error: 'Access denied - Invalid domain' }, { status: 403 });
        }
      }
    }

    // URL構築
    const path = params.path.join('/');
    const searchParams = request.nextUrl.searchParams.toString();
    const baseUrl = USE_LOCAL_BACKEND ? LOCAL_API_BASE_URL : CLOUD_RUN_BASE_URL;
    const targetUrl = `${baseUrl}/api/v1/${path}${searchParams ? `?${searchParams}` : ''}`;

    console.log(`[Proxy] Mode: ${USE_LOCAL_BACKEND ? 'LOCAL' : 'PRODUCTION'}`);
    console.log(`[Proxy] ${method} ${targetUrl}`);

    // リクエストボディとヘッダーの準備
    let body: ArrayBuffer | string | undefined = undefined;
    const contentType = request.headers.get('content-type');
    const isFileUpload = path.includes('attachments') && path.includes('upload');

    if (method === 'POST' || method === 'PUT' || method === 'PATCH') {
      // ファイルアップロードの場合はバイナリとして処理
      if (isFileUpload) {
        body = await request.arrayBuffer();
        console.log(`[Proxy] File upload detected, body size: ${body.byteLength} bytes`);
      } else {
        const requestBody = await request.text();
        if (requestBody) {
          body = requestBody;
        }
      }
    }

    // ローカル開発の場合は直接fetch
    if (USE_LOCAL_BACKEND) {
      const headers: HeadersInit = {};

      // Content-Typeを元のリクエストから引き継ぐ
      if (contentType) {
        headers['Content-Type'] = contentType;
      } else if (!isFileUpload) {
        headers['Content-Type'] = 'application/json';
      }

      // ファイルアップロード時に重要なヘッダーを引き継ぐ
      if (isFileUpload) {
        const contentLength = request.headers.get('content-length');
        const contentDisposition = request.headers.get('content-disposition');
        const xFilename = request.headers.get('x-filename');

        if (contentLength) headers['Content-Length'] = contentLength;
        if (contentDisposition) headers['Content-Disposition'] = contentDisposition;
        if (xFilename) headers['X-Filename'] = xFilename;

        console.log(`[Proxy] Upload headers:`, { 'Content-Type': contentType, 'Content-Length': contentLength });
      }

      const response = await fetch(targetUrl, {
        method,
        headers,
        body,
      });

      console.log(`[Proxy] Local Response: ${response.status} ${response.statusText}`);

      if (!response.ok) {
        const errorText = await response.text();
        console.error(`[Proxy] Error response: ${errorText}`);
        let errorData;
        try {
          errorData = JSON.parse(errorText);
        } catch {
          errorData = { detail: errorText || response.statusText };
        }
        return NextResponse.json(errorData, { status: response.status });
      }

      const responseData = await response.json();
      return NextResponse.json(responseData);
    }

    // 本番環境: Cloud Run への ID Token 付きリクエスト
    if (!GCP_SA_JSON) {
      console.error('[Proxy] GCP_SA_JSON not configured for production');
      return NextResponse.json(
        { error: 'Service account not configured' }, 
        { status: 500 }
      );
    }

    if (!CLOUD_RUN_BASE_URL) {
      console.error('[Proxy] CLOUD_RUN_BASE_URL not configured for production');
      return NextResponse.json(
        { error: 'Cloud Run URL not configured' }, 
        { status: 500 }
      );
    }

    // Google Auth を使用してID Tokenを取得
    const googleAuth = new GoogleAuth({
      credentials: JSON.parse(GCP_SA_JSON)
    });

    const client = await googleAuth.getIdTokenClient(CLOUD_RUN_BASE_URL);

    // ヘッダーの準備（本番環境）
    const requestHeaders: Record<string, string> = {};
    if (contentType) {
      requestHeaders['Content-Type'] = contentType;
    } else if (!isFileUpload) {
      requestHeaders['Content-Type'] = 'application/json';
    }

    // ファイルアップロード時に重要なヘッダーを引き継ぐ
    if (isFileUpload) {
      const contentLength = request.headers.get('content-length');
      const contentDisposition = request.headers.get('content-disposition');
      const xFilename = request.headers.get('x-filename');

      if (contentLength) requestHeaders['Content-Length'] = contentLength;
      if (contentDisposition) requestHeaders['Content-Disposition'] = contentDisposition;
      if (xFilename) requestHeaders['X-Filename'] = xFilename;
    }

    const requestConfig = {
      url: targetUrl,
      method: method as 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH',
      headers: requestHeaders,
      validateStatus: () => true, // すべてのステータスコードを有効とする
      data: body || undefined,
    };

    const response = await client.request(requestConfig);
    
    console.log(`[Proxy] Cloud Run Response: ${response.status} ${response.statusText}`);

    // レスポンス処理
    if (response.status >= 400) {
      console.error(`[Proxy] Error response:`, response.data);
      return NextResponse.json(
        response.data || { detail: response.statusText }, 
        { status: response.status }
      );
    }

    return NextResponse.json(response.data);

  } catch (error: unknown) {
    console.error('[Proxy] Request failed:', error);
    const message = error instanceof Error ? error.message : String(error);
    return NextResponse.json(
      { error: 'Internal server error', details: message },
      { status: 500 }
    );
  }
}
