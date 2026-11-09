# core - configuration and security

Cross-cutting configuration. No business logic.

## Tools used

- pydantic-settings (typed settings from `.env`)
- PyJWT (access tokens)
- bcrypt (password hashing)

## Rules

- May be imported by every layer.
- Never read `os.environ` elsewhere: use `get_settings()`.
- Secrets only in `.env`, never in git (NFR-10).

## Contents

| Item | Role |
|---|---|
| `config.py` | Settings: Mongo URI, Redis URL or Sentinels, JWT, CORS |
| `security.py` | bcrypt + JWT helpers (NFR-10) |
| `constants.py` | Disclaimer text (NFR-11), alert TTL (NFR-09) |
