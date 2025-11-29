import { NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const DEFAULT_BASE = "http://localhost:8000";
const derivedBaseFromServer = process.env.MARKETING_CHATKIT_BACKEND_URL
  ? process.env.MARKETING_CHATKIT_BACKEND_URL.replace(/\/api\/v1\/marketing\/chatkit$/, "")
  : null;
const derivedBaseFromPublic = process.env.NEXT_PUBLIC_MARKETING_CHATKIT_URL
  ? process.env.NEXT_PUBLIC_MARKETING_CHATKIT_URL.replace(/\/api\/v1\/marketing\/chatkit$/, "")
  : null;
const BACKEND_BASE =
  derivedBaseFromServer ||
  process.env.DEV_BACKEND_BASE ||
  derivedBaseFromPublic ||
  DEFAULT_BASE;

const CLIENT_SECRET_HEADER = "x-marketing-client-secret";
type DuplexRequestInit = RequestInit & { duplex?: "half" };

async function forward(request: NextRequest, id: string) {
  const backendUrl = `${BACKEND_BASE.replace(/\/$/, "")}/api/v1/marketing/model-assets/${id}`;

  if (!backendUrl) {
    return NextResponse.json(
      { error: "MARKETING_CHATKIT_BACKEND_URL is not configured" },
      { status: 500 }
    );
  }

  const clientSecret = request.headers.get(CLIENT_SECRET_HEADER);
  if (!clientSecret) {
    return NextResponse.json({ error: "Missing marketing client secret" }, { status: 401 });
  }

  const headers = new Headers(request.headers);
  headers.set(CLIENT_SECRET_HEADER, clientSecret);
  headers.set("Content-Type", "application/json");

  const init: DuplexRequestInit = {
    method: request.method,
    headers,
    body: request.method === "GET" || request.method === "DELETE" ? undefined : request.body,
    cache: "no-store",
  };
  if (init.body) {
    init.duplex = "half";
  }

  const res = await fetch(backendUrl, init);

  const text = await res.text();
  const nextHeaders = new Headers(res.headers);
  nextHeaders.set("Cache-Control", "no-store");
  nextHeaders.delete("content-length");
  return new NextResponse(text, { status: res.status, headers: nextHeaders });
}

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  return forward(request, id);
}

export async function PUT(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  return forward(request, id);
}

export async function DELETE(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  return forward(request, id);
}
