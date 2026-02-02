import { NextRequest, NextResponse } from "next/server";
import { GoogleAuth } from "google-auth-library";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const DEFAULT_BACKEND_URL =
  "http://localhost:8000/api/v1/marketing/chat/stream";
const BACKEND_URL =
  process.env.MARKETING_CHAT_STREAM_URL ||
  (process.env.MARKETING_CHATKIT_BACKEND_URL
    ? process.env.MARKETING_CHATKIT_BACKEND_URL.replace(
        /\/chatkit\/?$/,
        "/chat/stream"
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
type DuplexRequestInit = RequestInit & { duplex?: "half" };

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

    const backendHeaders = new Headers();
    backendHeaders.set("Content-Type", "application/json");
    backendHeaders.set("Accept", "text/event-stream");
    backendHeaders.set(CLIENT_SECRET_HEADER, clientSecret);

    // Forward model asset header
    const modelAssetId = request.headers.get("x-model-asset-id");
    if (modelAssetId) {
      backendHeaders.set("x-model-asset-id", modelAssetId);
    }

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

    const backendInit: DuplexRequestInit = {
      method: "POST",
      headers: backendHeaders,
      body: request.body,
      signal: controller.signal,
      cache: "no-store",
      duplex: "half",
    };

    const backendResponse = await fetch(BACKEND_URL, backendInit);

    const responseHeaders = new Headers();
    responseHeaders.set("Content-Type", "text/event-stream");
    responseHeaders.set("Cache-Control", "no-cache");
    responseHeaders.set("Connection", "keep-alive");

    return new NextResponse(backendResponse.body, {
      status: backendResponse.status,
      headers: responseHeaders,
    });
  } catch (error) {
    if (error instanceof Error && error.name === "AbortError") {
      return new NextResponse(null, { status: 499 });
    }
    console.error("Failed to forward chat stream request", error);
    return NextResponse.json(
      { error: "Failed to reach marketing backend" },
      { status: 502 }
    );
  } finally {
    request.signal.removeEventListener("abort", abort);
  }
}
