"use client";

import { use } from "react";
import ImageGenPage from "../page";

type Params = { sessionId?: string };
type Props = { params: Promise<Params> | Params };

export default function ImageGenSessionPage({ params }: Props) {
  const resolved =
    typeof (params as Promise<Params>).then === "function"
      ? use(params as Promise<Params>)
      : (params as Params);

  return <ImageGenPage initialSessionId={resolved.sessionId ?? null} />;
}
