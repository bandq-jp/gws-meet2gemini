"use client";

import { use } from "react";
import MarketingPage from "../page";

type Params = { threadId?: string };
type Props = { params: Promise<Params> | Params };

export default function MarketingThreadPage({ params }: Props) {
  // Next.js 15+: params is a Promise; unwrap with use()
  const resolved = typeof (params as any).then === "function" ? use(params as Promise<Params>) : (params as Params);
  return <MarketingPage initialThreadId={resolved.threadId ?? null} />;
}
