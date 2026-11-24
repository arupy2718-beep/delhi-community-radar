# Test report: phases A to D

**Result: 90 of 90 automated checks passed (52 backend, 38 frontend).** Run date 24 Nov 2026, in a Linux sandbox with **no internet** and **no Anthropic API key**.

**Read this first.** These are automated checks against the real backend code (FastAPI test client) and the real `index.html` run in **jsdom**, a simulated browser with no layout engine. Nothing was tested on the deployed Render site (nothing was deployed). External services were mocked where stated. A pass means *this code behaves as specified in this environment*, not that it is production-proven. Section 3 lists what was NOT TESTED.

## 1. Your 24 test areas to test IDs

| # | Area | Test IDs |
|---|---|---|
| 1 | Complaint-drafting messaging | F-01a F-01b F-01c F-01d F-02c |
| 2 | Sample volunteer labels | B-02 B-23b F-02a F-02b F-23 |
| 3 | Emergency notice visibility | F-03 |
| 4 | Consent notice visibility | F-04a F-04b |
| 5 | AQI loading success | F-05 B-05 |
| 6 | AQI timeout | F-06 B-06 |
| 7 | AQI API failure | F-07 B-07 |
| 8 | Simulated AQI fallback | F-08 F-08b B-08a B-08b B-08c |
| 9 | Dashboard statistics success | F-09 F-09b B-24a |
| 10 | Dashboard API failure | F-10 F-10b F-10c F-10d F-10e |
| 11 | Dashboard retry | F-11 |
| 12 | Missing location | B-12a B-12b B-12c B-12d F-12 |
| 13 | Invalid coordinates | B-13 |
| 14 | GPS permission denied | F-14 F-14b |
| 15 | Manual map selection | F-15 |
| 16 | Valid image upload | B-16jp B-16pn B-16we F-16 |
| 17 | Invalid file extension | B-17a..g F-17 |
| 18 | Disguised executable | B-18a..d |
| 19 | Oversized upload | B-19 B-19b F-19 |
| 20 | Public access to vulnerable reports | B-20a..e |
| 21 | Public map location privacy | B-21a B-21b B-21c F-21 |
| 22 | Administrator access to protected info | B-22a B-22b B-22c |
| 23 | Normal report submission | B-23a B-23b F-23 F-23c F-23d |
| 24 | Existing features still working | B-24a..f B-28 F-24 F-24x B-27* |

## 2. Every test

Evidence = the script in `tests/` that produced the actual result; raw output in `tests/results/*.json`. "Remaining" lists issues the test does not cover.

| ID | Test | Expected | Actual | Result | Evidence / remaining issue |
|---|---|---|---|---|---|
| B-24a | Seed stats unchanged | 16/14/2/4 | 16/14/2/4 | **PASS** | tests/test_backend.py |
| B-24b | All 16 seeds loaded, none skipped, all flagged sample | 16 sample | 16 sample of 16 | **PASS** | tests/test_backend.py |
| B-24c | Priority formula untouched (report's worked example = 59) | 59 | 59 | **PASS** | tests/test_backend.py |
| B-02 | Every volunteer record is marked sample (API) | all sample:true | True | **PASS** | tests/test_backend.py |
| B-12a | Missing location rejected | 422 + clear error, nothing stored | 422 {'error': "Location is required. Tap 'My location' or tap the map to set where the problem is."} | **PASS** | tests/test_backend.py |
| B-12b | Only latitude supplied rejected | 422 | 422 | **PASS** | tests/test_backend.py |
| B-13 | Invalid / non-finite / out-of-NCR coordinates rejected | all 422, nothing stored | [422, 422, 422, 422, 422, 422, 422, 422] | **PASS** | tests/test_backend.py · cases: [('999', '999'), ('abc', '77.2'), ('nan', '77.2'), ('inf', '77.2'), ('-91', '77.2'), ('28.6', '181'), ('19.07', '72.87'), ('0', '0')] |
| B-23a | Normal GPS report accepted | 200, locality from coordinates, source gps | 200 locality=Karol Bagh source=gps | **PASS** | tests/test_backend.py |
| B-23b | Owner response has draft, authority, SAMPLE volunteers; no cluster internals | volunteers all sample | [('Aarti Sharma', True), ('Seva Delhi NGO', True)] | **PASS** | tests/test_backend.py |
| B-12c | Location far from any known locality is NOT given a random locality | Other Delhi NCR | Other Delhi NCR | **PASS** | tests/test_backend.py |
| B-12d | Text-named locality never overrides coordinates; mismatch recorded for admin | locality=Okhla, hint=Ghazipur, mismatch | Okhla | **PASS** | tests/test_backend.py |
| B-27 | Over-long description rejected | 413 | 413 | **PASS** | tests/test_backend.py |
| B-09 | Phone / e-mail / 12-digit ID masked before storing | masked | Elderly neighbour Ramesh, call [phone removed] or [email removed], id [ID number removed] | **PASS** | tests/test_backend.py |
| B-27b | Empty complaint rejected | 422 | 422 | **PASS** | tests/test_backend.py |
| B-27c | Photo-only without AI key rejected with clear message | 422 | 422 Photo-only reports need AI mode. Please add a short description as well. | **PASS** | tests/test_backend.py |
| B-16jp | Valid a.jpg accepted and passed to AI path with sniffed media type | 200, media_type image/jpeg | 200, passed image/jpeg | **PASS** | tests/test_backend.py |
| B-16pn | Valid b.png accepted and passed to AI path with sniffed media type | 200, media_type image/png | 200, passed image/png | **PASS** | tests/test_backend.py |
| B-16we | Valid c.webp accepted and passed to AI path with sniffed media type | 200, media_type image/webp | 200, passed image/webp | **PASS** | tests/test_backend.py |
| B-17a | virus.exe, MIME exe | 415, nothing stored | 415 Unsupported photo. Please upload a JPG, PNG or WebP image. | **PASS** | tests/test_backend.py |
| B-17b | a.exe with image MIME | 415, nothing stored | 415 Unsupported photo. Please upload a JPG, PNG or WebP image. | **PASS** | tests/test_backend.py |
| B-17c | GIF not allowed | 415, nothing stored | 415 Unsupported photo. Please upload a JPG, PNG or WebP image. | **PASS** | tests/test_backend.py |
| B-17d | SVG (script-capable) not allowed | 415, nothing stored | 415 Unsupported photo. Please upload a JPG, PNG or WebP image. | **PASS** | tests/test_backend.py |
| B-17e | No extension | 415, nothing stored | 415 Unsupported photo. Please upload a JPG, PNG or WebP image. | **PASS** | tests/test_backend.py |
| B-17f | .html named as image MIME | 415, nothing stored | 415 Unsupported photo. Please upload a JPG, PNG or WebP image. | **PASS** | tests/test_backend.py |
| B-18a | Disguised: exe bytes named .jpg, MIME image/jpeg | 415, nothing stored | 415 That file is not a valid image of the type its name says. Please upload a JPG, PNG or WebP photo. | **PASS** | tests/test_backend.py |
| B-18b | Disguised: text/script named .png | 415, nothing stored | 415 That file is not a valid image of the type its name says. Please upload a JPG, PNG or WebP photo. | **PASS** | tests/test_backend.py |
| B-18c | Disguised: PNG bytes named .jpg | 415, nothing stored | 415 That file is not a valid image of the type its name says. Please upload a JPG, PNG or WebP photo. | **PASS** | tests/test_backend.py |
| B-18d | Disguised: ELF binary named .webp | 415, nothing stored | 415 That file is not a valid image of the type its name says. Please upload a JPG, PNG or WebP photo. | **PASS** | tests/test_backend.py |
| B-17g | Empty file | 400, nothing stored | 400 That photo is empty. Please choose another one. | **PASS** | tests/test_backend.py |
| B-19 | Oversized (>5 MB) photo rejected | 413, nothing stored | 413 That photo is too large. Photos must be 5 MB or smaller. | **PASS** | tests/test_backend.py |
| B-19b | Grossly oversized request stopped by Content-Length guard | 413 | 413 | **PASS** | tests/test_backend.py |
| B-20a | Public API exposes only whitelisted fields | no text/draft/volunteers/flag data | no extra fields | **PASS** | tests/test_backend.py |
| B-20b | No vulnerable-person wording / free text leaks anywhere in public JSON | no leaks | none | **PASS** | tests/test_backend.py |
| B-20c | Sensitive reports have generic summary + 'approximate' precision | 6 sensitive | 6 checked | **PASS** | tests/test_backend.py |
| B-21a | Sensitive public coordinates are 1-km grid-cell centres, not the stored point | coords != exact, on grid centre | 6 checked, e.g. offset 254 m | **PASS** | tests/test_backend.py |
| B-21b | Ordinary public coordinates rounded to 3 dp (~100 m) | <= 3 decimals | checked 17 | **PASS** | tests/test_backend.py |
| B-21c | Public API never lists a report without a valid location | none listed | inject + list | **PASS** | tests/test_backend.py |
| B-20d | Submitter (owner) still gets their own complaint draft and map position | draft present, map_lat generalised | draft=True map=28.655,77.195 | **PASS** | tests/test_backend.py |
| B-20e | Draft is NOT in the public list | absent | checked | **PASS** | tests/test_backend.py |
| B-22a | Public cannot read admin data | 401 | 401 | **PASS** | tests/test_backend.py |
| B-22b | Admin login failure | 401 | 401 | **PASS** | tests/test_backend.py |
| B-22c | Admin still sees full text, exact coordinates, location source, draft | all present | text=True lat=True src=gps | **PASS** | tests/test_backend.py |
| B-24d | Admin hide / approve still work and affect the public list | hide removes, approve restores | 200/True/200/True | **PASS** | tests/test_backend.py |
| B-24e | Admin delete still works | 200 and gone from store | 200 | **PASS** | tests/test_backend.py |
| B-24f | Citizen flag: 3 distinct addresses hide a report | hidden | True | **PASS** | tests/test_backend.py |
| B-28 | Offensive report is held | flagged | True | **PASS** | tests/test_backend.py |
| B-05 | AQI success: live, Open-Meteo, not CPCB, has update time | status live, simulated false | live simulated=False updated=2026-11-24T14:00 fetched_at=True | **PASS** | tests/test_backend.py |
| B-06 | AQI upstream timeout: simulated, labelled, no live claim | status simulated | simulated \| SIMULATED illustrative values. Not measurements. The live data service could not be reached. | **PASS** | tests/test_backend.py |
| B-07 | AQI upstream HTTP 500: simulated, labelled | status simulated | simulated | **PASS** | tests/test_backend.py |
| B-08a | Upstream down, 20-min-old data: shown but labelled STALE with age | status stale, age ~1200 s | stale age=1200 | **PASS** | tests/test_backend.py |
| B-08b | Upstream down, 4-hour-old data: NOT shown as current; simulated + last success time | simulated, last_success set | simulated last_success=1795502533 | **PASS** | tests/test_backend.py |
| B-08c | Real network call (sandbox has no internet) fails safely to simulated | simulated | simulated | **PASS** | tests/test_backend.py · Real Open-Meteo success path is NOT TESTED against the live service · remaining: needs internet access |
| F-01a | Misleading phrases removed from page HTML | none present | none | **PASS** | tests/test_frontend.js |
| F-01b | Hero + meta state the resident reviews and submits; nothing auto-sent | phrases present | meta ok=true; hero ok=true | **PASS** | tests/test_frontend.js |
| F-01c | Headline no longer promises "Resolve" | Report.Prioritise.Prepare. (line breaks) | Report.Prioritise.Prepare. | **PASS** | tests/test_frontend.js |
| F-01d | Routing feature kept, reworded (How-it-works) | "Suggest authority" step present | 04Suggest authorityAI identifies the relevant body (MCD, DJB, PWD, DPCC, RWA or NGO) and prepares a formal complaint dra | **PASS** | tests/test_frontend.js |
| F-03 | Emergency notice in reporting panel AND footer, role=note, exact wording | both exact | panel=true footer=true | **PASS** | tests/test_frontend.js |
| F-04a | Consent notice covers location, photo/description use, vulnerable people, avoiding unneeded personal data | all four topics + checkbox | true,true,true,true,true | **PASS** | tests/test_frontend.js |
| F-02a | Volunteer step in How-it-works says SAMPLE / none contacted | present | true | **PASS** | tests/test_frontend.js |
| F-09 | Dashboard shows the real API values (16/14/2/4) and hides loader | 16/14/2/4, loader hidden | 16/14/2/4 loaderHidden=true | **PASS** | tests/test_frontend.js |
| F-09b | Loading indicator shown before data arrives | "Loading statistics…" visible initially | Loading statistics… | **PASS** | tests/test_frontend.js |
| F-10 | Stats API 500: counters show "–" (NOT 0); error + Retry shown | –,–,–,–; error; retry button | –,–,–,– \| Statistics could not be loaded: x. Retry | **PASS** | tests/test_frontend.js |
| F-11 | Retry button recovers the dashboard | 16/14/2/4, error gone | 16/14/2/4 hidden=true | **PASS** | tests/test_frontend.js |
| F-10b | Stats request that never answers times out with a message (no endless spinner) | timeout error + retry, counters "–" | Statistics could not be loaded: The server took too long to answer (timeout). Retry \| total=– | **PASS** | tests/test_frontend.js · timeouts time-scaled 400x for the test |
| F-10c | Backend unreachable (network error): clear message, no fake zeros | "Could not reach the server" | Statistics could not be loaded: Could not reach the server. Retry | **PASS** | tests/test_frontend.js |
| F-10d | Later refresh failure keeps last real values and warns | 16 kept + "last values from" | 16 \| Statistics could not be refreshed (Server error (500)). Showing the last values from 10:42 AM. Retry | **PASS** | tests/test_frontend.js |
| F-05 | AQI success (live): source named, "Not a CPCB" shown, rows rendered | Live · Open-Meteo model | Live · Open-Meteo model \| Open-Meteo model estimate (US AQI scale, ~10 km grid, nearby areas share one value). Not a CPCB station reading. Model time 2026-11-24 14:00 IST. Checked 10:42 AM. Refres rows=4 | **PASS** | tests/test_frontend.js |
| F-06 | AQI request hangs: times out, NOT stuck on Loading, retry offered, no values shown | Unavailable + timeout + retry | Unavailable \| Air-quality data could not be loaded: The server took too long to answer (timeout). No values are shown rather than showing wrong ones. Retry | **PASS** | tests/test_frontend.js |
| F-07 | AQI API failure shows error; Retry then loads data | error then Live rows | Air-quality data could not be loaded: x. No values are shown => Live · Open-Meteo model | **PASS** | tests/test_frontend.js |
| F-08 | Simulated fallback is unmistakably labelled (badge, banner, per-row "sim") | SIMULATED badge + "not measurements" | SIMULATED \| SIMULATED values, not measurements. The live air-quality service could not be reached, so these numbers are il | **PASS** | tests/test_frontend.js |
| F-08b | Stale data labelled STALE with age, not shown as current | STALE + "min ago" | STALE Open-Meteo model \| Service unreachable: showing data from 20 min ago. Open-Meteo model estimate (US AQI scale | **PASS** | tests/test_frontend.js |
| F-21 | Vulnerable reports drawn as ~1 km dashed approximate-area circles at the API's generalised coordinates (never a pin) | 4 circles r=550, no markers | 4 shapes: circle:550 | **PASS** | tests/test_frontend.js |
| F-02b | Priority list marks sample reports; shows no vulnerable free-text | SAMPLE tags, no "bujurg"/"medicine" | samples=10 leak=false | **PASS** | tests/test_frontend.js |
| F-24x | XSS regression: HTML in a report summary/category is rendered as text | no injected element, script not run | img=0 pwn=false ran=false | **PASS** | tests/test_frontend.js |
| F-10e | Reports API failure: error + Retry in list (not blank) | error and retry in list | Reports could not be loaded: Server error (500). Retry | **PASS** | tests/test_frontend.js |
| F-12 | Submit with no location: blocked, clear message, NO request sent | no POST, message | Please set a location first: tap My location, or tap the map where the problem is. posts=0 | **PASS** | tests/test_frontend.js |
| F-14 | GPS permission denied: explains and points to the map; no location set | denied message; locInfo not set | Location permission was denied. Tap the map to choose the location instead. \| Location: not set. Tap My location or tap the map. | **PASS** | tests/test_frontend.js |
| F-14b | GPS accepted but inaccurate (±4200 m): user warned and told how to correct | GPS + warning + Clear | Location: GPS (accuracy about 4200 m) GPS is not precise here. Tap the map to correct it. Clear | **PASS** | tests/test_frontend.js |
| F-15 | Manual map selection sets location (source "map") and it is sent with the report | "chosen on the map"; POST has lat,lng,loc_source=map | Location: chosen on the map Clear \| {"text":"Minto bridge paani bhar gaya","lat":"28.6139","lng":"77.209","loc_source":"map"} | **PASS** | tests/test_frontend.js |
| F-23 | Normal submission: success text, "Not sent yet", SAMPLE volunteers, authority wording; form + location reset; lists refreshed | all | notSent=true sample=2 auth=true textCleared=true loc=Location: chosen on  refreshed=true | **PASS** | tests/test_frontend.js |
| F-02c | No "sent to the office"-style wording in confirmation | absent | PRIORITY 59Elderly & Vulnerable Help · Karol Bagh Your report is recorded. Your complaint draft is ready to review. Not sent yet. This draft has not been sent t | **PASS** | tests/test_frontend.js |
| F-23c | Network failure on submit: NO false confirmation; text + location kept; honest message | "NOT submitted", no result card, text kept | Your report was NOT submitted. Could not reach the server. Your text and location are kept. Please try again. result="" text=keep my text | **PASS** | tests/test_frontend.js |
| F-23d | Server validation error shown to user; input kept | server message | Location is required. | **PASS** | tests/test_frontend.js |
| F-04b | Consent unchecked: submit blocked, no request | no POST, prompt | Please read the privacy note and tick the box to continue. posts=0 | **PASS** | tests/test_frontend.js |
| F-17 | Browser pre-check rejects .exe | unsupported message | Unsupported photo. Please choose a JPG, PNG or WebP image. | **PASS** | tests/test_frontend.js |
| F-19 | Browser pre-check rejects >5 MB | larger than 5 MB | That photo is larger than 5 MB. Please choose a smaller one. | **PASS** | tests/test_frontend.js |
| F-16 | Browser pre-check accepts a normal JPG | Photo added | Photo added: ok.jpg | **PASS** | tests/test_frontend.js |
| F-24 | Existing features: example chips, Map/List tabs, flag button (POST /abuse) still work | all true | chips=true tabs=true flagPost=true items=10 | **PASS** | tests/test_frontend.js |
| F-ROOT-a | ORIGINAL page, Leaflet unavailable: whole script dies (counters stay 0, AQI stuck on Loading…) | reproduces the live symptoms | total=0 aqsrc="Loading…" engine="AI · …" | **PASS** | tests/test_frontend.js · Simulated condition in jsdom. Shows a plausible cause; does NOT prove it is what happens on the live site. |
| F-ROOT-b | PATCHED page, Leaflet unavailable: stats, list and AQI still work; map shows a message | 16 + AQI + map notice | total=16 aqsrc="Live · Open-Meteo model" map="The map could not load (the map library " | **PASS** | tests/test_frontend.js |

## 3. NOT TESTED (and what is needed)

| Item | Why | Needed |
|---|---|---|
| Visual rendering of new notices, mobile responsiveness, tap-target sizes, contrast | jsdom has no CSS/layout engine. Tests only prove the elements exist with the right text/attributes | A real browser (Chrome DevTools device mode, or Playwright with a browser) and a phone |
| Real Leaflet map: tap to set location, dashed approximate-area circles, popups | Leaflet is replaced by a stub that records calls | Real browser with internet (unpkg + OSM tiles) |
| Real GPS prompt, permission flows, real accuracy values | `navigator.geolocation` is mocked | Real device |
| Real Open-Meteo success path | Sandbox has no internet; the HTTP call is mocked with the shape the code expects | Run locally with internet, or check `/api/aqi` on a deployed copy. I did not verify Open-Meteo's live response format myself |
| Real Claude calls (text and photo) | No API key. The photo path is tested with a mocked `claude_analyze` (checks the sniffed media type is passed) | `ANTHROPIC_API_KEY`, then submit a real photo |
| Deployed Render behaviour: cold start duration, restart data loss, client-IP behind the proxy (affects citizen-flag counting and admin lockout) | Nothing was deployed | A deployed test copy |
| Concurrent submissions / race conditions | Not attempted | Load test (not in approved scope) |
| Admin web page (`admin.html`) | File unchanged; only the admin API was tested | Browser |
| Voice input, screen readers, keyboard-only use of the new consent checkbox and Retry buttons | ARIA roles/labels were added but no accessibility audit was run | Manual + axe/Lighthouse |
| The 60-second auto-refresh timer by itself | Refresh-on-focus path is tested (F-10d); the interval is not timed | Real-time test |
| Hindi / Hinglish classification quality, AI severity accuracy | Unchanged code; needs a labelled test set | Part of the priority-algorithm work |