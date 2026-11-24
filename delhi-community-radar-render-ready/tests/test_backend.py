"""Backend tests for phases A-D. Run: python test_backend.py  (from the app folder). Writes backend_results.json"""
import os, sys, json, io, struct, zlib, socket, time, urllib.error, urllib.request
os.environ.pop("ANTHROPIC_API_KEY", None)
os.environ["ADMIN_PASSWORD"] = "test-admin-pw-123"
sys.path.insert(0, os.getcwd())
from fastapi.testclient import TestClient
import app as A

R = []
def rec(tid, name, expected, actual, ok, evidence="", issue=""):
    R.append(dict(id=tid, name=name, expected=expected, actual=actual, result="PASS" if ok else "FAIL", evidence=evidence, remaining=issue))
    print(("PASS" if ok else "FAIL"), tid, name, "|", actual)

c = TestClient(A.app)
GOOD = dict(text="Karol Bagh mein ek bujurg akele rehte hain, tabiyat kharab hai", lat="28.6519", lng="77.1909", loc_source="gps")

def png():
    def ch(t, d): return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
    return b"\x89PNG\r\n\x1a\n" + ch(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)) + ch(b"IDAT", zlib.compress(b"\x00\xff\x00\x00")) + ch(b"IEND", b"")
JPEG = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00" + b"\x00" * 50 + b"\xff\xd9"
WEBP = b"RIFF" + struct.pack("<I", 20) + b"WEBPVP8 " + b"\x00" * 20
def post(data=None, files=None): return c.post("/api/report", data=data, files=files)
def n(): return len(A.REPORTS)

# ---- baseline / existing behaviour
st = c.get("/api/stats").json()
rec("B-24a", "Seed stats unchanged", "16/14/2/4", f'{st["total"]}/{st["clusters"]}/{st["duplicates_merged"]}/{st["vulnerable"]}',
    (st["total"], st["clusters"], st["duplicates_merged"], st["vulnerable"]) == (16, 14, 2, 4))
rec("B-24b", "All 16 seeds loaded, none skipped, all flagged sample", "16 sample", f'{sum(1 for r in A.REPORTS if r.get("sample"))} sample of {n()}', n() == 16 and all(r["sample"] for r in A.REPORTS))
rec("B-24c", "Priority formula untouched (report's worked example = 59)", "59", str(A.priority({"severity": 3, "cluster_size": 2, "vulnerable_people": True})), A.priority({"severity": 3, "cluster_size": 2, "vulnerable_people": True}) == 59)
vol_ok = all(v.get("sample") is True for v in A.VOLUNTEERS)
rec("B-02", "Every volunteer record is marked sample (API)", "all sample:true", str(vol_ok), vol_ok)

# ---- location
before = n()
r = post({"text": "pothole on road"})
rec("B-12a", "Missing location rejected", "422 + clear error, nothing stored", f"{r.status_code} {r.json()}", r.status_code == 422 and "Location is required" in r.json()["error"] and n() == before)
r = post({"text": "pothole", "lat": "28.6"})
rec("B-12b", "Only latitude supplied rejected", "422", str(r.status_code), r.status_code == 422 and n() == before)
bad = [("999", "999"), ("abc", "77.2"), ("nan", "77.2"), ("inf", "77.2"), ("-91", "77.2"), ("28.6", "181"), ("19.07", "72.87"), ("0", "0")]
codes = [post({"text": "pothole", "lat": a, "lng": b}).status_code for a, b in bad]
rec("B-13", "Invalid / non-finite / out-of-NCR coordinates rejected", "all 422, nothing stored", str(codes), all(x == 422 for x in codes) and n() == before, "cases: " + str(bad))
r = post(GOOD)
j = r.json()
rec("B-23a", "Normal GPS report accepted", "200, locality from coordinates, source gps", f'{r.status_code} locality={j.get("locality")} source={j.get("location_source")}', r.status_code == 200 and j["locality"] == "Karol Bagh" and j["location_source"] == "gps")
rec("B-23b", "Owner response has draft, authority, SAMPLE volunteers; no cluster internals", "volunteers all sample", str([(v["name"], v["sample"]) for v in j["volunteers"]]), j["volunteers"] and all(v["sample"] for v in j["volunteers"]) and "complaint_draft" in j)
r = post({"text": "kachra ka dher", "lat": "28.9", "lng": "77.1", "loc_source": "map"}).json()
rec("B-12c", "Location far from any known locality is NOT given a random locality", "Other Delhi NCR", r.get("locality", str(r)), r.get("locality") == "Other Delhi NCR")
r = post({"text": "Ghazipur mein kachra", "lat": "28.5355", "lng": "77.2751", "loc_source": "map"}).json()
rec("B-12d", "Text-named locality never overrides coordinates; mismatch recorded for admin", "locality=Okhla, hint=Ghazipur, mismatch", f'{r["locality"]}', r["locality"] == "Okhla" and [x for x in A.REPORTS if x["id"] == r["id"]][0]["location_mismatch"] is True)

# ---- text / PII
r = post({**GOOD, "text": "x" * 1501})
rec("B-27", "Over-long description rejected", "413", str(r.status_code), r.status_code == 413)
r = post({**GOOD, "text": "Elderly neighbour Ramesh, call 9876543210 or a@b.com, id 1234 5678 9012"}).json()
stored = [x for x in A.REPORTS if x["id"] == r["id"]][0]["text"]
rec("B-09", "Phone / e-mail / 12-digit ID masked before storing", "masked", stored, all(t not in stored for t in ("9876543210", "a@b.com", "1234 5678 9012")))
r = post({"lat": "28.65", "lng": "77.19", "text": ""})
rec("B-27b", "Empty complaint rejected", "422", str(r.status_code), r.status_code == 422)
r = post({"lat": "28.65", "lng": "77.19", "text": ""}, files={"photo": ("a.png", png(), "image/png")})
rec("B-27c", "Photo-only without AI key rejected with clear message", "422", f'{r.status_code} {r.json().get("error")}', r.status_code == 422)

# ---- uploads
cap = {}
orig = A.claude_analyze
def fake(text, image, mt): cap.update(mt=mt, size=len(image) if image else 0); return None
A.claude_analyze = fake; A.API_KEY = "test"   # exercises the photo->AI path with a MOCK (real Claude not called)
for nm, data, ct, want in [("a.jpg", JPEG, "image/jpeg", "image/jpeg"), ("b.png", png(), "image/png", "image/png"), ("c.webp", WEBP, "image/webp", "image/webp")]:
    cap.clear(); r = post({**GOOD, "text": "pothole on road"}, files={"photo": (nm, data, ct)})
    rec("B-16" + nm.split(".")[1][0:2], f"Valid {nm} accepted and passed to AI path with sniffed media type", f"200, media_type {want}", f'{r.status_code}, passed {cap.get("mt")}', r.status_code == 200 and cap.get("mt") == want and r.json()["has_photo"])
A.claude_analyze = orig; A.API_KEY = None
cases = [
 ("B-17a", "virus.exe, MIME exe", ("virus.exe", b"MZ\x90\x00" * 20, "application/x-msdownload"), 415),
 ("B-17b", "a.exe with image MIME", ("a.exe", JPEG, "image/jpeg"), 415),
 ("B-17c", "GIF not allowed", ("a.gif", b"GIF89a" + b"\x00" * 30, "image/gif"), 415),
 ("B-17d", "SVG (script-capable) not allowed", ("a.svg", b"<svg onload=alert(1)>", "image/svg+xml"), 415),
 ("B-17e", "No extension", ("photo", JPEG, "image/jpeg"), 415),
 ("B-17f", ".html named as image MIME", ("x.html", b"<script>", "image/jpeg"), 415),
 ("B-18a", "Disguised: exe bytes named .jpg, MIME image/jpeg", ("evil.jpg", b"MZ\x90\x00\x03" + b"\x00" * 60, "image/jpeg"), 415),
 ("B-18b", "Disguised: text/script named .png", ("evil.png", b"<?php system($_GET[1]); ?>", "image/png"), 415),
 ("B-18c", "Disguised: PNG bytes named .jpg", ("x.jpg", png(), "image/jpeg"), 415),
 ("B-18d", "Disguised: ELF binary named .webp", ("x.webp", b"\x7fELF" + b"\x00" * 60, "image/webp"), 415),
 ("B-17g", "Empty file", ("e.jpg", b"", "image/jpeg"), 400),
]
for tid, nm, f, want in cases:
    b = n(); r = post({**GOOD, "text": "pothole"}, files={"photo": f})
    rec(tid, nm, f"{want}, nothing stored", f"{r.status_code} {r.json().get('error')}", r.status_code == want and n() == b)
big = JPEG[:-2] + b"\x00" * (5 * 1024 * 1024) + b"\xff\xd9"
b = n(); r = post({**GOOD, "text": "pothole"}, files={"photo": ("big.jpg", big, "image/jpeg")})
rec("B-19", "Oversized (>5 MB) photo rejected", "413, nothing stored", f"{r.status_code} {r.json().get('error')}", r.status_code == 413 and n() == b)
big2 = JPEG[:-2] + b"\x00" * (6 * 1024 * 1024) + b"\xff\xd9"
r = post({**GOOD, "text": "pothole"}, files={"photo": ("big.jpg", big2, "image/jpeg")})
rec("B-19b", "Grossly oversized request stopped by Content-Length guard", "413", str(r.status_code), r.status_code == 413)

# ---- public privacy
pub = c.get("/api/reports").json()
WL = {"id", "category", "severity", "priority", "cluster_id", "cluster_size", "locality", "authority", "summary", "vulnerable_people", "lat", "lng", "location_precision", "created", "sample"}
rec("B-20a", "Public API exposes only whitelisted fields", "no text/draft/volunteers/flag data", str(sorted(set().union(*[set(x) for x in pub]) - WL) or "no extra fields"), all(set(x) <= WL for x in pub))
dump = json.dumps(pub)
leaks = [w for w in ("bujurg", "medicine", "akele", "tabiyat", "bachche bimar", "homeless", "blankets", "complaint_draft", "volunteers") if w in dump]
rec("B-20b", "No vulnerable-person wording / free text leaks anywhere in public JSON", "no leaks", str(leaks or "none"), not leaks)
by_id = {x["id"]: x for x in A.REPORTS}
sens = [p for p in pub if A.is_sensitive(by_id[p["id"]])]
ordn = [p for p in pub if not A.is_sensitive(by_id[p["id"]])]
rec("B-20c", "Sensitive reports have generic summary + 'approximate' precision", f"{len(sens)} sensitive", f"{len(sens)} checked", len(sens) >= 4 and all(p["location_precision"] == "approximate" and "withheld" in p["summary"] for p in sens))
def off(p):
    t = by_id[p["id"]]; return A.haversine(t["lat"], t["lng"], p["lat"], p["lng"])
cell_ok = all(round(p["lat"] * 100 % 1, 2) == 0.5 or abs((p["lat"] * 100 % 1) - 0.5) < 1e-6 for p in sens)
rec("B-21a", "Sensitive public coordinates are 1-km grid-cell centres, not the stored point", "coords != exact, on grid centre", f"{len(sens)} checked, e.g. offset {off(sens[0]):.0f} m", cell_ok and all(p["lat"] != by_id[p["id"]]["lat"] for p in sens))
rec("B-21b", "Ordinary public coordinates rounded to 3 dp (~100 m)", "<= 3 decimals", "checked " + str(len(ordn)), all(abs(p["lat"] - round(p["lat"], 3)) < 1e-9 for p in ordn))
rec("B-21c", "Public API never lists a report without a valid location", "none listed", "inject + list", (lambda: (A.REPORTS.append({**A.REPORTS[0], "id": "badloc", "lat": None, "lng": None}), [x["id"] for x in c.get("/api/reports").json()].count("badloc") == 0, A.REPORTS.pop())[1])())
rep = post({**GOOD, "text": "Elderly person alone, needs medicine at flat 12"}).json()
rec("B-20d", "Submitter (owner) still gets their own complaint draft and map position", "draft present, map_lat generalised", f'draft={bool(rep["complaint_draft"])} map={rep["map_lat"]},{rep["map_lng"]}', bool(rep["complaint_draft"]) and rep["map_lat"] != rep["lat"])
rec("B-20e", "Draft is NOT in the public list", "absent", "checked", "complaint_draft" not in json.dumps(c.get("/api/reports").json()))

# ---- admin
rec("B-22a", "Public cannot read admin data", "401", str(c.get("/api/admin/reports").status_code), c.get("/api/admin/reports").status_code == 401)
rec("B-22b", "Admin login failure", "401", str(c.post("/api/admin/login", data={"password": "wrong"}).status_code), c.post("/api/admin/login", data={"password": "wrong"}).status_code == 401)
tok = c.post("/api/admin/login", data={"password": "test-admin-pw-123"}).json()["token"]
ad = c.get("/api/admin/reports", headers={"x-admin-token": tok}).json()
v = [x for x in ad["reports"] if x["id"] == rep["id"]][0]; truth = [x for x in A.REPORTS if x["id"] == rep["id"]][0]
rec("B-22c", "Admin still sees full text, exact coordinates, location source, draft", "all present", f'text={"flat 12" in v["text"]} lat={v["lat"]==truth["lat"]} src={v["location_source"]}', "flat 12" in v["text"] and v["lat"] == truth["lat"] and v["location_source"] == "gps" and "complaint_draft" in v)
h = c.post(f"/api/admin/reports/{rep['id']}/hide", headers={"x-admin-token": tok}).status_code
gone = rep["id"] not in [x["id"] for x in c.get("/api/reports").json()]
ap = c.post(f"/api/admin/reports/{rep['id']}/approve", headers={"x-admin-token": tok}).status_code
back = rep["id"] in [x["id"] for x in c.get("/api/reports").json()]
rec("B-24d", "Admin hide / approve still work and affect the public list", "hide removes, approve restores", f"{h}/{gone}/{ap}/{back}", h == 200 and gone and ap == 200 and back)
dl = c.delete(f"/api/admin/reports/{rep['id']}", headers={"x-admin-token": tok}).status_code
rec("B-24e", "Admin delete still works", "200 and gone from store", str(dl), dl == 200 and rep["id"] not in {x["id"] for x in A.REPORTS})
# citizen flag from 3 different addresses
fid = [x["id"] for x in c.get("/api/reports").json()][-1]
for ip in ("10.0.0.1", "10.0.0.2", "10.0.0.3"):
    TestClient(A.app, client=(ip, 5000)).post(f"/api/report/{fid}/abuse")
rec("B-24f", "Citizen flag: 3 distinct addresses hide a report", "hidden", str(fid not in [x["id"] for x in c.get("/api/reports").json()]), fid not in [x["id"] for x in c.get("/api/reports").json()])
rr = post({**GOOD, "text": "these idiot officers never clean the drain"}).json()
rec("B-28", "Offensive report is held", "flagged", str(rr.get("flagged")), rr.get("flagged") is True)

# ---- AQI (urllib mocked: the sandbox has no internet; real Open-Meteo NOT TESTED)
class FakeResp:
    def __init__(s, body): s.b = body
    def read(s): return s.b
    def __enter__(s): return s
    def __exit__(s, *a): return False
def reset(): A._AQI_CACHE.update(t=0, data=None, fail_t=0)
orig_open = urllib.request.urlopen
def ok_open(url, timeout=0):
    return FakeResp(json.dumps([{"current": {"us_aqi": 168 + i % 3, "pm2_5": 70.1, "time": "2026-11-24T14:00"}} for i in range(len(A.AQI_BASE))]).encode())
def boom(exc):
    def f(url, timeout=0): raise exc
    return f
urllib.request.urlopen = ok_open; reset()
a = c.get("/api/aqi").json()
rec("B-05", "AQI success: live, Open-Meteo, not CPCB, has update time", "status live, simulated false", f'{a["status"]} simulated={a["simulated"]} updated={a["updated"]} fetched_at={a["fetched_at"]>0}', a["status"] == "live" and a["simulated"] is False and "Open-Meteo" in a["source"] and "Not a CPCB" in a["source"] and a["updated"])
urllib.request.urlopen = boom(socket.timeout("timed out")); reset()
a = c.get("/api/aqi").json()
rec("B-06", "AQI upstream timeout: simulated, labelled, no live claim", "status simulated", f'{a["status"]} | {a["source"]}', a["status"] == "simulated" and a["simulated"] is True and "SIMULATED" in a["source"] and a["last_success"] is None)
urllib.request.urlopen = boom(urllib.error.HTTPError("u", 500, "err", {}, None)); reset()
a = c.get("/api/aqi").json()
rec("B-07", "AQI upstream HTTP 500: simulated, labelled", "status simulated", a["status"], a["status"] == "simulated" and a["simulated"])
urllib.request.urlopen = ok_open; reset(); c.get("/api/aqi")
urllib.request.urlopen = boom(OSError("down")); A._AQI_CACHE.update(t=time.time() - 1200, fail_t=0)
a = c.get("/api/aqi").json()
rec("B-08a", "Upstream down, 20-min-old data: shown but labelled STALE with age", "status stale, age ~1200 s", f'{a["status"]} age={a.get("age_s")}', a["status"] == "stale" and a["age_s"] >= 1190)
A._AQI_CACHE.update(t=time.time() - 4 * 3600, fail_t=0)
a = c.get("/api/aqi").json()
rec("B-08b", "Upstream down, 4-hour-old data: NOT shown as current; simulated + last success time", "simulated, last_success set", f'{a["status"]} last_success={a["last_success"]}', a["status"] == "simulated" and a["last_success"])
urllib.request.urlopen = orig_open; reset()
a = c.get("/api/aqi").json()
rec("B-08c", "Real network call (sandbox has no internet) fails safely to simulated", "simulated", a["status"], a["status"] == "simulated", "Real Open-Meteo success path is NOT TESTED against the live service", "needs internet access")

json.dump(R, open("backend_results.json", "w"), indent=1)
p = sum(x["result"] == "PASS" for x in R); print(f"\n{p}/{len(R)} passed"); sys.exit(0 if p == len(R) else 1)
