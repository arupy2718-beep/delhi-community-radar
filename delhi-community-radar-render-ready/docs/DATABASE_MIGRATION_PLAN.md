# Database migration recommendation (NOT started, awaiting your approval)

Prices and limits below come from the providers' own pages and docs as found on 24 Nov 2026. They change often: **re-check before you decide.** Where sources disagreed I say so.

## Why
All state lives in Python lists (`REPORTS`, `ABUSE`, `AUDIT`, `ADMIN_TOKENS`, `FAILED`). A restart or redeploy resets reports, admin deletions, flags, the audit log and admin sessions, and the 16 sample reports are re-seeded. Render's docs say free web services cannot keep local files (only paid services can attach a persistent disk), so **SQLite on the free web service will not survive either**.

## Options
| Option | Free-tier facts | Fit |
|---|---|---|
| **Neon Postgres (free)** | Permanent free plan, no card. 100 projects; storage per project is 1 GB per Neon's Oct 2026 changelog (an older third-party article and one Neon page say 0.5 GB: check the console). Compute scales to zero after 5 min idle. Free "history window" is only 6 hours, so it is not a backup. Paid: Launch is pay-as-you-go ($0.106 per compute-hour, $0.35 per GB-month on Neon's pages) | Good: data lives outside Render, no expiry, plain Postgres |
| **Supabase Postgres (free)** | 500 MB per project, 2 active projects, **project pauses after 1 week of inactivity**, no automatic backups on free. Pro is $25/month (daily backups, 7-day retention, no pausing) | Good if kept awake or on Pro; the pause is a demo risk |
| **Render Postgres (free)** | 1 GB, **expires 30 days after creation**, 14-day grace then deleted, **no backups**, may restart/maintenance any time. Paid price: not verified here | Fine only for a short demo window created close to the evaluation; a trap for anything longer |
| SQLite file on Render free | Local files are lost (see above) | Not suitable |
| Other (Turso, Cloudflare D1, etc.) | Not evaluated | |

**Recommendation:** Postgres on **Neon** (or Supabase Pro if money allows), in an Asia region near your Render service to keep latency low, using the `psycopg` driver with plain SQL (no ORM, one new dependency). Keep the web service on Render.

## Proposed schema
`reports` (all current fields, `sample` boolean, `location_source`, `lat`, `lng`, `created_at`, `status`, `tracking_id`), `abuse_flags (report_id, ip_hash)`, `audit_log`, `admin_sessions` (or signed tokens), later `reporter_keys (hash, first_seen)` with a TTL. Seed only when the table is empty, and flag the rows `sample=true`.

## Steps and rough effort (my estimate: 1-2 focused days plus testing)
1. Create DB, store `DATABASE_URL` as a Render env var (never in git); create a **least-privilege app role** (no superuser), TLS required.
2. Add `db.py` with the few queries the app uses; keep the public/owner/admin view functions as they are.
3. Move `REPORTS`, flags and audit to tables; do cluster assignment inside a transaction (lock the cluster row) so two simultaneous submissions cannot corrupt cluster sizes.
4. Keep an in-memory fallback only for local demos, clearly labelled.
5. Re-run `tests/` against a test database; add restart-persistence and concurrent-submission tests.

## Risks
- **No real backups on any free tier.** Schedule `pg_dump` (e.g. a GitHub Actions cron) to a private location. Test a restore once.
- **Privacy:** you would be storing locations of vulnerable people in a durable database. Decide retention first (for example auto-delete after N days), keep photos out of the DB, and review DPDP Act 2023 obligations before any real pilot.
- **Cold starts:** Render free web sleeps and Neon scales to zero, so the first request after idle can be slow. Open both before judges do.
- **Latency/limits:** a remote DB adds round-trips per request; Render notes that unusually high external-service traffic can get a free service suspended (unlikely at this scale).
- **Migration mistakes:** re-seeding on every start would duplicate sample rows (guard with "seed only if empty").
- Free-tier terms change, so a plan that works today may not in a month.
