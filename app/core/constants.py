"""Shared constants: disclaimer (NFR-11), alert retention (NFR-09), URL prefix."""

API_PREFIX = "/api"

DISCLAIMER = (
    "Adverse event reports are voluntary and unverified. "
    "They show a statistical signal, not proof that a drug caused a reaction."
)

ALERT_TTL_DAYS = 30
ALERT_TTL_SECONDS = ALERT_TTL_DAYS * 24 * 3600
