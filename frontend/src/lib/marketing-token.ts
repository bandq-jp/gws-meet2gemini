import crypto from "crypto";

type TokenPayload = {
  sub: string;
  email: string;
  name?: string | null;
  exp: number;
  iat: number;
};

const header = {
  alg: "HS256",
  typ: "JWT",
};

function base64UrlEncode(value: Buffer | string) {
  return Buffer.isBuffer(value)
    ? value.toString("base64url")
    : Buffer.from(value).toString("base64url");
}

function base64UrlDecode<T = unknown>(value: string): T {
  return JSON.parse(Buffer.from(value, "base64url").toString("utf-8")) as T;
}

export function signMarketingToken(
  payload: TokenPayload,
  secret: string
): string {
  if (!secret) {
    throw new Error("MARKETING_CHATKIT_TOKEN_SECRET is not configured");
  }
  const encodedHeader = base64UrlEncode(JSON.stringify(header));
  const encodedPayload = base64UrlEncode(JSON.stringify(payload));
  const signingInput = `${encodedHeader}.${encodedPayload}`;
  const signature = crypto
    .createHmac("sha256", secret)
    .update(signingInput)
    .digest("base64url");
  return `${signingInput}.${signature}`;
}

export function verifyMarketingToken(
  token: string,
  secret: string
): TokenPayload {
  if (!secret) {
    throw new Error("MARKETING_CHATKIT_TOKEN_SECRET is not configured");
  }
  const [encodedHeader, encodedPayload, encodedSignature] = token.split(".");
  if (!encodedHeader || !encodedPayload || !encodedSignature) {
    throw new Error("Invalid client secret");
  }
  const expectedSignature = crypto
    .createHmac("sha256", secret)
    .update(`${encodedHeader}.${encodedPayload}`)
    .digest("base64url");
  if (!crypto.timingSafeEqual(Buffer.from(expectedSignature), Buffer.from(encodedSignature))) {
    throw new Error("Invalid signature");
  }
  const decodedHeader = base64UrlDecode<typeof header>(encodedHeader);
  if (decodedHeader.alg !== "HS256") {
    throw new Error("Unsupported token algorithm");
  }
  const payload = base64UrlDecode<TokenPayload>(encodedPayload);
  const now = Math.floor(Date.now() / 1000);
  if (payload.exp < now) {
    throw new Error("Client secret expired");
  }
  if (payload.iat > now + 60) {
    throw new Error("Client secret not yet valid");
  }
  return payload;
}
