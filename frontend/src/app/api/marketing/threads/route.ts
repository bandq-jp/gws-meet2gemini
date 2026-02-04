/**
 * Marketing Threads API Route
 *
 * GET /api/marketing/threads - List user's conversations
 */

import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL =
  process.env.USE_LOCAL_BACKEND === "true"
    ? process.env.DEV_BACKEND_BASE || "http://localhost:8000"
    : process.env.MARKETING_BACKEND_URL || "http://localhost:8000";

export async function GET(request: NextRequest) {
  try {
    const clientSecret = request.headers.get("x-marketing-client-secret");
    if (!clientSecret) {
      return NextResponse.json(
        { error: "Missing client secret" },
        { status: 401 }
      );
    }

    const searchParams = request.nextUrl.searchParams;
    const limit = searchParams.get("limit") || "50";

    const response = await fetch(
      `${BACKEND_URL}/api/v1/marketing/threads?limit=${limit}`,
      {
        headers: {
          Authorization: `Bearer ${clientSecret}`,
        },
        cache: "no-store",
      }
    );

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
