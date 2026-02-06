/**
 * Marketing V2 Threads API Route
 *
 * GET /api/marketing-v2/threads - List user's conversations (ADK engine)
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

export async function GET(request: NextRequest) {
  try {
    const clientSecret = request.headers.get(CLIENT_SECRET_HEADER);
    if (!clientSecret) {
      return NextResponse.json(
        { error: "Missing client secret" },
        { status: 401 }
      );
    }

    const searchParams = request.nextUrl.searchParams;
    const limit = searchParams.get("limit") || "50";

    const backendUrl = `${BACKEND_BASE.replace(/\/$/, "")}/api/v1/marketing-v2/threads?limit=${limit}`;

    const headers = new Headers();
    headers.set(CLIENT_SECRET_HEADER, clientSecret);
    headers.set("accept", "application/json");

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

    const response = await fetch(backendUrl, {
      headers,
      cache: "no-store",
    });

    if (!response.ok) {
      const detail = await response.json().catch(() => ({}));
      return NextResponse.json(
        { error: detail?.detail || "Failed to fetch threads" },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error("Error fetching threads:", error);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}
