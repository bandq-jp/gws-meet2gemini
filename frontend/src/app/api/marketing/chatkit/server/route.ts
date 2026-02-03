import { NextRequest, NextResponse } from "next/server";
import { GoogleAuth } from "google-auth-library";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export const maxDuration = 300; // 5 minutes for Vercel Pro plan

const DEFAULT_BACKEND_URL = "http://localhost:8000/api/v1/marketing/chatkit";
const BACKEND_URL =
  process.env.MARKETING_CHATKIT_BACKEND_URL || DEFAULT_BACKEND_URL;
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
  if (!url) {
    return "";
  }
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
  if (!headers.has("accept")) {
    headers.set("accept", "text/event-stream, application/json");
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
      { error: "MARKETING_CHATKIT_BACKEND_URL is not configured" },
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

    const backendHeaders = buildForwardHeaders(request);
    backendHeaders.delete(CLIENT_SECRET_HEADER);
    backendHeaders.delete("authorization");
    backendHeaders.set(CLIENT_SECRET_HEADER, clientSecret);

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

    const responseHeaders = new Headers(backendResponse.headers);
    responseHeaders.delete("content-length");
    responseHeaders.set("Cache-Control", "no-cache");
    responseHeaders.set("Connection", "keep-alive");
    responseHeaders.set("X-Accel-Buffering", "no"); // Disable Nginx/proxy buffering

    return new NextResponse(backendResponse.body, {
      status: backendResponse.status,
      headers: responseHeaders,
    });
  } catch (error) {
    // Client aborted the request - this is normal (e.g., page navigation)
    if (error instanceof Error && error.name === "AbortError") {
      console.log("ChatKit request aborted by client (normal behavior)");
      return new NextResponse(null, { status: 499 }); // Client Closed Request
    }

    console.error("Failed to forward ChatKit request", error);
    return NextResponse.json(
      { error: "Failed to reach marketing ChatKit backend" },
      { status: 502 }
    );
  } finally {
    request.signal.removeEventListener("abort", abort);
  }
}
