import { auth } from '@clerk/nextjs/server';
import { NextRequest, NextResponse } from 'next/server';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';

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

async function handleRequest(
  request: NextRequest,
  params: { path: string[] },
  method: string
) {
  try {
    // Check authentication
    const { userId } = await auth();
    if (!userId) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    // Build the target URL
    const path = params.path.join('/');
    const searchParams = request.nextUrl.searchParams.toString();
    const targetUrl = `${API_BASE_URL}/api/v1/${path}${searchParams ? `?${searchParams}` : ''}`;

    console.log(`[Proxy] ${method} ${targetUrl}`);

    // Prepare headers
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
    };

    // Prepare request options
    const requestOptions: RequestInit = {
      method,
      headers,
    };

    // Add body for POST/PUT requests
    if (method === 'POST' || method === 'PUT') {
      const body = await request.text();
      if (body) {
        requestOptions.body = body;
      }
    }

    // Make the request to the backend
    const response = await fetch(targetUrl, requestOptions);
    
    console.log(`[Proxy] Response: ${response.status} ${response.statusText}`);

    // Return the response
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

  } catch (error) {
    console.error('[Proxy] Request failed:', error);
    return NextResponse.json(
      { error: 'Internal server error', details: error.message },
      { status: 500 }
    );
  }
}