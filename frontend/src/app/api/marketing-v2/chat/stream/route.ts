import { NextRequest, NextResponse } from "next/server";
import { GoogleAuth } from "google-auth-library";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export const maxDuration = 300; // 5 minutes for Vercel Pro plan

const DEFAULT_BACKEND_URL = "http://localhost:8000/api/v1/marketing-v2/chat/stream";
const BACKEND_URL =
  process.env.MARKETING_V2_CHAT_STREAM_BACKEND_URL ||
  process.env.MARKETING_CHATKIT_BACKEND_URL?.replace("/chatkit", "-v2/chat/stream") ||
  DEFAULT_BACKEND_URL;
const BACKEND_ORIGIN = safeOrigin(BACKEND_URL);
const BACKEND_AUDIENCE =
  process.env.MARKETING_CHATKIT_BACKEND_AUDIENCE || BACKEND_ORIGIN;
const CLIENT_SECRET_HEADER = "x-marketing-client-secret";
const MODEL_ASSET_HEADER = "x-model-asset-id";
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
  if (!BACKEND_AUDIENCE) {
    throw new Error("Backend URL must be a valid absolute URL");
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
  if (!BACKEND_URL) {
    return NextResponse.json(
      { error: "Backend URL is not configured" },
      { status: 500 }
    );
  }

  const controller = new AbortController();
  const abort = () => controller.abort();
  request.signal.addEventListener("abort", abort);

  try {
    const clientSecret = request.headers.get(CLIENT_SECRET_HEADER);
    if (!clientSecret) {
      return NextResponse.json(
        { error: "Missing marketing client secret" },
        { status: 401 }
      );
    }

    // Build backend headers
    const backendHeaders = new Headers();
    backendHeaders.set("Content-Type", "application/json");
    backendHeaders.set("Accept", "text/event-stream");
    backendHeaders.set(CLIENT_SECRET_HEADER, clientSecret);

    // Forward model asset ID if present
    const modelAssetId = request.headers.get(MODEL_ASSET_HEADER);
    if (modelAssetId) {
      backendHeaders.set(MODEL_ASSET_HEADER, modelAssetId);
    }

    // Add authorization
    if (SHOULD_USE_ID_TOKEN) {
      try {
        const idToken = await getIdToken();
        backendHeaders.set("Authorization", `Bearer ${idToken}`);
      } catch (error) {
        console.error("Failed to mint Cloud Run ID token", error);
        return NextResponse.json(
          { error: "Failed to mint Cloud Run ID token" },
          { status: 500 }
        );
      }
    } else {
      backendHeaders.set("Authorization", `Bearer ${clientSecret}`);
    }

    // Parse request body
    const body = await request.json();

    const backendResponse = await fetch(BACKEND_URL, {
      method: "POST",
      headers: backendHeaders,
      body: JSON.stringify(body),
      signal: controller.signal,
      cache: "no-store",
    });

    if (!backendResponse.ok) {
      const errorText = await backendResponse.text().catch(() => "Unknown error");
      console.error("Backend error:", backendResponse.status, errorText);
      return NextResponse.json(
        { error: "Backend error", detail: errorText },
        { status: backendResponse.status }
      );
    }

    // Build response headers for SSE
    const responseHeaders = new Headers();
    responseHeaders.set("Content-Type", "text/event-stream");
    responseHeaders.set("Cache-Control", "no-cache");
    responseHeaders.set("Connection", "keep-alive");
    responseHeaders.set("X-Accel-Buffering", "no");

    return new NextResponse(backendResponse.body, {
      status: 200,
      headers: responseHeaders,
    });
  } catch (error) {
    if (error instanceof Error && error.name === "AbortError") {
      console.log("Chat stream request aborted by client");
      return new NextResponse(null, { status: 499 });
    }

    console.error("Failed to forward chat stream request", error);
    return NextResponse.json(
      { error: "Failed to reach backend" },
      { status: 502 }
    );
  } finally {
    request.signal.removeEventListener("abort", abort);
  }
}
