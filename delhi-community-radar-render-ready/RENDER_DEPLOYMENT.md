# Delhi Community Radar — Render deployment package

This archive is arranged so that `app.py` and `requirements.txt` are at the project root.

## Render settings

Create a **Web Service** connected to the GitHub repository containing these files.

- Runtime: Python 3
- Branch: `main` (or the branch you actually use)
- Root Directory: leave blank if these files are at the GitHub repository root
- Build Command: `pip install -r requirements.txt`
- Start Command: `uvicorn app:app --host 0.0.0.0 --port $PORT`

If you place this project inside a subfolder in GitHub, set Root Directory to that exact subfolder instead.

## Environment variables

In Render → your service → Environment, add:

- `ADMIN_PASSWORD`: a strong password you create. Admin login stays disabled until this is configured.
- `ANTHROPIC_API_KEY`: optional; only needed for Claude-powered features.

Do not put secrets in GitHub or in frontend files.

## Uploading to GitHub

Extract this ZIP on your computer, then upload the **contents** of the extracted folder (including `app.py`, `requirements.txt`, `static/`, `tests/`, and `docs/`) into the intended GitHub repository folder. Do not upload a `.git` folder.

## Important prototype limitation

Reports and admin state are held in memory and reset when the service restarts or redeploys. Add persistent database storage before relying on this for real-world reporting.

