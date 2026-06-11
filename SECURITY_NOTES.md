# Security Notes

## Secret Handling Policy

- Real secrets must live only in local ignored files or hosted secret managers.
- Commit only example env files.
- Backend-only secrets must not use the `VITE_` prefix.
- Frontend `VITE_*` values are public after build.

## Frontend Env Warning

Do not put Hugging Face, RapidAPI, YouTube, Reddit, Stocktwits, database, or password values in frontend env files. `VITE_*` is visible in browser JavaScript.

## Backend-Only Key Handling

- `HF_API_KEY` is backend-only.
- `HF_MODEL_ID` is backend-only configuration.
- Provider keys such as `RAPIDAPI_KEY` and `YOUTUBE_API_KEY` belong in `backend/.env` or deployment secret settings.

## Evidence Provider And Cache Policy

- Evidence providers must never return or log raw API keys.
- Provider status endpoints expose configured/unconfigured state, not secret values.
- The in-memory evidence cache stores only derived evidence objects, provider status metadata, timestamps, and provenance.
- Do not cache user-sensitive data or credentials.
- Live mode must not silently substitute synthetic evidence unless `ALLOW_LIVE_MODE_DEMO_FALLBACK=true`.
- Provider runtime metrics store counts, timing, circuit state, and redacted error messages only.
- Manual refresh is unauthenticated in this local prototype and must be protected before production use.
- Background refresh logs must not include provider secrets or raw credential values.

## Git History Exposure Warning

A Hugging Face-style token existed in tracked backend source history. Current source no longer contains it, but Git history still needs cleanup before publishing.

## Secret Rotation Required

Rotate exposed key immediately.

Use BFG Repo-Cleaner or `git filter-repo` to purge the old secret from history before publishing. Force-push only if you understand the consequences and collaborators are informed.

Example guidance:

```bash
# Example only. Review carefully before running.
git filter-repo --replace-text replacements.txt
```

or use BFG Repo-Cleaner with a secrets file. After purging, rotate the provider key anyway.

## Secret Rotation Checklist

- Revoke the exposed Hugging Face token.
- Create a new Hugging Face token if needed.
- Update only backend secret storage.
- Confirm no `hf_` tokens exist in current tree.
- Purge Git history before public sharing.
- Re-clone after history rewrite to verify.

## What Not To Commit

```text
.env
.env.*
backend/.env
backend/.env.*
backend/data/*.db
backend/data/*.sqlite
backend/data/*.sqlite3
node_modules/
dist/
build/
.venv/
venv/
backend/.venv/
__pycache__/
*.pyc
*.log
.pytest_cache/
coverage/
```
