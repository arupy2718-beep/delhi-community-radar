"""Builds tests/fixtures.json from the REAL backend (Open-Meteo is mocked: no internet needed). Run from the app folder."""
import os, sys, json, urllib.request
os.environ.pop("ANTHROPIC_API_KEY", None); sys.path.insert(0, ".")
from fastapi.testclient import TestClient
import app as A
c = TestClient(A.app)
class F:
    def __init__(s, b): s.b = b
    def read(s): return s.b
    def __enter__(s): return s
    def __exit__(s, *a): return False
ok = lambda v: (lambda u, timeout=0: F(json.dumps([{"current": {"us_aqi": v + i % 4, "pm2_5": 64.0, "time": "2026-11-24T14:00"}} for i in range(len(A.AQI_BASE))]).encode()))
down = lambda u, timeout=0: (_ for _ in ()).throw(OSError("down"))
reset = lambda: A._AQI_CACHE.update(t=0, data=None, fail_t=0)
urllib.request.urlopen = ok(160); reset()
fx = {"reports": c.get("/api/reports").json(), "stats": c.get("/api/stats").json(), "aqi_live": c.get("/api/aqi").json()}
reset(); urllib.request.urlopen = down; fx["aqi_sim"] = c.get("/api/aqi").json()
reset(); urllib.request.urlopen = ok(170); c.get("/api/aqi"); A._AQI_CACHE["t"] -= 1200; urllib.request.urlopen = down
fx["aqi_stale"] = c.get("/api/aqi").json()
fx["owner"] = c.post("/api/report", data={"text": "Karol Bagh mein ek bujurg akele hain, tabiyat kharab hai", "lat": "28.6519", "lng": "77.1909", "loc_source": "gps"}).json()
fx["sensitive_ids"] = [r["id"] for r in fx["reports"] if r["location_precision"] == "approximate"]
json.dump(fx, open("tests/fixtures.json", "w"))
print("fixtures written")
