import { auth, clerkClient, currentUser } from '@clerk/nextjs/server';
export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';
import { NextResponse } from 'next/server';

type Body = {
  targetUserId?: string;
  email?: string;
  mode?: 'ticket' | 'impersonation';
  expiresInSeconds?: number;
};

export async function POST(req: Request) {
  // Dev gating
  const IS_PROD = process.env.NODE_ENV === 'production';
  const DEV_AUTH_ENABLED = process.env.NEXT_PUBLIC_DEV_AUTH === 'true';
  if (IS_PROD || !DEV_AUTH_ENABLED) {
    return NextResponse.json({ error: 'forbidden' }, { status: 403 });
  }

  const { userId: impersonatorUserId } = await auth();
  if (!impersonatorUserId) {
    return NextResponse.json({ error: 'unauthorized' }, { status: 401 });
  }

  // Optional: simple allowlist by domain or env
  const me = await currentUser();
  const allowedEmails = (process.env.DEV_ALLOWED_IMPERSONATORS || '')
    .split(',')
    .map((s) => s.trim())
    .filter(Boolean);
  const allowedDomains = (process.env.ALLOWED_EMAIL_DOMAINS || '@bandq.jp')
    .split(',')
    .map((s) => s.trim());

  const myEmails = me?.emailAddresses?.map((e) => e.emailAddress) || [];
  const isAllowed =
    allowedEmails.length > 0
      ? myEmails.some((e) => allowedEmails.includes(e))
      : myEmails.some((e) => allowedDomains.some((d) => e.endsWith(d)));

  if (!isAllowed) {
    return NextResponse.json({ error: 'access denied' }, { status: 403 });
  }

  const body = (await req.json()) as Body;
  let { targetUserId, email, mode = 'ticket', expiresInSeconds } = body;

  if (!targetUserId && !email) {
    return NextResponse.json(
      { error: 'targetUserId or email is required' },
      { status: 400 }
    );
  }

  try {
    if (!process.env.CLERK_SECRET_KEY) {
      return NextResponse.json({ error: 'Clerk secret not configured (CLERK_SECRET_KEY)' }, { status: 500 });
    }
    // Resolve by email if needed
    if (!targetUserId && email) {
      const list = await clerkClient.users.getUserList({ emailAddress: [email] });
      const found = list?.data?.[0];
      if (!found) {
        return NextResponse.json({ error: 'user not found' }, { status: 404 });
      }
      targetUserId = found.id;
    }

    if (!targetUserId) {
      return NextResponse.json(
        { error: 'failed to resolve targetUserId' },
        { status: 400 }
      );
    }

    // Create either a ticket (sign-in token) or an impersonation session
    const cc = await clerkClient();
    if (mode === 'impersonation') {
      // Not supported in this SDK version; fall back or reject explicitly
      return NextResponse.json({ error: 'impersonation mode not supported via API; use ticket' }, { status: 400 });
    } else {
      const tokenResp = await cc.signInTokens.createSignInToken({
        userId: targetUserId,
        expiresInSeconds: Math.max(30, Math.min(expiresInSeconds ?? 300, 300)),
      });
      return NextResponse.json({ token: tokenResp.token, url: tokenResp.url, mode });
    }
  } catch (err: unknown) {
    console.error('[dev/impersonate] failed:', err);
    const message = err instanceof Error ? err.message : String(err);
    return NextResponse.json({ error: 'internal error', details: message }, { status: 500 });
  }
}
