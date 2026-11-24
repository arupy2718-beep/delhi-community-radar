"""Compares the CURRENT formula (app.py, unchanged) with two PROPOSALS. Proposals are not wired into the app."""
import math
def current(S, dups, V):                 # dups = merged duplicate REPORTS (cluster_size - 1)
    return min(100, S * 12 + 8 * dups + (15 if V else 0))
def A(S, u, V):                          # u = distinct reporters in the cluster
    s = S * 12 + (24 if V else 0) + min(16, 4 * (u - 1))
    if S == 5 or (S >= 4 and V): s = max(s, 80)          # danger floor
    return min(100, round(s))
def B(S, u, V):
    s = S * 12 + (24 if V else 0) + 16 * (1 - 0.6 ** (u - 1))
    return min(100, round(s))
band = lambda p: "Critical" if p >= 80 else "High" if p >= 60 else "Medium" if p >= 40 else "Low"
# (label, S, V, total_reports, distinct_reporters)
SC = [
 ("1. Lone elderly person, collapsed (sev 5, vulnerable, 1 report)", 5, True, 1, 1),
 ("2. Live wire sparking (sev 5, not vulnerable, 1 report)", 5, False, 1, 1),
 ("3. Elderly alone and unwell (sev 3, vulnerable, 1 report)", 3, True, 1, 1),
 ("4. Sev 4 + vulnerable, 1 report", 4, True, 1, 1),
 ("5. Pothole (sev 2), ONE person submits it 6 times", 2, False, 6, 1),
 ("6. Same pothole (sev 2) reported by 6 different people", 2, False, 6, 6),
 ("7. Garbage (sev 3), 10 different reporters", 3, False, 10, 10),
 ("8. Garbage (sev 3), ONE person submits 10 times", 3, False, 10, 1),
 ("9. Sev 5 + vulnerable + 4 reporters", 5, True, 4, 4),
 ("10. Minor issue (sev 1) near a vulnerable person", 1, True, 1, 1),
]
rows = []
for lab, S, V, n, u in SC:
    c, a, b = current(S, n - 1, V), A(S, u, V), B(S, u, V)
    rows.append((lab, c, band(c), a, band(a), b, band(b)))
    print(f"| {lab} | {c} {band(c)} | {a} {band(a)} | {b} {band(b)} |")
# property checks used as the proposed test plan
import itertools
ok = True
for S, V, u in itertools.product(range(1, 6), (False, True), range(1, 15)):
    for f in (A, B):
        if f(S, u, V) > 100: ok = False
        if S < 5 and f(S + 1, u, V) < f(S, u, V): ok = False
        if f(S, u + 1, V) < f(S, u, V): ok = False
        if V is False and f(S, u, True) < f(S, u, False): ok = False
print("monotonic + capped properties hold:", ok)
print("max possible, A:", max(A(5, 99, True), 0), " B:", B(5, 99, True))
print("A: sev2 never reaches Critical via dups:", max(A(2, u, False) for u in range(1, 99)), "| sev3:", max(A(3, u, False) for u in range(1, 99)))
