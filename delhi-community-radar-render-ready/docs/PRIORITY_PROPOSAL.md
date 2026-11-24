# Proposal: priority scoring (NOT implemented, awaiting your approval)

The formula in `app.py` is unchanged: `min(100, severity*12 + 8*(cluster_size-1) + 15 if vulnerable)`.

## Problems found (reproduced by running the code)
1. **Duplicates can outrank danger.** Severity 2 + 5 duplicates = 64 (High). Severity 3 with a vulnerable person alone = 51 (Medium).
2. **A single worst case is never "Critical".** Severity 5 + vulnerable, one report = 75 (High). Critical (80+) needs duplicates.
3. **Duplicates are unbounded and counted per report, not per person.** One person submitting a severity-3 garbage report 10 times scores 100 (Critical). There is no reporter identity at all.
4. **Merging can hide separate people.** Two different elderly people within 700 m become one cluster, so one case can be lost. Cluster logic is also greedy and can leave orphan clusters.
5. **The AI's severity is trusted as-is** (1-5 clamp only). A wrong severity moves the score by 12 points per step.

## Proposal A: bounded additive score + danger floor
- `score = 12*severity + 24*(vulnerable) + min(16, 4*(distinct_reporters-1))`, capped at 100.
- **Danger floor:** severity 5, or severity >= 4 with a vulnerable person, scores at least 80 (Critical).
- Vulnerable weight raised 15 -> 24 so that severity 3 + vulnerable reaches High (60).
- Max without floor: 60+24+16 = 100, so the cap is never what limits it.

## Proposal B: diminishing returns + a separate urgent lane (no score override)
- `score = 12*severity + 24*(vulnerable) + 16*(1 - 0.6^(distinct_reporters-1))` (each extra reporter counts less).
- Cases with severity 5, or severity >= 4 with a vulnerable person, go into an **"Urgent" lane shown above the ranked list**, sorted by score inside the lane. The number itself is not distorted.

## Worked examples (computed by `docs/priority_scenarios.py` from the same code)
| Scenario | Current | A | B |
|---|---|---|---|
| 1. Lone elderly person collapsed (sev 5, vulnerable) | 75 High | 84 Critical | 84 Critical |
| 2. Live wire sparking (sev 5, not vulnerable) | 60 High | 80 Critical | 60 High (but Urgent lane) |
| 3. Elderly alone and unwell (sev 3, vulnerable) | 51 Medium | 60 High | 60 High |
| 4. Sev 4 + vulnerable, 1 report | 63 High | 80 Critical | 72 High (Urgent lane) |
| 5. Pothole (sev 2), ONE person submits 6 times | 64 High | 24 Low | 24 Low |
| 6. Same pothole, 6 different people | 64 High | 40 Medium | 39 Low |
| 7. Garbage (sev 3), 10 different reporters | 100 Critical | 52 Medium | 52 Medium |
| 8. Garbage (sev 3), ONE person submits 10 times | 100 Critical | 36 Low | 36 Low |
| 9. Sev 5 + vulnerable + 4 reporters | 99 Critical | 96 Critical | 97 Critical |
| 10. Minor issue (sev 1) near a vulnerable person | 27 Low | 36 Low | 36 Low |

**My recommendation:** A's danger floor is simple to explain to judges, but it turns one wrong AI severity into a false Critical. B is gentler on the number but needs a UI change (the lane). I would take **B's diminishing returns plus A's floor, shown as "Urgent, needs human verification"**, and decide after you see the test results below. This is a judgment call: both are defensible.

## Repeated submissions by one person
No accounts exist. Use a salted hash of (IP + browser) with a 24 h life, never stored raw, as a reporter key. Same key = counted once for urgency (still shown as "repeat report"). Limits: shared IPs/NAT undercount, and behind Render's proxy the real client IP needs `--proxy-headers`/`X-Forwarded-For` handling, or a per-browser random token. A determined attacker can still rotate devices; this stops accidental and casual inflation, not abuse. Pair with rate limiting.

## Duplicate rules (clustering)
- Radius per category instead of a flat 700 m: pothole ~50-100 m, streetlight ~100 m, waterlogging ~300 m, garbage ~300 m, air pollution ~1-2 km (these radii are my starting suggestions, to be tuned on data).
- **Never auto-merge "Elderly & Vulnerable Help" reports** unless very close (~50 m) and similar in text: they are different people.
- Make merging transitive and consistent (fix the orphan-cluster case).

## How to test it
1. Unit tests: score <= 100; monotonic (higher severity, adding vulnerable, adding a distinct reporter never lowers the score; I already ran these properties over severity 1-5 x vulnerable x 1-14 reporters for A and B and they hold); same reporter key counts once.
2. A labelled set of ~50 realistic reports (Hindi, Hinglish, English) with a human-assigned urgency; compare rank agreement and Critical precision/recall against the current formula.
3. Adversarial cases: 10 identical submissions, spam, wrong AI severity (inject 5 for a trivial issue and confirm the human-verification flag appears).
4. Judges' view: show the table above live.
