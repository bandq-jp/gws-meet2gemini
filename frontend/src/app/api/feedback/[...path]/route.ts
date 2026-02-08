/**
 * Feedback API Proxy
 *
 * Proxies all /api/feedback/* requests to the backend /api/v1/feedback/*
 * Uses the same auth pattern as marketing-v2 API routes.
 */

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

function safeOrigin(url: string | undefined | null) {
  if (!url) return "";
  try {
    return new URL(url).origin;
  } catch {
    return "";
  }
}

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

async function getIdToken(): Promise<string> {
  if (!SERVICE_ACCOUNT_JSON) {
    throw new Error("GCP_SA_JSON is not configured");
  }
  if (!BACKEND_AUDIENCE) {
    throw new Error("Backend URL must be a valid absolute URL");
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

async function proxyRequest(request: NextRequest, method: string) {
  try {
    const clientSecret = request.headers.get(CLIENT_SECRET_HEADER);
    if (!clientSecret) {
      return NextResponse.json({ error: "Missing client secret" }, { status: 401 });
    }

    // Extract the path after /api/feedback/
    const url = new URL(request.url);
    const feedbackPath = url.pathname.replace(/^\/api\/feedback/, "");
    const backendUrl = `${BACKEND_BASE.replace(/\/$/, "")}/api/v1/feedback${feedbackPath}${url.search}`;

    const headers = new Headers();
    headers.set(CLIENT_SECRET_HEADER, clientSecret);
    headers.set("accept", "application/json");

    if (SHOULD_USE_ID_TOKEN) {
      try {
        const idToken = await getIdToken();
        headers.set("Authorization", `Bearer ${idToken}`);
      } catch (error) {
        console.error("Failed to mint Cloud Run ID token", error);
        return NextResponse.json({ error: "Failed to mint Cloud Run ID token" }, { status: 500 });
      }
    } else {
      headers.set("Authorization", `Bearer ${clientSecret}`);
    }

    const fetchOptions: RequestInit = {
      method,
      headers,
      cache: "no-store",
    };

    if (method !== "GET" && method !== "DELETE") {
      const body = await request.text();
      if (body) {
        headers.set("Content-Type", "application/json");
        fetchOptions.body = body;
      }
    }

    const response = await fetch(backendUrl, fetchOptions);

    // Handle streaming responses (export)
    const contentType = response.headers.get("content-type") || "";
    if (contentType.includes("ndjson") || contentType.includes("csv")) {
      const blob = await response.blob();
      return new NextResponse(blob, {
        status: response.status,
        headers: {
          "Content-Type": contentType,
          "Content-Disposition": response.headers.get("content-disposition") || "",
        },
      });
    }

    if (!response.ok) {
      const detail = await response.json().catch(() => ({}));
      return NextResponse.json(
        { error: detail?.detail || "Backend error" },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error("Feedback proxy error:", error);
    return NextResponse.json({ error: "Internal server error" }, { status: 500 });
  }
}

export async function GET(request: NextRequest) {
  return proxyRequest(request, "GET");
}

export async function POST(request: NextRequest) {
  return proxyRequest(request, "POST");
}

export async function PUT(request: NextRequest) {
  return proxyRequest(request, "PUT");
}

export async function DELETE(request: NextRequest) {
  return proxyRequest(request, "DELETE");
}
