"""Signed pre-auth signup-intent cookie (ADR-0013).

Role/DOB/ToS are chosen *before* Clerk account creation — including before the
OAuth redirect — so they must survive a round-trip without a session. The intent
is validated by POST /auth/signup-intent and stored in an HMAC-signed, HttpOnly
cookie (`pending_signup`). POST /auth/complete-signup verifies and consumes it.

Format: base64url(json_payload) + "." + hex(hmac_sha256(secret_key, b64)).
Payload keys: role, dob (YYYY-MM-DD | None), tos (bool), parent_email (str | None), exp (unix ts).
"""

import base64
import hashlib
import hmac
import json
import time
from datetime import date
from typing import Optional

from src.config import settings

COOKIE_NAME = "pending_signup"

SELF_SERVE_ROLES = ("student", "teacher", "parent")  # admin/school are never self-assignable


def _sign(b64_payload: str) -> str:
    return hmac.new(
        settings.secret_key.encode(), b64_payload.encode(), hashlib.sha256
    ).hexdigest()


def create_intent_cookie(
    role: str,
    dob: Optional[date] = None,
    tos_accepted: bool = False,
    parent_email: Optional[str] = None,
) -> str:
    payload = {
        "role": role,
        "dob": dob.isoformat() if dob else None,
        "tos": tos_accepted,
        "parent_email": parent_email,
        "exp": int(time.time()) + settings.signup_intent_ttl_seconds,
    }
    b64 = base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode()).decode()
    return f"{b64}.{_sign(b64)}"


def verify_intent_cookie(value: str | None) -> Optional[dict]:
    """Return the payload dict, or None if missing/tampered/expired."""
    if not value or "." not in value:
        return None
    b64, sig = value.rsplit(".", 1)
    if not hmac.compare_digest(_sign(b64), sig):
        return None
    try:
        payload = json.loads(base64.urlsafe_b64decode(b64.encode()))
    except (ValueError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict) or payload.get("exp", 0) < time.time():
        return None
    if payload.get("role") not in SELF_SERVE_ROLES:
        return None
    return payload


def age_on(dob: date, today: date) -> int:
    """Age in whole years at `today` (server-side; never trust client math)."""
    years = today.year - dob.year
    if (today.month, today.day) < (dob.month, dob.day):
        years -= 1
    return years
