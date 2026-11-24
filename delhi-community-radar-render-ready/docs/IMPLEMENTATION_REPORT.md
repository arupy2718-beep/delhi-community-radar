# Implementation report: phases A to D (branch `hardening-phase-abcd`, not deployed)

Baseline commit `4d443eb` = your original code. All work is on the branch; `hardening.patch` is the full diff.

## Modified / added files
- `app.py` (backend): validation, privacy tiers, AQI states, sample flags, error codes.
- `static/index.html` (frontend): copy, notices, consent, location flow, stats/AQI states, map-optional.
- `README.md`: corrected claims and data rules.
- Added: `CHANGELOG.md`, `tests/` (backend, frontend, fixtures, results), `docs/` (this file, TEST_REPORT.md, PRIORITY_PROPOSAL.md, DATABASE_MIGRATION_PLAN.md, priority_scenarios.py).
- Unchanged: `static/admin.html`, `static/theme.css`, `requirements.txt` (no new dependencies; `httpx` and `jsdom` are test-only).

## Before and after (measured)
| Behaviour | Before | After |
|---|---|---|
| Hero / meta / confirmation | "sends it to the right office", "Thanks, your report is in" | "prepares a complaint for the resident to review and submit", "Not sent yet" |
| Report with no location | Random locality (test returned Ghazipur), shown on the map | HTTP 422, nothing stored |
| `.exe` upload | Accepted (`has_photo: true`) | 415 (also disguised files, GIF, SVG, >5 MB) |
| Public `/api/reports` | 24 fields incl. full text, exact lat/lng, draft, volunteers | 15 whitelisted fields; vulnerable = generic summary + ~1 km cell |
| Counters on failure | Stay "0", only a toast | "–", error, Retry, last real values kept |
| AQI on failure | `.catch(()=>{})`, stuck on "Loading…" | Timeout, error + Retry; labelled live / stale / SIMULATED |
| Map library fails | Entire page script dies | Page works; map explains itself |
| Volunteers | Real-looking names | SAMPLE badge + "no one was contacted" |
| Emergency / consent | None | Notice in form and footer; required consent box |

## The dashboard zeros: what I can and cannot say
I could **not** reproduce zeros with the backend (it returns 16/14/2/4). In jsdom, when the Leaflet script is unavailable, the **original** page reproduces your exact live symptoms (counters 0, "AI · …", AQI "Loading…") because `L.map()` throws and stops the whole script. That is a plausible cause, **not proven for your live site**. To confirm: open the live site, DevTools > Console, and look for `L is not defined` or a failed `unpkg.com` request, plus the Network tab for `/api/stats`.

## Remaining bugs / risks (not fixed: outside approved scope, or not verifiable)
1. **Priority formula flaws stand** (see proposal).
2. **Data is still in memory**: restart resets everything.
3. **Default admin password `radar-admin` still works if `ADMIN_PASSWORD` is not set on Render.** Check it today. I recommend (needs your OK) refusing to start with the default on Render.
4. **No rate limiting on `/api/report`** (AI cost/spam). Citizen-flag counting and admin lockout depend on client IP; behind Render's proxy all users may share one IP (unverified).
5. `create_report` is `async` but calls the Claude client synchronously: a slow AI call blocks every other request (timeout now capped at 25 s).
6. Only phone/e-mail/12-digit IDs are masked; **names and street addresses are not detected**, and ordinary-report summaries could contain them.
7. A report that names a different place than the user's location is flagged for admins only (`location_mismatch`); users reporting remote problems from home get their own location.
8. Image check is signature-based; a valid image with a hidden appended payload would pass. It is never saved, served or executed; decoding/re-encoding would need Pillow.
9. Leaflet, fonts load from third-party CDNs without integrity hashes.
10. A vulnerable report alone in a ~1 km cell is still locatable to that area; k-anonymity is not enforced.
11. Hero headline wording ("Prioritise. Prepare.") and your tagline "Reach the right help" are my/your choices: the tagline is slightly stronger than what the app does (it suggests help, it doesn't reach it).

## Is it ready for another evaluation?
**Honest answer: closer, not "fully ready".** What it can now truthfully claim: drafts not sends, sample data labelled, AQI source and fallbacks labelled, vulnerable data protected in the public API, location/upload validation. What the tests do not support yet: behaviour in a real browser/phone and on Render (nothing was deployed or run in a real browser), real Claude and Open-Meteo calls, persistence, and the priority logic. Suggested before the evaluation: (1) deploy to a **test** Render service and run the NOT TESTED items on a phone, (2) verify `ADMIN_PASSWORD`, (3) approve a priority approach, (4) if time allows, the database.
