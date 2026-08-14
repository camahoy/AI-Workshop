"""Best-effort redundant backup of survey responses to a Google Sheet via
an Apps Script Web App webhook (see README for setup).

This exists because Streamlit Community Cloud's local disk — where
survey_responses.db normally lives — is not guaranteed to survive an app
restart, reboot, or sleep/wake cycle. The webhook gives every submission
a copy that lives entirely outside that container, on Google's own
infrastructure, the instant it's submitted.

Deliberately best-effort and non-blocking: if the webhook is unset or the
request fails, the survey submission itself must still succeed — this is
a backup path, not the primary write path, and a network hiccup here
should never cost someone their answers.
"""
import requests
import streamlit as st

TIMEOUT_SECONDS = 8


def send(payload: dict) -> tuple[bool, str]:
    """POSTs a JSON payload to the configured webhook. Returns (ok,
    message) — never raises, so callers can log/display the result
    without needing their own try/except."""
    url = st.secrets.get("SHEETS_WEBHOOK_URL")
    if not url:
        return False, "SHEETS_WEBHOOK_URL not configured in secrets"
    try:
        resp = requests.post(url, json=payload, timeout=TIMEOUT_SECONDS)
        if resp.status_code == 200:
            return True, "ok"
        return False, f"webhook returned HTTP {resp.status_code}"
    except requests.RequestException as e:
        return False, str(e)
