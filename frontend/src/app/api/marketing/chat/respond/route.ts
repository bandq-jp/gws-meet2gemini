import { NextRequest, NextResponse } from "next/server";
import { GoogleAuth } from "google-auth-library";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const DEFAULT_BACKEND_URL =
  "http://localhost:8000/api/v1/marketing/chat/respond";
const BACKEND_URL =
  process.env.MARKETING_CHAT_RESPOND_URL ||
  (process.env.MARKETING_CHATKIT_BACKEND_URL
    ? process.env.MARKETING_CHATKIT_BACKEND_URL.replace(
        /\/chatkit\/?$/,
        "/chat/respond"
      )
    : DEFAULT_BACKEND_URL);
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

export async function POST(request: NextRequest) {
  try {
    const clientSecret = request.headers.get(CLIENT_SECRET_HEADER);
    if (!clientSecret) {
      return NextResponse.json(
        { error: "Missing marketing client secret" },
        { status: 401 }
      );
    }

    const body = await request.json();
    const backendHeaders: Record<string, string> = {
      "Content-Type": "application/json",
      [CLIENT_SECRET_HEADER]: clientSecret,
    };

    if (SHOULD_USE_ID_TOKEN) {
      const idToken = await getIdToken();
      backendHeaders["Authorization"] = `Bearer ${idToken}`;
    } else {
      backendHeaders["Authorization"] = `Bearer ${clientSecret}`;
    }

    const res = await fetch(BACKEND_URL, {
      method: "POST",
      headers: backendHeaders,
      body: JSON.stringify(body),
    });

    const data = await res.json().catch(() => ({}));
    return NextResponse.json(data, { status: res.status });
  } catch (error) {
    console.error("Failed to forward respond request", error);
    return NextResponse.json(
      { error: "Failed to reach marketing backend" },
      { status: 502 }
    );
  }
}
