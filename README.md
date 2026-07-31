# Kino Bot — Production-Ready Telegram Movie Delivery Bot

A Clean-Architecture Telegram bot that delivers movies/series/any media by a
short numeric code, backed by SQLAlchemy + SQLite (swappable to PostgreSQL
with a single environment variable), Alembic migrations, an in-bot admin
panel, force-subscribe, broadcast, backups, and full audit logging.

## Architecture

```
src/
├── config/        Pydantic Settings (all config from environment variables)
├── database/      Async engine/session lifecycle, declarative Base
├── models/        SQLAlchemy ORM models (7 tables)
├── repositories/  Repository Pattern — all SQL lives here, nowhere else
├── services/      Service Layer — business rules, transaction boundaries
├── middlewares/   DI injection, rate limiting, activity tracking, error handling
├── filters/       aiogram filters (admin/owner/movie-code)
├── states/        FSM state groups
├── keyboards/     Reply & inline keyboards, typed callback data
├── handlers/      Presentation layer — user/ and admin/ routers
├── scheduler/     APScheduler jobs (auto-backup, log housekeeping)
├── web/           aiohttp app — /health endpoint + optional webhook receiver
├── utils/         Cross-cutting helpers (validation, logging, retry, etc.)
└── main.py        Composition root / entrypoint

alembic/           Database migrations (Alembic)
tests/             pytest + pytest-asyncio test suite
```

Data flow for the core feature is strictly layered:
`Handler -> Service -> Repository -> SQLAlchemy -> SQLite/PostgreSQL`.
Handlers never touch the database or `bot.send_*` file semantics directly
beyond calling into a service; services never write raw SQL; repositories are
the only place that talks to SQLAlchemy Core/ORM.

## How movie delivery works

1. User sends a code, e.g. `1055`.
2. `MovieCodeFilter` recognizes the message as a code candidate.
3. Handler validates the code, checks the user isn't banned/muted, and checks
   force-subscribe requirements.
4. `MovieService.get_by_code` loads the row from the `movies` table.
5. The handler calls the matching `bot.send_<type>` method
   (`send_video`, `send_document`, `send_audio`, `send_photo`,
   `send_animation`) passing the **stored `telegram_file_id` directly** — the
   media is never re-downloaded or re-uploaded.
6. Views/downloads counters and the user's "movies received" counter are
   incremented, and the action is written to the audit log.

## Tech stack

- Python 3.13, Aiogram 3.x, SQLAlchemy 2.0 (async), aiosqlite, Alembic
- APScheduler for background jobs, aiohttp for the health/webhook server
- structlog for structured JSON-capable logging
- Optional Redis URL is accepted in config for future caching use

## Local setup

```bash
python3.13 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env   # fill in BOT_TOKEN, OWNER_ID, SECRET_KEY at minimum
alembic upgrade head
python -m src.main
```

Run the test suite:

```bash
pytest
```

## Configuration (`.env`)

Every configurable value is read from the environment — nothing is
hardcoded. See `.env.example` for the full list. Key variables:

| Variable | Purpose |
|---|---|
| `BOT_TOKEN` | Telegram Bot API token |
| `OWNER_ID` | Telegram ID of the bot owner (highest RBAC role) |
| `ADMINS` | Comma-separated extra admin Telegram IDs |
| `DATABASE_URL` | SQLAlchemy URL. Default: `sqlite+aiosqlite:////data/database.sqlite3` |
| `SECRET_KEY` | Used for signing/validating sensitive tokens |
| `USE_WEBHOOK` / `WEBHOOK_URL` / `WEBHOOK_SECRET` | Webhook mode toggle |
| `HOST` / `PORT` | aiohttp bind address (Railway injects `PORT`) |
| `FORCE_SUB_CHANNELS` | Comma-separated `@username` or chat id seed list |
| `RATE_LIMIT` | Minimum seconds between messages per user |
| `BACKUP_PATH` / `LOGS_PATH` | Railway Volume paths for backups/logs |

### Switching from SQLite to PostgreSQL

Change one variable:

```env
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/kino_bot
```

No code changes are required — the engine, pooling strategy, and Alembic
configuration all branch on the URL scheme automatically.

## Deploying to Railway

1. **Push to GitHub.** Railway builds directly from the repository using the
   included `Dockerfile`.
2. **Create a new Railway project** from the GitHub repo.
3. **Attach a Volume** mounted at `/data`. This is where the SQLite database
   file, backups, and logs live, so they survive every redeploy/restart.
4. **Set environment variables** in the Railway dashboard (mirror
   `.env.example`). At minimum: `BOT_TOKEN`, `OWNER_ID`, `SECRET_KEY`.
   Leave `DATABASE_URL` at its default to keep using the SQLite Volume path,
   or point it at a Railway PostgreSQL plugin's connection string.
5. **Deploy.** Railway sets `PORT` automatically; the app binds to
   `HOST`/`PORT` and Railway's health checks hit `GET /health`, which
   returns `200 OK` once the database connection is confirmed live.
6. **Migrations run automatically** on container start (see `Dockerfile`'s
   `CMD`, which runs `alembic upgrade head` before `python -m src.main`), so
   a fresh Volume gets its schema created with no manual step.
7. **Graceful shutdown**: the process listens for `SIGTERM`/`SIGINT`,
   stops polling/webhook delivery, shuts the scheduler down, closes the bot
   session, and disposes the database engine before exiting — Railway
   restarts never leave partial writes or orphaned connections.

### Updating the bot

Push new commits to the tracked branch; Railway rebuilds and redeploys the
container. Because the database, backups, and logs all live on the attached
Volume (not in the container filesystem), an update never loses users,
movies, statistics, settings, or backup history — only the container image
is replaced.

### Backup & restore

- **Automatic**: a daily APScheduler job (03:00 in `TIMEZONE`) copies the
  live SQLite file into `/data/backups/`, keeping the most recent 14 backups.
- **Manual (admin panel)**: *Admin → Backup* creates a fresh backup on
  demand and sends the file to the admin in chat.
- **Restore**: upload a previously created backup file to the bot with the
  caption `/restore` while logged in as an admin. The bot validates and
  swaps in the uploaded database file.

### Monitoring

- `GET /health` — used by Railway's health check; returns `503` if the
  database is unreachable so Railway can restart the container.
- *Admin → Server Info* — process/runtime summary from inside Telegram.
- *Admin → Logs* — the most recent audit log entries (who / when / what).
- Application logs are written as daily-rotated files under `LOGS_PATH`
  (`/data/logs` on Railway) in addition to stdout, which Railway captures in
  its own log viewer.

## What's implemented vs. roadmap

The original specification requested an extremely large admin feature list.
Everything below is **fully implemented and working**, not a placeholder:

- Movie lookup-by-code delivery for all supported media types via stored
  `file_id` (no re-upload), with views/downloads/received-count tracking.
- Movie CRUD: add (with duplicate `file_id` detection), edit fields, delete
  (with confirmation), activate/deactivate, code replace, caption replace.
- Bulk upload (auto-index every media message sent to the bot until `/done`).
- Search: by code, title, genre, year, language (user-facing and admin).
- Media source (channel/group) management: add / remove / list.
- Force-subscribe: add / remove / toggle any number of channels; checked
  before every delivery, with a "I've subscribed" recheck button.
- User management: search, ban/unban, mute/unmute, grant/revoke premium,
  referral tracking and invite counts.
- Admin/owner management: add/remove admins with `owner` / `admin` /
  `moderator` roles (RBAC), owner-only admin management commands.
- Broadcast: text/photo/video/animation/document/audio, forward or copy,
  one optional inline button (URL), confirmation step, per-user failure
  logging, sent/failed counters.
- Statistics dashboard: today/yesterday/weekly/monthly/total/active users,
  premium count, top codes/movies by views and downloads.
- Backup/restore/auto-backup, and a full audit log (`ActionLog`) recording
  actor, action, old/new values for every state-changing admin action.
- Security: sliding-window rate limiting, RBAC filters, input validation on
  every FSM step, centralized exception handling with a typed exception
  hierarchy, SQL-injection-safe (parameterized) queries only, and a
  duplicate-request/replay-protection middleware keyed on Telegram
  `update_id`.
- **Professional multi-platform force-subscribe center**: unlimited
  Telegram Channel/Group/Discussion Group/Bot plus Instagram/YouTube/
  TikTok/Facebook/X/Website targets, each independently Aktiv/Noaktiv and
  Majburiy/Ixtiyoriy. Telegram targets are auto-verified via
  `get_chat_member` (30s cache); non-Telegram targets use a "Tasdiqlash"
  confirmation button plus admin-provided instructions. Enforced on every
  `/start` and every movie-code request; a user with an outstanding
  mandatory subscription cannot use any other function until they clear it.
- **Movie visibility rules**: Public / Hidden / VIP / Premium / Admin-only /
  Subscriber-only / Referral-only, enforced at delivery time.
- **Media Center**: preview (with a live broken-file check), duplicate
  detection (by `file_id`), broken-file detection, CSV export/import, most-
  and least-viewed listings, all reachable from the admin panel.
- **Kod boshqaruvi (code management)**: random/sequential code generation,
  explicit code reservation (`/reserve`, `/release`) that blocks conflicting
  creates from other admins, and duplicate/conflict detection on every
  create.
- **Media Queue**: drop a video/document/audio/animation straight into a
  configured source group and the bot auto-captures its `file_id` and asks
  the admin for a code — no manual `file_id` copying required.
- **Real-time Dashboard**: CPU/RAM/disk, DB size, media count, today/
  yesterday/online users, bot ping, average response time, requests/sec,
  error count, uptime, backup status — all in one admin screen.
- **Extended user history**: per-user start count, spam score, warnings,
  notes, admin remarks, verification flag, in addition to the existing
  searches/received-movies/referral/premium/ban tracking.
- Every hot lookup (`movie.code`, force-sub membership) is backed by a
  dependency-free async-safe in-process `TTLCache`, keeping the common-case
  code lookup and force-sub check O(1) with no extra DB round-trip.

**Documented as roadmap, intentionally not built to avoid destructive or
fake functionality:**

- *Bulk delete* is implemented as a guided "search then delete" flow rather
  than a single irreversible mass-delete action, to prevent an admin from
  accidentally wiping the catalogue with one tap.
- *Database export/import* as a portable, cross-backend format (the backup
  system already gives full SQLite-file-level backup/restore; a schema-level
  export/import for migrating between SQLite and PostgreSQL is a larger,
  separate feature). Movie catalogue CSV export/import (Media Center) is
  implemented; Excel/JSON export and full-database Excel/JSON export are not.
- *Cache clearing* / Redis-backed caching: `REDIS_URL` is accepted in config
  for forward-compatibility; hot-path caching is implemented via an
  in-process `TTLCache`, not Redis yet.
- Admin Manager beyond the existing owner/admin/moderator RBAC — additional
  named roles (Super Admin/Developer/Support/Uploader/Analyst), login
  history, 2FA, API keys, and session management are not implemented.
- Broadcast beyond text/photo/video/animation/document/audio with one URL
  button — album, voice, poll, quiz, multiple inline buttons, scheduling,
  drafts, and per-message retry are not implemented (retry/progress/failed-
  user tracking and success % already exist).
- Analytics beyond top movies/codes by views/downloads and the existing
  daily/weekly/monthly/total user stats — empty-search tracking, countries,
  and languages breakdowns are not implemented.
- Captcha and automated referral-fraud detection are not implemented (basic
  rate limiting + duplicate-request protection + spam-score field exist as
  building blocks).
- User export as Excel/JSON (CSV-equivalent exists via Media Center for
  movies only) and User Manager coins/tags/user-merge are not implemented.
- A locales/i18n system beyond the current Uzbek-only text (the `locales/`
  package exists for future translations).

None of the above roadmap items are faked with mock data — they are simply
not present yet, so nothing in the running bot silently no-ops or lies about
its state.

## Production-readiness checklist

- ✅ Async end-to-end, no blocking I/O on the event loop.
- ✅ SQLite via `NullPool` (safe across restarts) / PostgreSQL via a real
  pool with `pool_pre_ping` for automatic reconnect.
- ✅ Alembic migrations run automatically on container start.
- ✅ `/health` reports real database connectivity, not just "process alive".
- ✅ Signal-based graceful shutdown (stops polling, scheduler, HTTP server,
  bot session, and disposes the DB engine in order).
- ✅ Centralized error-handling middleware — no unhandled exception can
  crash the dispatcher; every known failure mode maps to a typed exception
  with a clear user-facing Uzbek message.
- ✅ No hardcoded configuration or secrets anywhere in source code.
- ✅ No `TODO` / mock / demo code paths in the implemented features above.
