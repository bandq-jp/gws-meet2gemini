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

const BACKEND_URL = `${BACKEND_BASE.replace(/\/$/, "")}/api/v1/marketing/model-assets`;
const BACKEND_ORIGIN = safeOrigin(BACKEND_URL);
const BACKEND_AUDIENCE =
  process.env.MARKETING_CHATKIT_BACKEND_AUDIENCE || BACKEND_ORIGIN;
const CLIENT_SECRET_HEADER = "x-marketing-client-secret";
const SERVICE_ACCOUNT_JSON =
  process.env.MARKETING_CHATKIT_GCP_SA_JSON || process.env.GCP_SA_JSON || "";
const REQUIRE_ID_TOKEN_ENV = process.env.MARKETING_CHATKIT_REQUIRE_ID_TOKEN;
const IS_LOCAL_BACKEND = BACKEND_URL.startsWith("http://localhost");
const SHOULD_USE_ID_TOKEN =
  REQUIRE_ID_TOKEN_ENV === "true" ||
  (REQUIRE_ID_TOKEN_ENV !== "false" && !IS_LOCAL_BACKEND);
type DuplexRequestInit = RequestInit & { duplex?: "half" };

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

async function forward(request: NextRequest) {
  if (!BACKEND_URL) {
    return NextResponse.json(
      { error: "MARKETING_CHATKIT_BACKEND_URL is not configured" },
      { status: 500 }
    );
  }

  const clientSecret = request.headers.get(CLIENT_SECRET_HEADER);
  if (!clientSecret) {
    return NextResponse.json({ error: "Missing marketing client secret" }, { status: 401 });
  }

  const headers = buildForwardHeaders(request);
  headers.delete("authorization");
  headers.set(CLIENT_SECRET_HEADER, clientSecret);
  headers.set("Content-Type", "application/json");

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

  const init: DuplexRequestInit = {
    method: request.method,
    headers,
    body: request.method === "GET" ? undefined : request.body,
    cache: "no-store",
  };
  if (init.body) {
    init.duplex = "half";
  }

  const res = await fetch(BACKEND_URL, init);

  const text = await res.text();
  const nextHeaders = new Headers(res.headers);
  nextHeaders.set("Cache-Control", "no-store");
  // avoid mismatched content-length when streaming
  nextHeaders.delete("content-length");
  return new NextResponse(text, { status: res.status, headers: nextHeaders });
}

export async function GET(request: NextRequest) {
  return forward(request);
}

export async function POST(request: NextRequest) {
  return forward(request);
}

export async function PUT(request: NextRequest) {
  return forward(request);
}

export async function DELETE(request: NextRequest) {
  return forward(request);
}
