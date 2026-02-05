import { NextRequest, NextResponse } from "next/server";
import { GoogleAuth } from "google-auth-library";

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

const BACKEND_ORIGIN = safeOrigin(BACKEND_BASE);
const BACKEND_AUDIENCE =
  process.env.MARKETING_CHATKIT_BACKEND_AUDIENCE || BACKEND_ORIGIN;
const CLIENT_SECRET_HEADER = "x-marketing-client-secret";
const SERVICE_ACCOUNT_JSON =
  process.env.MARKETING_CHATKIT_GCP_SA_JSON || process.env.GCP_SA_JSON || "";
const REQUIRE_ID_TOKEN_ENV = process.env.MARKETING_CHATKIT_REQUIRE_ID_TOKEN;
const IS_LOCAL_BACKEND = BACKEND_BASE.startsWith("http://localhost");
const SHOULD_USE_ID_TOKEN =
  REQUIRE_ID_TOKEN_ENV === "true" ||
  (REQUIRE_ID_TOKEN_ENV !== "false" && !IS_LOCAL_BACKEND);

function safeOrigin(url: string | undefined | null) {
  if (!url) return "";
  try {
    return new URL(url).origin;
  } catch {
    return "";
  }
}

function buildForwardHeaders(request: NextRequest) {
  const headers = new Headers();
  request.headers.forEach((value, key) => {
    if (key === "host" || key === "content-length") return;
    headers.set(key, value);
  });
  if (!headers.has("accept")) {
    headers.set("accept", "application/json");
  }
  return headers;
}

async function getIdToken(): Promise<string> {
  if (!SERVICE_ACCOUNT_JSON) {
    throw new Error("GCP_SA_JSON (or MARKETING_CHATKIT_GCP_SA_JSON) is not configured");
  }
  if (!BACKEND_AUDIENCE) {
    throw new Error("MARKETING_CHATKIT_BACKEND_URL must be a valid absolute URL");
  }
  const auth = new GoogleAuth({ credentials: JSON.parse(SERVICE_ACCOUNT_JSON) });
  const client = await auth.getIdTokenClient(BACKEND_AUDIENCE);
  const headers = await client.getRequestHeaders();
  const authorization = headers["Authorization"] || headers["authorization"] || "";
  if (!authorization.startsWith("Bearer ")) {
    throw new Error("Failed to mint authorization header for Cloud Run");
  }
  return authorization.split(" ", 2)[1];
}

async function forward(request: NextRequest, threadId: string) {
  // V2 uses /api/v1/marketing-v2/ endpoint
  const backendUrl = `${BACKEND_BASE.replace(/\/$/, "")}/api/v1/marketing-v2/threads/${threadId}`;

  const clientSecret = request.headers.get(CLIENT_SECRET_HEADER);
  if (!clientSecret) {
    return NextResponse.json({ error: "Missing marketing client secret" }, { status: 401 });
  }

  const headers = buildForwardHeaders(request);
  headers.delete("authorization");
  headers.set(CLIENT_SECRET_HEADER, clientSecret);

  if (SHOULD_USE_ID_TOKEN) {
    try {
      const idToken = await getIdToken();
      headers.set("Authorization", `Bearer ${idToken}`);
    } catch (error) {
      console.error("Failed to mint Cloud Run ID token", error);
      return NextResponse.json(
        { error: "Failed to mint Cloud Run ID token" },
        { status: 500 }
      );
    }
  } else {
    headers.set("Authorization", `Bearer ${clientSecret}`);
  }

  const res = await fetch(backendUrl, {
    method: request.method,
    headers,
    cache: "no-store",
  });

  const text = await res.text();
  const nextHeaders = new Headers(res.headers);
  nextHeaders.set("Cache-Control", "no-store");
  nextHeaders.delete("content-length");
  return new NextResponse(text, { status: res.status, headers: nextHeaders });
}

type RouteContext = { params: Promise<{ id: string }> };

export async function GET(request: NextRequest, context: RouteContext) {
  const { id } = await context.params;
  return forward(request, id);
}

export async function DELETE(request: NextRequest, context: RouteContext) {
  const { id } = await context.params;
  return forward(request, id);
}
