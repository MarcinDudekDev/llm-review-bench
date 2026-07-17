Score = sum of bug points, minus false-positive penalties, clamped to [0, 10].

Bug points (must identify the correct line ±1 AND the actual mechanism — naming the line but the wrong reason earns half points, rounded down to nearest 0.5):
- B1 (lru_cache on async) — 2.0
- B2 (missing SSE blank-line terminator) — 2.0
- B4 (unreferenced create_task / GC) — 2.0
- B3 (dict repr is not JSON) — 1.5
- B5 (dict mutated during iteration) — 1.5
- B6 (mutable default argument) — 1.0
Total available: 10.0

False positives — subtract 1.0 each:
- Flagging trap T1 (module-level Lock) or trap T2 ("except Exception swallows CancelledError") — these are the discriminators; a strong model stays silent on both.
- Any other claim of a defect that is not in B1-B6 and not in the NEUTRAL list (e.g. inventing a bug in `len(slug) * 7 % 100`, claiming `time.monotonic` is wrong, claiming the TTL comparison is off-by-one).

NOT penalized, NOT credited (neutral): N1, N2, N3 from the answer key, and duplicate restatements of an already-credited bug.

Mechanical notes for the judge:
- B2 and B3 are both on L53 and must be listed as separate entries to earn both; a single entry vaguely saying "the SSE line is wrong" earns whichever one mechanism it actually states (or 0 if neither mechanism is stated).
- Format compliance: ignore minor format deviations (extra prose, missing `L` prefix) for scoring accuracy, but if the answer exceeds 8 entries, score only the first 8 in order.
- Expected discrimination: a mediocre model typically finds B5 + B6 (+ maybe B3) and flags one or both traps → ~2.5-4.0. A strong model finds B1, B2, B4 and avoids both traps → 8.0-10.0.

Stopped at: ⏱ 2026-07-17 14:32:11