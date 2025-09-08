import { auth, clerkClient, currentUser } from '@clerk/nextjs/server';
export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';
import { NextResponse } from 'next/server';

export async function GET(req: Request) {
  // Dev gating
  const IS_PROD = process.env.NODE_ENV === 'production';
  const DEV_AUTH_ENABLED = process.env.NEXT_PUBLIC_DEV_AUTH === 'true';
  if (IS_PROD || !DEV_AUTH_ENABLED) {
    return NextResponse.json({ error: 'forbidden' }, { status: 403 });
  }

  const { userId } = await auth();
  if (!userId) return NextResponse.json({ error: 'unauthorized' }, { status: 401 });

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

  const url = new URL(req.url);
  const q = url.searchParams.get('q') || undefined;
  const limit = Math.min(Number(url.searchParams.get('limit') || '20'), 100);
  const offset = Number(url.searchParams.get('offset') || '0');

  try {
    if (!process.env.CLERK_SECRET_KEY) {
      return NextResponse.json({ error: 'Clerk secret not configured (CLERK_SECRET_KEY)' }, { status: 500 });
    }
    const cc = await clerkClient();
    const list = await cc.users.getUserList({
      query: q,
      limit,
      offset,
    });

    const users = (list?.data || []).map((u) => ({
      id: u.id,
      fullName: u.fullName,
      imageUrl: u.imageUrl,
      emails: (u.emailAddresses || []).map((e) => e.emailAddress),
      createdAt: (u.createdAt as any) ?? undefined,
    }));

    return NextResponse.json({ users, totalCount: list?.totalCount ?? users.length });
  } catch (err: unknown) {
    console.error('[dev/users] failed:', err);
    const message = err instanceof Error ? err.message : String(err);
    return NextResponse.json({ error: 'internal error', details: message }, { status: 500 });
  }
}
