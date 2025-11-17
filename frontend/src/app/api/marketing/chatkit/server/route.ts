import { NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const DEFAULT_BACKEND_URL = "http://localhost:8000/api/v1/marketing/chatkit";
const BACKEND_URL =
  process.env.MARKETING_CHATKIT_BACKEND_URL || DEFAULT_BACKEND_URL;
const CLIENT_SECRET_HEADER = "x-marketing-client-secret";

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
    backendHeaders.set("Authorization", `Bearer ${clientSecret}`);
    backendHeaders.delete(CLIENT_SECRET_HEADER);

    const backendResponse = await fetch(BACKEND_URL, {
      method: "POST",
      headers: backendHeaders,
      body: request.body,
      signal: controller.signal,
      cache: "no-store",
    });

    const responseHeaders = new Headers(backendResponse.headers);
    responseHeaders.delete("content-length");
    responseHeaders.set("Cache-Control", "no-cache");
    responseHeaders.set("Connection", "keep-alive");

    return new NextResponse(backendResponse.body, {
      status: backendResponse.status,
      headers: responseHeaders,
    });
  } catch (error) {
    console.error("Failed to forward ChatKit request", error);
    return NextResponse.json(
      { error: "Failed to reach marketing ChatKit backend" },
      { status: 502 }
    );
  } finally {
    request.signal.removeEventListener("abort", abort);
  }
}
