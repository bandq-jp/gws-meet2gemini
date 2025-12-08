from __future__ import annotations

import base64
import hmac
import json
import time
from dataclasses import dataclass
from hashlib import sha256
from typing import Any, Dict


class MarketingTokenError(Exception):
    """Raised when a marketing client token cannot be decoded or validated."""


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("utf-8").rstrip("=")


def _b64decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


@dataclass
class MarketingTokenClaims:
    sub: str
    email: str
    name: str | None
    exp: int
    iat: int
    extra: Dict[str, Any] | None = None

    @classmethod
    def from_payload(cls, payload: Dict[str, Any]) -> "MarketingTokenClaims":
        payload_copy = dict(payload)
        try:
            sub = str(payload_copy.pop("sub"))
            email = str(payload_copy.pop("email"))
            name = payload_copy.pop("name", None)
            exp = int(payload_copy.pop("exp"))
            iat = int(payload_copy.pop("iat"))
            # Remaining keys are treated as additional claims
            extra = payload_copy or None
            return cls(
                sub=sub,
                email=email,
                name=name,
                exp=exp,
                iat=iat,
                extra=extra,
            )
        except KeyError as exc:
            raise MarketingTokenError(f"Missing required claim: {exc}") from exc


class MarketingTokenService:
    """Signs and verifies HMAC-based JWT tokens for marketing chat access."""

    def __init__(self, secret: str):
        if not secret:
            raise ValueError("MARKETING_CHATKIT_TOKEN_SECRET is not configured")
        self._secret = secret.encode("utf-8")

    def sign(self, payload: Dict[str, Any]) -> str:
        header = {"alg": "HS256", "typ": "JWT"}
        header_str = _b64encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
        payload_str = _b64encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
        signing_input = f"{header_str}.{payload_str}".encode("utf-8")
        signature = hmac.new(self._secret, signing_input, sha256).digest()
        return f"{header_str}.{payload_str}.{_b64encode(signature)}"

    def verify(self, token: str) -> MarketingTokenClaims:
        try:
            header_b64, payload_b64, signature_b64 = token.split(".")
        except ValueError as exc:
            raise MarketingTokenError("Invalid token format") from exc

        signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
        expected_sig = hmac.new(self._secret, signing_input, sha256).digest()
        provided_sig = _b64decode(signature_b64)
        if not hmac.compare_digest(expected_sig, provided_sig):
            raise MarketingTokenError("Invalid token signature")

        header = json.loads(_b64decode(header_b64))
        if header.get("alg") != "HS256":
            raise MarketingTokenError("Unsupported signing algorithm")

        payload = json.loads(_b64decode(payload_b64))
        claims = MarketingTokenClaims.from_payload(payload)
        now = int(time.time())
        if claims.exp < now:
            raise MarketingTokenError("Token expired")
        if claims.iat > now + 60:
            # Basic clock skew guard
            raise MarketingTokenError("Token not yet valid")
        return claims
