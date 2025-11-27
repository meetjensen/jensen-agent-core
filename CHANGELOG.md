# Jensen Agent — Changelog

All notable changes to this project will be documented here.

## [1.2.1] — 2025-10-18
### Added
- Home route `/` with links to `/health`, `/version`, `/docs`.
- TROUBLESHOOTING.md, RUNBOOK.md, API.md, BACKUP_RESTORE.md, README.md.

### Fixed
- Pinned dependencies for stability: `fastapi==0.115.0`, `httpx==0.27.2`.
- Compose mounts and `.env` handling; removed stray heredoc markers.
- Reverse proxy CORS configuration.

### Changed
- Dockerfile command: `uvicorn main:app --host 0.0.0.0 --port 8000`.

---

## [1.2.0] — 2025-10-17
### Added
- Auth via `X-Agent-Token` header.
- Rate limiting & CORS support.

### Fixed
- Health/version endpoint responses.

---

## Versioning
We follow semantic-ish versioning: `MAJOR.MINOR.PATCH`. When bumping versions, update:
- `app/main.py` version constant
- `README.md` & `API.md` headers
- `CHANGELOG.md`

2025-10-26T16:07:47-07:00  v1.6.0 locked
