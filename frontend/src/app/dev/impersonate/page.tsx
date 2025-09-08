"use client";

import { useEffect, useMemo, useState } from 'react';
import { useClerk, useSignIn, useUser, useAuth } from '@clerk/nextjs';
import { useRouter, useSearchParams } from 'next/navigation';
import toast from 'react-hot-toast';

const DEV_AUTH_ENABLED = process.env.NEXT_PUBLIC_DEV_AUTH === 'true';

export default function DevImpersonatePage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user } = useUser();
  const { userId: currentUserId } = useAuth();
  const { signIn, isLoaded: signInLoaded } = useSignIn();
  const { setActive, signOut } = useClerk();

  const [identifier, setIdentifier] = useState(''); // userId or email
  const [identifierType, setIdentifierType] = useState<'userId' | 'email'>('userId');
  const mode: 'ticket' = 'ticket';
  const [working, setWorking] = useState(false);
  const [q, setQ] = useState('');
  const [loadingUsers, setLoadingUsers] = useState(false);
  const [users, setUsers] = useState<{ id: string; fullName?: string | null; imageUrl?: string; emails: string[] }[]>([]);

  const currentEmail = useMemo(() => user?.emailAddresses?.[0]?.emailAddress ?? '', [user]);

  if (!DEV_AUTH_ENABLED) {
    return (
      <div className="p-6">
        <h1 className="text-xl font-semibold">Dev Impersonation</h1>
        <p className="mt-2 text-sm text-muted-foreground">NEXT_PUBLIC_DEV_AUTH is not enabled.</p>
      </div>
    );
  }

  const fetchUsers = async () => {
    setLoadingUsers(true);
    try {
      const res = await fetch(`/api/dev/users${q ? `?q=${encodeURIComponent(q)}` : ''}`, { cache: 'no-store' });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data?.error || `request failed: ${res.status}`);
      }
      const data = await res.json();
      setUsers(data.users || []);
    } catch (e: any) {
      toast.error(e?.message || 'failed to load users');
    } finally {
      setLoadingUsers(false);
    }
  };

  const getTicket = async (payload: any) => {
    const res = await fetch('/api/dev/impersonate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      const details = data?.details ? `: ${data.details}` : '';
      throw new Error((data?.error || `request failed: ${res.status}`) + details);
    }
    const data = await res.json();
    return data.token as string;
  };

  const signInWithTicket = async (ticket: string) => {
    if (!signInLoaded) throw new Error('signIn is not loaded');
    const result = await signIn.create({ strategy: 'ticket', ticket });
    if (!result?.createdSessionId) throw new Error('ticket sign-in failed');
    await setActive({ session: result.createdSessionId });
    toast.success('Switched via ticket');
  };

  const submit = async () => {
    if (!identifier) {
      toast.error('Enter a target userId or email');
      return;
    }
    setWorking(true);
    try {
      const token = await getTicket({ mode, [identifierType === 'userId' ? 'targetUserId' : 'email']: identifier });
      if (currentUserId) {
        const ticket = encodeURIComponent(token);
        await signOut({ redirectUrl: `/dev/impersonate?ticket=${ticket}` });
        return;
      }
      await signInWithTicket(token);
    } catch (e: any) {
      toast.error(e?.message || 'failed');
    } finally {
      setWorking(false);
    }
  };

  const switchTo = async (targetUserId: string) => {
    setWorking(true);
    try {
      const token = await getTicket({ mode, targetUserId });
      if (currentUserId) {
        const ticket = encodeURIComponent(token);
        await signOut({ redirectUrl: `/dev/impersonate?ticket=${ticket}` });
        return;
      }
      await signInWithTicket(token);
      toast.success(`Switched to ${targetUserId}`);
    } catch (e: any) {
      toast.error(e?.message || 'failed');
    } finally {
      setWorking(false);
    }
  };

  useEffect(() => {
    if (DEV_AUTH_ENABLED) fetchUsers();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Auto sign-in when redirected back with ticket and no active session
  useEffect(() => {
    const ticket = searchParams?.get('ticket');
    if (!ticket) return;
    if (currentUserId) return; // already signed in
    if (!signInLoaded) return;
    (async () => {
      try {
        await signInWithTicket(ticket);
        router.replace('/dev/impersonate');
      } catch (err: any) {
        const clerkErrors = err?.errors?.map((e: any) => e?.longMessage || e?.message).join('\n');
        toast.error(clerkErrors || err?.message || 'ticket sign-in failed');
      }
    })();
  }, [searchParams, currentUserId, signInLoaded]);

  return (
    <div className="p-6 max-w-5xl">
      <h1 className="text-xl font-semibold">Dev Impersonation</h1>
      <p className="mt-2 text-sm text-muted-foreground">
        Sign in as another Clerk user in development.
      </p>

      <div className="mt-6 grid gap-8 md:grid-cols-2">
        <div className="text-sm">
          <div className="text-muted-foreground">Current user</div>
          <div className="font-medium">{user?.fullName || '(unknown)'}</div>
          <div className="text-muted-foreground">{currentEmail}</div>
        </div>

        <div className="grid gap-2">
          <label className="text-sm font-medium">Identifier type</label>
          <div className="flex gap-2">
            <button
              className={`px-3 py-1 rounded border ${identifierType === 'userId' ? 'bg-primary text-primary-foreground' : ''}`}
              onClick={() => setIdentifierType('userId')}
            >
              userId
            </button>
            <button
              className={`px-3 py-1 rounded border ${identifierType === 'email' ? 'bg-primary text-primary-foreground' : ''}`}
              onClick={() => setIdentifierType('email')}
            >
              email
            </button>
          </div>
        </div>

        <div className="grid gap-2">
          <label className="text-sm font-medium">
            {identifierType === 'userId' ? 'Target Clerk userId' : 'Target email address'}
          </label>
          <input
            className="border rounded px-3 py-2 text-sm"
            placeholder={identifierType === 'userId' ? 'user_...' : 'user@example.com'}
            value={identifier}
            onChange={(e) => setIdentifier(e.target.value)}
          />
        </div>

        <div className="grid gap-1">
          <div className="text-sm font-medium">Mode</div>
          <div className="text-xs text-muted-foreground">ticket only (impersonation via API is not supported in this setup)</div>
        </div>

        <div className="flex gap-3">
          <button
            onClick={submit}
            disabled={working}
            className="px-4 py-2 rounded bg-primary text-primary-foreground text-sm"
          >
            {working ? 'Switching...' : 'Switch session'}
          </button>
          <button
            onClick={() => signOut({ redirectUrl: '/dev/impersonate' })}
            className="px-4 py-2 rounded border text-sm"
          >
            Sign out
          </button>
        </div>
      </div>

      <div className="mt-10">
        <div className="flex items-end gap-2">
          <div className="grid flex-1 gap-2">
            <label className="text-sm font-medium">Search users</label>
            <input
              className="border rounded px-3 py-2 text-sm"
              placeholder="name or email"
              value={q}
              onChange={(e) => setQ(e.target.value)}
            />
          </div>
          <button
            onClick={fetchUsers}
            className="px-4 py-2 rounded border text-sm mt-6"
            disabled={loadingUsers}
          >
            {loadingUsers ? 'Loading...' : 'Search'}
          </button>
        </div>

        <div className="mt-4 border rounded">
          <div className="grid grid-cols-1 divide-y">
            {users.length === 0 && (
              <div className="p-4 text-sm text-muted-foreground">No users</div>
            )}
            {users.map((u) => (
              <div key={u.id} className="flex items-center justify-between gap-4 p-3">
                <div className="flex items-center gap-3 min-w-0">
                  {u.imageUrl ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img src={u.imageUrl} alt={u.fullName || u.id} className="h-8 w-8 rounded" />
                  ) : (
                    <div className="h-8 w-8 rounded bg-muted" />)
                  }
                  <div className="min-w-0">
                    <div className="font-medium truncate max-w-[28rem]">{u.fullName || '(no name)'}</div>
                    <div className="text-xs text-muted-foreground truncate max-w-[28rem]">{u.emails[0] || '-'}</div>
                    <div className="text-[11px] text-muted-foreground/70">{u.id}</div>
                  </div>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <button
                    onClick={() => switchTo(u.id)}
                    disabled={working}
                    className="px-3 py-1.5 rounded bg-primary text-primary-foreground text-xs"
                  >
                    Sign in as (ticket)
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

