import { NextRequest, NextResponse } from "next/server";
import { GoogleAuth } from "google-auth-library";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const DEFAULT_BASE = "http://localhost:8000";
const derivedBaseFromServer = process.env.MARKETING_CHATKIT_BACKEND_URL
  ? process.env.MARKETING_CHATKIT_BACKEND_URL.replace(
      /\/api\/v1\/marketing\/chatkit$/,
      ""
    )
  : null;
const derivedBaseFromPublic = process.env.NEXT_PUBLIC_MARKETING_CHATKIT_URL
  ? process.env.NEXT_PUBLIC_MARKETING_CHATKIT_URL.replace(
      /\/api\/v1\/marketing\/chatkit$/,
      ""
    )
  : null;
const BACKEND_BASE =
  derivedBaseFromServer ||
  process.env.DEV_BACKEND_BASE ||
  derivedBaseFromPublic ||
  DEFAULT_BASE;

const BACKEND_ORIGIN = safeOrigin(BACKEND_BASE);
const BACKEND_AUDIENCE =
  process.env.MARKETING_CHATKIT_BACKEND_AUDIENCE || BACKEND_ORIGIN;
const SERVICE_ACCOUNT_JSON =
  process.env.MARKETING_CHATKIT_GCP_SA_JSON || process.env.GCP_SA_JSON || "";
const REQUIRE_ID_TOKEN_ENV = process.env.MARKETING_CHATKIT_REQUIRE_ID_TOKEN;
const IS_LOCAL_BACKEND = BACKEND_BASE.startsWith("http://localhost");
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
    if (key === "host" || key === "content-length") {
      return;
    }
    headers.set(key, value);
  });
  return headers;
}

async function getIdToken(): Promise<string> {
  if (!SERVICE_ACCOUNT_JSON) {
    throw new Error(
      "GCP_SA_JSON (or MARKETING_CHATKIT_GCP_SA_JSON) is not configured"
    );
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

async function forwardUpload(
  request: NextRequest,
  attachmentId: string,
  method: "POST" | "PUT"
) {
  const searchParams = request.nextUrl.searchParams.toString();
  const backendUrl = `${BACKEND_BASE.replace(
    /\/$/,
    ""
  )}/api/v1/marketing/attachments/${attachmentId}/upload${
    searchParams ? `?${searchParams}` : ""
  }`;

  const backendHeaders = buildForwardHeaders(request);
  backendHeaders.delete("authorization");

  if (SHOULD_USE_ID_TOKEN) {
    const idToken = await getIdToken();
    backendHeaders.set("Authorization", `Bearer ${idToken}`);
  } else {
    const clientSecret = request.headers.get("x-marketing-client-secret");
    if (clientSecret) {
      backendHeaders.set("Authorization", `Bearer ${clientSecret}`);
    }
  }

  const backendInit: DuplexRequestInit = {
    method,
    headers: backendHeaders,
    body: request.body,
    cache: "no-store",
    duplex: "half",
  };

  const res = await fetch(backendUrl, backendInit);
  const nextHeaders = new Headers(res.headers);
  nextHeaders.delete("content-length");
  nextHeaders.set("Cache-Control", "no-store");
  return new NextResponse(res.body, { status: res.status, headers: nextHeaders });
}

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ attachmentId?: string }> }
) {
  const resolved = await params;
  const attachmentId = resolved?.attachmentId;
  if (!attachmentId) {
    return NextResponse.json({ error: "Missing attachment id" }, { status: 400 });
  }
  try {
    return await forwardUpload(request, attachmentId, "POST");
  } catch (error) {
    console.error("Failed to proxy attachment upload", error);
    return NextResponse.json(
      { error: "Failed to proxy attachment upload" },
      { status: 502 }
    );
  }
}

export async function PUT(
  request: NextRequest,
  { params }: { params: Promise<{ attachmentId?: string }> }
) {
  const resolved = await params;
  const attachmentId = resolved?.attachmentId;
  if (!attachmentId) {
    return NextResponse.json({ error: "Missing attachment id" }, { status: 400 });
  }
  try {
    return await forwardUpload(request, attachmentId, "PUT");
  } catch (error) {
    console.error("Failed to proxy attachment upload", error);
    return NextResponse.json(
      { error: "Failed to proxy attachment upload" },
      { status: 502 }
    );
  }
}

export async function OPTIONS(request: NextRequest) {
  const origin = request.headers.get("origin") || "*";
  return new NextResponse(null, {
    status: 200,
    headers: {
      "Access-Control-Allow-Origin": origin,
      "Access-Control-Allow-Methods": "POST, PUT, OPTIONS",
      "Access-Control-Allow-Headers": "*",
      "Access-Control-Allow-Credentials": "true",
      "Access-Control-Max-Age": "600",
    },
  });
}

