"""
Delhi Community Radar - AI-powered civic issue triage for Delhi.

Pipeline for every citizen report (text / Hindi / Hinglish / voice transcript / photo):
  1. AI understands  -> category, severity, locality, vulnerable people flag
  2. AI routes       -> correct authority (MCD, NDMC, DJB, PWD, DPCC ...)
  3. AI drafts       -> ready-to-send formal complaint
  4. Clustering      -> merges nearby duplicate reports, raises priority
  5. Volunteer match -> nearest volunteers with the right skill
Works with Claude if ANTHROPIC_API_KEY is set, otherwise falls back to a
rule-based engine so the demo never breaks.
"""
import base64
import json
import math
import os
import random
import re
import time
import uuid
import secrets
import hmac
from typing import Optional

from fastapi import FastAPI, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-5-5")
API_KEY = os.getenv("ANTHROPIC_API_KEY")

# ---- admin config. SET ADMIN_PASSWORD before you deploy publicly.
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
if not ADMIN_PASSWORD:
    ADMIN_PASSWORD = "radar-admin"
    print("WARNING: ADMIN_PASSWORD is not set. Using the default demo password. Set ADMIN_PASSWORD before deploying.")
ADMIN_TOKENS = {}   # token -> expiry timestamp
FAILED = {}         # ip -> recent failed login timestamps
ABUSE = {}          # report id -> set of reporter IPs who flagged it
AUDIT = []          # admin activity log

app = FastAPI(title="Delhi Community Radar")

# ----------------------------------------------------------------- reference data
LOCALITIES = {
    "Karol Bagh": (28.6519, 77.1909, ["karol bagh", "करोल बाग"]),
    "Connaught Place": (28.6315, 77.2167, ["connaught", "cp", "minto bridge", "minto", "कनॉट"]),
    "Chandni Chowk": (28.6506, 77.2303, ["chandni chowk", "चांदनी चौक", "old delhi"]),
    "Dwarka": (28.5921, 77.0460, ["dwarka", "द्वारका"]),
    "Rohini": (28.7495, 77.0565, ["rohini", "रोहिणी"]),
    "Janakpuri": (28.6219, 77.0878, ["janakpuri", "जनकपुरी"]),
    "Lajpat Nagar": (28.5677, 77.2432, ["lajpat", "लाजपत"]),
    "Saket": (28.5245, 77.2066, ["saket", "साकेत"]),
    "Vasant Kunj": (28.5200, 77.1590, ["vasant kunj", "वसंत कुंज"]),
    "Okhla": (28.5355, 77.2751, ["okhla", "ओखला"]),
    "Mayur Vihar": (28.6080, 77.2940, ["mayur vihar", "मयूर विहार"]),
    "Ghazipur": (28.6250, 77.3280, ["ghazipur", "गाज़ीपुर", "गाजीपुर"]),
    "Bhalswa": (28.7460, 77.1660, ["bhalswa", "भलस्वा"]),
    "Seelampur": (28.6700, 77.2670, ["seelampur", "सीलमपुर"]),
    "Anand Vihar": (28.6469, 77.3158, ["anand vihar", "आनंद विहार"]),
    "Pitampura": (28.7033, 77.1322, ["pitampura", "पीतमपुरा"]),
    "Laxmi Nagar": (28.6304, 77.2773, ["laxmi nagar", "लक्ष्मी नगर"]),
}

CATEGORIES = {
    "Garbage & Waste": {"authority": "MCD (Sanitation Dept.)", "skill": "cleanup",
        "kw": ["garbage", "kooda", "kachra", "कचरा", "कूड़ा", "waste", "dump", "landfill", "badbu", "smell", "गंदगी"]},
    "Waterlogging & Drainage": {"authority": "MCD / PWD Drainage", "skill": "cleanup",
        "kw": ["waterlog", "paani bhar", "पानी भर", "flood", "drain", "naala", "नाला", "sewer", "overflow", "jal jamav", "बारिश"]},
    "Water Supply": {"authority": "Delhi Jal Board (DJB)", "skill": "plumbing",
        "kw": ["no water", "water supply", "pipeline", "leak", "paani nahi", "पानी नहीं", "tanker", "contaminated", "dirty water", "गंदा पानी", "djb", "gandha paani", "paani gandha", "jal board"]},
    "Streetlight & Electricity": {"authority": "MCD Electrical / DISCOM", "skill": "electrical",
        "kw": ["streetlight", "street light", "light nahi", "बत्ती", "अंधेरा", "dark", "wire", "transformer", "pole"]},
    "Road & Potholes": {"authority": "PWD / MCD Roads", "skill": "general",
        "kw": ["pothole", "gadda", "गड्ढा", "road", "sadak", "सड़क", "broken road", "footpath"]},
    "Air Pollution": {"authority": "DPCC / Delhi Pollution Control Committee", "skill": "general",
        "kw": ["smog", "pollution", "dhuan", "धुआं", "burning", "stubble", "construction dust", "aqi", "dust", "smoke", "fire", "प्रदूषण"]},
    "Elderly & Vulnerable Help": {"authority": "Local RWA / NGO + Delhi Social Welfare Dept.", "skill": "care",
        "kw": ["elderly", "senior", "bujurg", "बुजुर्ग", "alone", "akela", "अकेला", "sick", "bimar", "बीमार", "homeless", "disabled", "medicine"]},
    "Stray Animals": {"authority": "MCD Veterinary Services", "skill": "general",
        "kw": ["stray", "dog", "kutta", "कुत्ता", "cattle", "cow", "gaay", "monkey", "bandar", "बंदर"]},
}

VOLUNTEERS = [
    {"id": "v1", "name": "Aarti Sharma", "skills": ["care", "general"], "area": "Karol Bagh"},
    {"id": "v2", "name": "Rohit Verma", "skills": ["cleanup", "general"], "area": "Ghazipur"},
    {"id": "v3", "name": "Seva Delhi NGO", "skills": ["care", "cleanup"], "area": "Chandni Chowk"},
    {"id": "v4", "name": "Imran Khan", "skills": ["electrical", "plumbing"], "area": "Okhla"},
    {"id": "v5", "name": "Neha Gupta", "skills": ["cleanup", "general"], "area": "Dwarka"},
    {"id": "v6", "name": "Rajesh Yadav", "skills": ["plumbing", "general"], "area": "Rohini"},
    {"id": "v7", "name": "Green Saket RWA", "skills": ["cleanup", "care"], "area": "Saket"},
    {"id": "v8", "name": "Pooja Malhotra", "skills": ["care"], "area": "Janakpuri"},
    {"id": "v9", "name": "Delhi Youth Corps", "skills": ["cleanup", "general", "electrical"], "area": "Laxmi Nagar"},
]

# Illustrative demo AQI per locality (simulated; swap for CPCB / OpenAQ feed in production)
AQI_BASE = {"Anand Vihar": 412, "Ghazipur": 389, "Bhalswa": 376, "Rohini": 341, "Okhla": 352,
            "Dwarka": 318, "Karol Bagh": 305, "Connaught Place": 287, "Saket": 262,
            "Vasant Kunj": 241, "Seelampur": 355, "Pitampura": 322, "Mayur Vihar": 330,
            "Lajpat Nagar": 296, "Janakpuri": 308, "Chandni Chowk": 340, "Laxmi Nagar": 347}

REPORTS = []


# ----------------------------------------------------------------- helpers
def haversine(a, b, c, d):
    r = 6371000
    p1, p2 = math.radians(a), math.radians(c)
    dp, dl = p2 - p1, math.radians(d - b)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


def find_locality(text: str) -> Optional[str]:
    t = text.lower()
    for name, (_, _, aliases) in LOCALITIES.items():
        if name.lower() in t or any(a in t for a in aliases):
            return name
    return None


def detect_language(text: str) -> str:
    if re.search(r"[\u0900-\u097F]", text):
        return "Hindi"
    hinglish = ["hai", "nahi", "bhar", "kachra", "paani", "bahut", "kab", "mein", "ka ", "ki "]
    if sum(w in text.lower() for w in hinglish) >= 2:
        return "Hinglish"
    return "English"


def aqi_band(v: int):
    if v > 400: return "Severe+"
    if v > 300: return "Very Poor"
    if v > 200: return "Poor"
    return "Moderate"


# ----------------------------------------------------------------- moderation
BAD_WORDS = ["fuck", "fucking", "shit", "bitch", "bastard", "asshole", "idiot", "stupid", "moron",
             "madarchod", "behenchod", "bhenchod", "chutiya", "bhosdike", "bhosdi", "gandu", "harami", "randi", "saala", "kamina"]
BAD_RE = re.compile(r"\b(" + "|".join(BAD_WORDS) + r")\b", re.I)


def moderate(text: str) -> Optional[str]:
    m = BAD_RE.search(text or "")
    return f"Offensive language detected ({m.group(1).lower()})" if m else None


def hidden(r) -> bool:
    return bool(r.get("flagged")) or len(ABUSE.get(r["id"], ())) >= 3


def audit(action, r=None, note=""):
    AUDIT.append({"t": int(time.time()), "action": action, "id": r["id"] if r else None,
                  "snippet": (r["text"][:70] if r else ""), "note": note})
    del AUDIT[:-200]


def recompute():
    """Rebuild cluster sizes and priorities after a delete / hide / approve."""
    groups = {}
    for o in REPORTS:
        groups.setdefault(o["cluster_id"], []).append(o)
    for g in groups.values():
        vis = [o for o in g if not hidden(o)]
        for o in g:
            o["cluster_size"] = 1 if hidden(o) else max(1, len(vis))
    for o in REPORTS:
        o["priority"] = priority(o)


# ----------------------------------------------------------------- AI engines
def rule_based(text: str) -> dict:
    t = text.lower()
    best, score = "Garbage & Waste", 0
    for cat, info in CATEGORIES.items():
        s = sum(k in t for k in info["kw"])
        if s > score:
            best, score = cat, s
    urgent_words = ["urgent", "emergency", "accident", "bimar", "sick", "elderly", "bujurg", "बुजुर्ग",
                    "overflow", "danger", "child", "bachche", "days", "hafte", "week", "ambulance"]
    sev = 2 + min(3, sum(w in t for w in urgent_words))
    vulnerable = any(w in t for w in ["elderly", "senior", "bujurg", "बुजुर्ग", "child", "bachche", "sick", "bimar", "homeless", "disabled"])
    return {"category": best, "severity": min(5, sev), "locality": find_locality(text),
            "vulnerable_people": vulnerable, "engine": "rules"}


PROMPT = """You are the triage engine of Delhi Community Radar. A Delhi resident sent a civic report
(may be English, Hindi or Hinglish, and may include a photo). Respond with ONLY a JSON object:
{{
 "category": one of {cats},
 "severity": integer 1-5 (5 = immediate danger / vulnerable people at risk),
 "locality": one of {locs} or null if unclear,
 "vulnerable_people": true/false (elderly, children, sick, outdoor workers affected),
 "offensive": true if the report contains abuse, hate, slurs, threats, or is spam / not a genuine civic issue, else false,
 "summary_en": one-line English summary,
 "complaint_draft": a polite, formal 4-6 line complaint in English addressed to the right authority,
   including issue, location, impact, and a request for action within a stated timeframe,
 "suggested_action": one short practical next step for residents/volunteers
}}
Citizen report: \"\"\"{text}\"\"\""""


def claude_analyze(text: str, image: Optional[bytes], media_type: str) -> Optional[dict]:
    if not API_KEY:
        return None
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=API_KEY)
        content = []
        if image:
            content.append({"type": "image", "source": {"type": "base64", "media_type": media_type,
                                                         "data": base64.b64encode(image).decode()}})
        content.append({"type": "text", "text": PROMPT.format(
            cats=list(CATEGORIES.keys()), locs=list(LOCALITIES.keys()), text=text or "(photo only - describe the issue from the image)")})
        msg = client.messages.create(model=MODEL, max_tokens=900, messages=[{"role": "user", "content": content}])
        raw = msg.content[0].text
        data = json.loads(re.search(r"\{.*\}", raw, re.S).group(0))
        data["engine"] = "claude"
        return data
    except Exception as e:  # never break the demo
        print("Claude call failed, using fallback:", e)
        return None


def draft_fallback(cat, loc, text, authority):
    return (f"To,\nThe Officer-in-Charge, {authority}\n\n"
            f"Subject: Urgent civic issue - {cat} at {loc}\n\n"
            f"Residents of {loc} have reported the following: \"{text.strip()[:240]}\". "
            f"This is affecting daily life and public safety in the area. "
            f"We request inspection and resolution within 48 hours and a status update to the complainant.\n\nRegards,\nDelhi Community Radar (on behalf of residents)")


def analyze(text, image, media_type):
    ai = claude_analyze(text, image, media_type)
    base = rule_based(text)
    if not ai:
        ai = base
    cat = ai.get("category") if ai.get("category") in CATEGORIES else base["category"]
    loc = ai.get("locality") if ai.get("locality") in LOCALITIES else (base["locality"] or None)
    sev = int(ai.get("severity") or base["severity"])
    sev = max(1, min(5, sev))
    info = CATEGORIES[cat]
    return {
        "category": cat, "severity": sev, "locality": loc,
        "vulnerable_people": bool(ai.get("vulnerable_people", base["vulnerable_people"])),
        "offensive": bool(ai.get("offensive", False)),
        "authority": info["authority"], "skill": info["skill"],
        "summary": ai.get("summary_en") or text.strip()[:110],
        "complaint_draft": ai.get("complaint_draft") or None,
        "suggested_action": ai.get("suggested_action") or "Report logged and prioritised. Residents can document the issue with photos; suggested volunteers are listed.",
        "engine": ai.get("engine", "rules"),
    }


def cluster_and_score(r):
    """Merge with nearby same-category reports, compute priority."""
    if hidden(r):
        r["cluster_id"], r["cluster_size"] = r["id"], 1
        return 1
    mates = [o for o in REPORTS if o["category"] == r["category"] and not hidden(o)
             and haversine(o["lat"], o["lng"], r["lat"], r["lng"]) < 700 and o["id"] != r["id"]]
    cid = mates[0]["cluster_id"] if mates else r["id"]
    r["cluster_id"] = cid
    for o in mates:
        o["cluster_id"] = cid
    group = [o for o in REPORTS if o["cluster_id"] == cid] + ([r] if r not in REPORTS else [])
    size = len(group)
    for o in group:
        o["cluster_size"] = size
    return size


def priority(r):
    score = r["severity"] * 12 + (r["cluster_size"] - 1) * 8 + (15 if r["vulnerable_people"] else 0)
    return min(100, score)


def match_volunteers(r, k=2):
    scored = []
    for v in VOLUNTEERS:
        la, lo, _ = LOCALITIES[v["area"]]
        d = haversine(la, lo, r["lat"], r["lng"]) / 1000
        bonus = 0 if r["skill"] in v["skills"] else 8  # penalise skill mismatch
        scored.append((d + bonus, d, v))
    scored.sort(key=lambda x: x[0])
    return [{"name": v["name"], "area": v["area"], "skills": v["skills"], "distance_km": round(d, 1)}
            for _, d, v in scored[:k]]


def make_report(text, lat, lng, image=None, media_type="image/jpeg", ts=None):
    a = analyze(text, image, media_type)
    if lat is None or lng is None:
        loc = a["locality"] or random.choice(list(LOCALITIES.keys()))
        a["locality"] = loc
        la, lo, _ = LOCALITIES[loc]
        lat, lng = la + random.uniform(-0.0015, 0.0015), lo + random.uniform(-0.0015, 0.0015)
    elif not a["locality"]:
        a["locality"] = min(LOCALITIES, key=lambda n: haversine(LOCALITIES[n][0], LOCALITIES[n][1], lat, lng))
    r = {"id": uuid.uuid4().hex[:8], "text": text, "lat": lat, "lng": lng,
         "language": detect_language(text), "created": ts or int(time.time()), "has_photo": bool(image), **a}
    reason = moderate(text) or ("Flagged by AI moderation" if a.get("offensive") else None)
    r["flagged"], r["flag_reason"] = bool(reason), reason
    if not r["complaint_draft"]:
        r["complaint_draft"] = draft_fallback(r["category"], r["locality"], text, r["authority"])
    cluster_and_score(r)
    REPORTS.append(r)
    r["priority"] = priority(r)
    for o in REPORTS:
        if o["cluster_id"] == r["cluster_id"]:
            o["priority"] = priority(o)
    r["volunteers"] = match_volunteers(r)
    return r


# ----------------------------------------------------------------- seed demo data
SEED = [
    ("Minto Bridge underpass mein paani bhar gaya hai, gaadiyan phans gayi hain. Urgent!", None),
    ("Minto bridge waterlogging again, buses stuck near Connaught Place", None),
    ("Ghazipur landfill ke paas kachra ka pahad, bahut badbu aur dhuan hai, bachche bimar ho rahe hain", None),
    ("Garbage not collected for 6 days near Ghazipur market, stray dogs and smell", None),
    ("Karol Bagh mein ek bujurg akele rehte hain, unki tabiyat kharab hai, medicine chahiye", None),
    ("Streetlight kharab hai Dwarka sector 12, raat ko andhera, women safety issue", None),
    ("Rohini sector 7 mein DJB ka paani gandha aa raha hai, 3 din se", None),
    ("Dwarka mor drain overflow, sewer water on the road", None),
    ("Anand Vihar mein bahut dhuan, construction dust aur AQI very high, outdoor workers affected", None),
    ("Bhalswa landfill fire smoke covering the colony, children coughing", None),
    ("Okhla pothole on main road, two-wheeler accident today", None),
    ("Saket mein stray dogs ka jhund bachchon ko dara rahe hain", None),
    ("Janakpuri mein transformer sparking near the park, danger", None),
    ("Laxmi Nagar nala choked, paani bhar gaya gali mein", None),
    ("Chandni Chowk mein kooda sadak par pada hai, 4 din se nahi utha", None),
    ("Seelampur mein homeless elderly people sleeping outside in the cold smog, need blankets", None),
]


def seed():
    if REPORTS:
        return
    random.seed(7)
    for i, (txt, _) in enumerate(SEED):
        make_report(txt, None, None, ts=int(time.time()) - (len(SEED) - i) * 3600)
    random.seed()


seed()


# ----------------------------------------------------------------- API
@app.post("/api/report")
async def create_report(text: str = Form(""), lat: Optional[float] = Form(None),
                        lng: Optional[float] = Form(None), photo: Optional[UploadFile] = File(None)):
    image, mt = None, "image/jpeg"
    if photo is not None:
        image = await photo.read()
        mt = photo.content_type or "image/jpeg"
    if not text.strip() and not image:
        return {"error": "Please describe the issue or attach a photo."}
    return make_report(text, lat, lng, image, mt)


@app.get("/api/reports")
def list_reports():
    return sorted([r for r in REPORTS if not hidden(r)], key=lambda r: -r["priority"])


@app.get("/api/stats")
def stats():
    by_cat, by_loc = {}, {}
    vis = [r for r in REPORTS if not hidden(r)]
    for r in vis:
        by_cat[r["category"]] = by_cat.get(r["category"], 0) + 1
        by_loc.setdefault(r["locality"], []).append(r["priority"])
    areas = [{"locality": k, "lat": LOCALITIES[k][0], "lng": LOCALITIES[k][1],
              "reports": len(v), "score": round(sum(v) / len(v) + len(v) * 2)} for k, v in by_loc.items()]
    areas.sort(key=lambda a: -a["score"])
    clusters = {r["cluster_id"] for r in vis}
    return {"total": len(vis), "clusters": len(clusters),
            "duplicates_merged": len(vis) - len(clusters),
            "vulnerable": sum(r["vulnerable_people"] for r in vis),
            "by_category": by_cat, "areas": areas,
            "ai_engine": "Claude" if API_KEY else "Rule-based fallback (set ANTHROPIC_API_KEY for full AI)"}


@app.get("/api/aqi")
def aqi():
    out = []
    for loc, v in AQI_BASE.items():
        v = v + random.randint(-12, 12)
        band = aqi_band(v)
        adv = ("Elderly, children & outdoor workers: stay indoors, wear N95, avoid morning walks."
               if v > 300 else "Sensitive groups should limit prolonged outdoor activity.")
        out.append({"locality": loc, "lat": LOCALITIES[loc][0], "lng": LOCALITIES[loc][1],
                    "aqi": v, "band": band, "advisory": adv})
    out.sort(key=lambda x: -x["aqi"])
    return {"simulated": True, "data": out}


# ----------------------------------------------------------------- public abuse flag
def _find(rid):
    r = next((o for o in REPORTS if o["id"] == rid), None)
    if not r:
        raise HTTPException(status_code=404, detail="Report not found")
    return r


@app.post("/api/report/{rid}/abuse")
def report_abuse(rid: str, request: Request):
    r = _find(rid)
    ip = request.client.host if request.client else "unknown"
    ABUSE.setdefault(rid, set()).add(ip)
    recompute()
    audit("citizen-flag", r, f"{len(ABUSE[rid])} flag(s)")
    return {"ok": True}


# ----------------------------------------------------------------- admin API
def require_admin(token: Optional[str]):
    exp = ADMIN_TOKENS.get(token or "")
    if not exp or exp < time.time():
        raise HTTPException(status_code=401, detail="Admin login required")


@app.post("/api/admin/login")
def admin_login(request: Request, password: str = Form("")):
    ip = request.client.host if request.client else "unknown"
    now = time.time()
    fails = [t for t in FAILED.get(ip, []) if now - t < 300]
    if len(fails) >= 5:
        raise HTTPException(status_code=429, detail="Too many attempts. Try again in a few minutes.")
    if not hmac.compare_digest(password.encode(), ADMIN_PASSWORD.encode()):
        fails.append(now)
        FAILED[ip] = fails
        raise HTTPException(status_code=401, detail="Wrong password")
    FAILED.pop(ip, None)
    tok = secrets.token_urlsafe(24)
    ADMIN_TOKENS[tok] = now + 4 * 3600
    audit("admin-login")
    return {"token": tok}


@app.get("/api/admin/reports")
def admin_reports(x_admin_token: Optional[str] = Header(None)):
    require_admin(x_admin_token)
    rows = sorted(REPORTS, key=lambda r: (0 if hidden(r) else 1, -r["priority"]))
    return {"reports": [{**r, "hidden": hidden(r), "abuse_reports": len(ABUSE.get(r["id"], ()))} for r in rows],
            "audit": AUDIT[-40:][::-1],
            "total": len(REPORTS), "hidden": sum(1 for r in REPORTS if hidden(r))}


@app.delete("/api/admin/reports/{rid}")
def admin_delete(rid: str, x_admin_token: Optional[str] = Header(None)):
    require_admin(x_admin_token)
    r = _find(rid)
    REPORTS.remove(r)
    ABUSE.pop(rid, None)
    recompute()
    audit("delete", r, r.get("flag_reason") or "")
    return {"ok": True}


@app.post("/api/admin/reports/{rid}/hide")
def admin_hide(rid: str, x_admin_token: Optional[str] = Header(None)):
    require_admin(x_admin_token)
    r = _find(rid)
    r["flagged"], r["flag_reason"] = True, "Hidden by admin"
    recompute()
    audit("hide", r)
    return {"ok": True}


@app.post("/api/admin/reports/{rid}/approve")
def admin_approve(rid: str, x_admin_token: Optional[str] = Header(None)):
    require_admin(x_admin_token)
    r = _find(rid)
    r["flagged"], r["flag_reason"] = False, None
    ABUSE.pop(rid, None)
    cluster_and_score(r)
    recompute()
    audit("approve", r)
    return {"ok": True}


@app.get("/admin")
def admin_page():
    return FileResponse(os.path.join(os.path.dirname(__file__), "static", "admin.html"))


app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")), name="static")


@app.get("/")
def home():
    return FileResponse(os.path.join(os.path.dirname(__file__), "static", "index.html"))
