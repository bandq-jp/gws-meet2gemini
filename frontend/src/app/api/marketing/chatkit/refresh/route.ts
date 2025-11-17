"use server";

import { auth } from "@clerk/nextjs/server";
import { NextResponse } from "next/server";

import {
  signMarketingToken,
  verifyMarketingToken,
} from "@/lib/marketing-token";

const TOKEN_SECRET = process.env.MARKETING_CHATKIT_TOKEN_SECRET || "";
const TOKEN_TTL = Number(process.env.MARKETING_CHATKIT_TOKEN_TTL || "900");
const DEV_AUTH_ENABLED =
  process.env.NODE_ENV !== "production" &&
  process.env.NEXT_PUBLIC_DEV_AUTH === "true";
const DEV_USER_ID = process.env.DEV_MARKETING_USER_ID || "dev-marketing-user";

async function resolveUserId(): Promise<string | null> {
  if (DEV_AUTH_ENABLED) {
    return DEV_USER_ID;
  }
  const { userId } = await auth();
  return userId ?? null;
}

export async function POST(request: Request) {
  if (!TOKEN_SECRET) {
    return NextResponse.json(
      { error: "Marketing client secret is not configured." },
      { status: 500 }
    );
  }

  const userId = await resolveUserId();
  if (!userId) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const { currentClientSecret } = await request.json().catch(() => ({
    currentClientSecret: "",
  }));

  if (!currentClientSecret) {
    return NextResponse.json(
      { error: "Missing current client secret" },
      { status: 400 }
    );
  }

  try {
    const payload = verifyMarketingToken(currentClientSecret, TOKEN_SECRET);
    if (payload.sub !== userId) {
      return NextResponse.json(
        { error: "Client secret does not belong to this user" },
        { status: 403 }
      );
    }
    const now = Math.floor(Date.now() / 1000);
    const clientSecret = signMarketingToken(
      {
        sub: payload.sub,
        email: payload.email,
        name: payload.name,
        iat: now,
        exp: now + TOKEN_TTL,
      },
      TOKEN_SECRET
    );
    return NextResponse.json({
      client_secret: clientSecret,
      expires_in: TOKEN_TTL,
    });
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Invalid client secret";
    return NextResponse.json({ error: message }, { status: 401 });
  }
}
