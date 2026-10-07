"""Facilitator access.

Admin controls (Export, Reset board, Summary, session settings) appear only
after the facilitator passphrase from Streamlit secrets is entered — never
from a URL flag. If FACILITATOR_PASSWORD isn't set, no one gets admin
controls at all (fail closed).

The browser keeps a cookie so the facilitator stays logged in across
refreshes. The cookie holds an HMAC of the passphrase, not a plain "1": it
can't be forged by setting a cookie by hand, and changing the passphrase
logs every device out.
"""
import hashlib
import hmac

import streamlit as st

COOKIE = "workshop_facilitator"
COOKIE_MAX_AGE = 60 * 60 * 24  # one day


def passphrase() -> str | None:
    try:
        return st.secrets.get("FACILITATOR_PASSWORD") or None
    except Exception:
        return None


def _token(pw: str) -> str:
    return hmac.new(pw.encode(), b"field-notes-facilitator-v2", hashlib.sha256).hexdigest()


def check(entered: str) -> bool:
    pw = passphrase()
    return bool(pw) and hmac.compare_digest(entered or "", pw)


def is_facilitator(cookie_value) -> bool:
    # The cookie library JSON-decodes values, so the old app's "1" cookie
    # arrives as the int 1 — anything that isn't a string is simply not a token.
    pw = passphrase()
    if not pw or not isinstance(cookie_value, str):
        return False
    return hmac.compare_digest(cookie_value, _token(pw))


def login(cookies) -> None:
    cookies.set(COOKIE, _token(passphrase()), max_age=COOKIE_MAX_AGE)


def logout(cookies) -> None:
    cookies.remove(COOKIE)
