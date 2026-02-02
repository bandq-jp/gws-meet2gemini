import { NextRequest, NextResponse } from "next/server";
import { GoogleAuth } from "google-auth-library";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const DEFAULT_BASE = "http://localhost:8000/api/v1/marketing/chat";
const BASE_URL =
  process.env.MARKETING_CHAT_BASE_URL ||
  (process.env.MARKETING_CHATKIT_BACKEND_URL
    ? process.env.MARKETING_CHATKIT_BACKEND_URL.replace(
        /\/chatkit\/?$/,
        "/chat"
      )
    : DEFAULT_BASE);
const BACKEND_ORIGIN = safeOrigin(BASE_URL);
const BACKEND_AUDIENCE =
  process.env.MARKETING_CHATKIT_BACKEND_AUDIENCE || BACKEND_ORIGIN;
const CLIENT_SECRET_HEADER = "x-marketing-client-secret";
const SERVICE_ACCOUNT_JSON =
  process.env.MARKETING_CHATKIT_GCP_SA_JSON || process.env.GCP_SA_JSON || "";
const REQUIRE_ID_TOKEN_ENV = process.env.MARKETING_CHATKIT_REQUIRE_ID_TOKEN;
const IS_LOCAL_BACKEND = BASE_URL.startsWith("http://localhost");
const SHOULD_USE_ID_TOKEN =
  REQUIRE_ID_TOKEN_ENV === "true" ||
  (REQUIRE_ID_TOKEN_ENV !== "false" && !IS_LOCAL_BACKEND);

let googleAuthPromise: Promise<GoogleAuth> | null = null;

function safeOrigin(url: string | undefined | null) {
  if (!url) return "";
  try {
    return new URL(url).origin;
  } catch {
    return "";
  }
}

async function getIdToken(): Promise<string> {
  if (!SERVICE_ACCOUNT_JSON) {
    throw new Error("GCP_SA_JSON is not configured");
  }
  if (!googleAuthPromise) {
    googleAuthPromise = Promise.resolve(
      new GoogleAuth({ credentials: JSON.parse(SERVICE_ACCOUNT_JSON) })
    );
  }
  const auth = await googleAuthPromise;
  const client = await auth.getIdTokenClient(BACKEND_AUDIENCE);
  const headers = await client.getRequestHeaders();
  const authorization =
    headers["Authorization"] || headers["authorization"] || "";
  if (!authorization.startsWith("Bearer ")) {
    throw new Error("Failed to mint authorization header for Cloud Run");
  }
  return authorization.split(" ", 2)[1];
}

async function proxyRequest(
  method: string,
  path: string,
  clientSecret: string,
  body?: unknown
) {
  const idToken = SHOULD_USE_ID_TOKEN ? await getIdToken() : undefined;
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    [CLIENT_SECRET_HEADER]: clientSecret,
  };
  if (idToken) {
    headers["Authorization"] = `Bearer ${idToken}`;
  } else {
    headers["Authorization"] = `Bearer ${clientSecret}`;
  }

  const init: RequestInit = { method, headers, cache: "no-store" };
  if (body !== undefined) {
    init.body = JSON.stringify(body);
  }

  const url = `${BASE_URL}${path}`;
  const res = await fetch(url, init);
  const data = await res.json().catch(() => ({}));
  return NextResponse.json(data, { status: res.status });
}

// GET /api/marketing/chat/threads/[id] -> get thread + messages
export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const clientSecret = request.headers.get(CLIENT_SECRET_HEADER);
  if (!clientSecret) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  try {
    const { id } = await params;
    return await proxyRequest("GET", `/threads/${id}`, clientSecret);
  } catch (error) {
    console.error("Failed to get thread", error);
    return NextResponse.json({ error: "Backend error" }, { status: 502 });
  }
}

// DELETE /api/marketing/chat/threads/[id] -> delete thread
export async function DELETE(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const clientSecret = request.headers.get(CLIENT_SECRET_HEADER);
  if (!clientSecret) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  try {
    const { id } = await params;
    return await proxyRequest("DELETE", `/threads/${id}`, clientSecret);
  } catch (error) {
    console.error("Failed to delete thread", error);
    return NextResponse.json({ error: "Backend error" }, { status: 502 });
  }
}

// PUT /api/marketing/chat/threads/[id] -> rename thread (title)
export async function PUT(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const clientSecret = request.headers.get(CLIENT_SECRET_HEADER);
  if (!clientSecret) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  try {
    const { id } = await params;
    const body = await request.json().catch(() => ({}));
    return await proxyRequest(
      "PUT",
      `/threads/${id}/title`,
      clientSecret,
      body
    );
  } catch (error) {
    console.error("Failed to rename thread", error);
    return NextResponse.json({ error: "Backend error" }, { status: 502 });
  }
}
