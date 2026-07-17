**Scoring (0–10, floor 0):**

**Findings: 6.0 pts max — 0.6 per bug**, for each of the 10 keyed bugs where BOTH hold:
- Line matches the key exactly (A:36 also accepted as A:22 if the stated mechanism is "raw newlines break SSE data framing"; C:7's mechanism at any mention of GNU-vs-BSD date).
- Stated mechanism matches the key's mechanism (grader keyword check — e.g. for A:8 must reference 3.12+/3.14 behavior or RuntimeError/no-running-loop, not a generic "don't use get_event_loop").
Right line + wrong mechanism = 0 pts (not an FP).

**Part D output: 4.0 pts max.** Compare line-by-line, exact string match (including `M4 False`). −0.5 per missing, extra, wrong, or out-of-place line; floor 0. (Exactly right = 4.0; one misplaced line = 3.0, since it's wrong in its position and missing from the right one — count each discrepancy once, max −0.5 per output-line slot.)

**False positives: −0.75 each.** Any finding on a line not in the key — including all six traps, and style/robustness findings on any line. The 12-finding cap prevents shotgunning; findings beyond 12: ignore extras but apply −0.75 each anyway.

**Expected band for a strong frontier model: 5.0–7.0.**
- Likely gets: A:49, C:6, C:7 (moderates), B:5, B:16, and 1–2 of {A:8, B:11, B:27, A:35} → ~3.0–4.2 finding pts. A:36's newline-framing defect and the Datastar 1.0 naming pair should split the field.
- Part D: strong models get 7–10 lines right → 2.5–4.0; `M4 False` and `CB1`-before-`M5` are the expected drop points.
- Traps: expect 1–3 bites (T1 sync-generator and T6 zsh-splitting are the strongest lures, T4 in_array third) → −0.75 to −2.25.
Net: ~5–7. A 9+ requires near-perfect recall of 3.14 asyncio changes, the EventSource parsing algorithm, Datastar 1.0's wire rename, PHP 8 migration trivia, WP return types, zsh-vs-bash expansion rules, AND resisting all six reflex flags — that's the discrimination surface v1 lacked.

**Ceiling insurance:** if both models still tie on findings, Part D's per-line deltas and the FP count are secondary sort keys — three independent axes (recall, restraint, exact simulation) make an exact tie far less likely than v1's single-axis recall score.

Test scripts and verification runs are in `/Users/cminds/claude-tmp/tmp/bench-v2/` if you want to re-check any ground-truth claim.

Stopped at: ⏱ 2026-07-17 16:24:41