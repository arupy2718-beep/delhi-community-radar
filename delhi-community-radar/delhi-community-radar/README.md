# Delhi Community Radar

**Theme:** Community Well-being · **Region:** Delhi

AI-powered civic triage. Residents report problems by **voice, photo or text** in Hindi, English or Hinglish. The AI classifies each report, merges duplicates, ranks urgency, routes it to the right Delhi authority with a ready-to-send complaint, matches nearby volunteers, and shows everything on a live priority map with smog-season alerts. A password-protected **admin console** lets moderators delete offensive reports.

## Run locally (Windows PowerShell)
```powershell
cd path\to\delhi-community-radar        # the folder that contains app.py
python -m pip install -r requirements.txt
python -m uvicorn app:app --reload
```
Open http://127.0.0.1:8000 in Chrome (voice input needs Chrome). Admin console: http://127.0.0.1:8000/admin

Optional settings (set them before the last command, in the same window):
```powershell
$env:ANTHROPIC_API_KEY="sk-ant-..."     # full AI mode (photos, better complaints, AI moderation). Without it: demo mode
$env:ADMIN_PASSWORD="choose-a-strong-password"
```
Mac/Linux: use `python3` and `export NAME=value` instead of `$env:NAME="value"`.

## Admin console (/admin)
- Locked behind `ADMIN_PASSWORD`. If you do not set it, a default demo password is used and a warning prints. **Always set your own before deploying.**
- Login attempts are limited (5 wrong tries, then a 5-minute lockout). Sessions last 4 hours.
- **Needs review** tab lists reports hidden by moderation. **Delete** removes a report permanently (clusters and priorities are recalculated). **Hide** takes it off the public site without deleting. **Approve** restores it.
- An **activity log** records every admin action.

## How offensive content is handled
1. Reports with abusive language (English and Hinglish word list) are held automatically. With an API key, Claude also flags abuse, threats and spam.
2. Citizens can flag any report with the ⚑ button. It is hidden after 3 flags from 3 different devices.
3. Held and hidden reports never appear on the public map or queue; they wait in the admin console.

## How it works
1. **Capture** voice, photo or text; location by GPS or map tap
2. **Understand** category, severity (1-5), locality, vulnerable people at risk
3. **Cluster** nearby reports of the same issue (within 700 m) merge and raise priority
4. **Route** to MCD / DJB / PWD / DPCC / RWA-NGO with an auto-drafted complaint
5. **Match** nearest volunteers with the right skill

Priority = severity x 12 + 8 per merged duplicate + 15 if vulnerable people are affected (max 100).

## Deploy free (Render)
1. Push this folder to GitHub
2. render.com -> New -> Web Service -> pick the repo
3. Build command: `pip install -r requirements.txt`
4. Start command: `uvicorn app:app --host 0.0.0.0 --port $PORT`
5. Environment variables: `ADMIN_PASSWORD` (required), `ANTHROPIC_API_KEY` (optional)
6. Open the public URL once before judges do (the free tier sleeps)

## 3-minute demo script
1. (20s) Problem: scattered complaints, duplicates, slow help
2. (30s) Map and queue: 16 seeded Delhi reports, Ghazipur garbage ranked first
3. (60s) Live: Speak in Hinglish, "Karol Bagh mein ek bujurg akele hain, tabiyat kharab hai". Watch the AI console, then show classification, authority, drafted complaint, volunteers
4. (30s) Moderation: submit an abusive report, show it is held, open /admin, delete it
5. (20s) Smog watch and the roadmap

## Honest notes (say these in your pitch)
- Seeded reports, volunteers and AQI values are **illustrative sample data**; production would use CPCB / OpenAQ
- Complaints are drafted for the citizen to send; direct MCD/DJB submission is on the roadmap
- Data is held in memory, so restarting the server resets reports and admin deletions. A database is the next step

## Stack
FastAPI, Claude API (text + vision), Leaflet + OpenStreetMap, Web Speech API. Plain HTML/CSS/JS front end, no build step.
