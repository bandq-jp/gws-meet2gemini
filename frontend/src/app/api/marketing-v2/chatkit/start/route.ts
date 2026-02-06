"use server";

import { auth, currentUser } from "@clerk/nextjs/server";
import { NextResponse } from "next/server";

import { signMarketingToken } from "@/lib/marketing-token";

const TOKEN_SECRET = process.env.MARKETING_CHATKIT_TOKEN_SECRET || "";
const TOKEN_TTL = Number(process.env.MARKETING_CHATKIT_TOKEN_TTL || "900");
const DEV_AUTH_ENABLED =
  process.env.NODE_ENV !== "production" &&
  process.env.NEXT_PUBLIC_DEV_AUTH === "true";
const DEV_EMAIL =
  process.env.DEV_MARKETING_USER_EMAIL ||
  process.env.DEV_ALLOWED_IMPERSONATORS?.split(",")[0]?.trim() ||
  (DEV_AUTH_ENABLED ? "dev@localhost" : undefined);
const DEV_NAME = process.env.DEV_MARKETING_USER_NAME || "Marketing Dev User";
const DEV_USER_ID = process.env.DEV_MARKETING_USER_ID || "dev-marketing-user";

type ResolvedUser = {
  userId: string;
  email: string;
  name?: string | null;
};

async function resolveUser(): Promise<ResolvedUser | null> {
  // 1) Try real Clerk session first (even in dev) so actual logged-in users win
  const { userId } = await auth();
  if (userId) {
    const user = await currentUser();
    const email =
      user?.primaryEmailAddress?.emailAddress ||
      user?.emailAddresses?.[0]?.emailAddress;
    if (email) {
      return { userId, email, name: user?.fullName };
    }
  }

  // 2) Fall back to dev impersonation only when explicitly enabled
  if (DEV_AUTH_ENABLED && DEV_EMAIL) {
    return { userId: DEV_USER_ID, email: DEV_EMAIL, name: DEV_NAME };
  }

  return null;
}

export async function POST() {
  if (!TOKEN_SECRET) {
    return NextResponse.json(
      { error: "Marketing client secret is not configured." },
      { status: 500 }
    );
  }

  const resolved = await resolveUser();
  if (!resolved) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const now = Math.floor(Date.now() / 1000);
  const clientSecret = signMarketingToken(
    {
      sub: resolved.userId,
      email: resolved.email,
      name: resolved.name,
      iat: now,
      exp: now + TOKEN_TTL,
    },
    TOKEN_SECRET
  );

  return NextResponse.json({
    client_secret: clientSecret,
    expires_in: TOKEN_TTL,
  });
}
