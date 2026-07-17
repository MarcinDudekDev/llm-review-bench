All items below were empirically verified on Python 3.14.4, PHP 8.5 (8.3-compatible behaviors), zsh 5.9 / macOS 15, Starlette 0.50.

**BUGS (10):**

1. **A:8 — SUBTLE (3.14 version-specific).** `asyncio.get_event_loop()` with no running loop raises `RuntimeError: There is no current event loop` on Python 3.14 (the auto-create fallback was removed). The app crashes **at import**. Verified: raises on 3.14.4.
2. **A:35 — SUBTLE (Datastar version-specific).** `datastar-merge-fragments` is the pre-1.0 event name. Datastar 1.0 only handles `datastar-patch-elements` (and `datastar-patch-signals`); a 1.0 client silently ignores this event. Nothing ever renders.
3. **A:36 — SUBTLE (SSE spec-level).** Two defects accepted on this line, either earns credit: (a) `fragments` is the pre-1.0 data prefix — 1.0 requires `elements`; (b) `html` contains raw `\n` (from line 22), so the 2nd/3rd HTML lines become SSE lines without a `data:` prefix — per the WHATWG EventSource parser they're treated as unknown fields and **silently dropped**, truncating the payload. Multi-line payloads must be split into one `data:` line each. (b) is the discriminator.
4. **A:49 — MODERATE.** `asyncio.TaskGroup` wraps child exceptions in an `ExceptionGroup`; plain `except ValueError` does not catch it (needs `except*`). Verified: the group escapes.
5. **B:5 — SUBTLE (PHP 8 version-specific).** Unparenthesized nested ternary is a **compile-time fatal error** in PHP 8 ("Unparenthesized `a ? b : c ? d : e` is not supported") — the whole file fails to load. Verified.
6. **B:11 — SUBTLE.** Array union `+` keeps the **left** operand's value for duplicate keys, so `$defaults + $user_args` silently discards every user setting that has a default. Verified: user's `per_page=50` lost, `10` kept. (Correct: `$user_args + $defaults` or `wp_parse_args`.)
7. **B:16 — SUBTLE (WP API trivia).** `wp_verify_nonce()` returns `1`, `2`, or `false` — never `true`. `=== true` is always false, so **every** save dies with 403, valid nonce or not.
8. **B:27 — SUBTLE (PHP 8 version-specific).** Comparator returns bool: deprecated in PHP 8 (`Returning bool from comparison function is deprecated`) and can never return `-1`, so "less" and "equal" are indistinguishable → incorrect ordering. Verified: emits deprecation + mis-sorts.
9. **C:6 — MODERATE.** zsh arrays are 1-indexed; `$files[0]` is **empty** (verified). `first` is `""`, so line 10 runs `cp $dest/` → error.
10. **C:7 — MODERATE.** BSD `date` has no `-d` flag (`date: illegal option -- d`, verified); needs `date -v-1d`. With `set -e`… (the command-substitution failure leaves `stamp` empty / errors) — flag it as GNU-only flag on macOS.

**TRAPS (6) — correct code; flagging any of these is a false positive:**

- **T1, A:11–19.** "Sync generator in `StreamingResponse` blocks the event loop" — **wrong**. Starlette wraps sync iterators in `iterate_in_threadpool` (verified in Starlette 0.50 source). The `time.sleep` runs in a worker thread. Correct code.
- **T2, A:37.** `": keepalive\n\n"` — a line starting with `:` is a **comment** per the SSE spec, the standard keep-alive idiom. Not malformed.
- **T3, A:22.** f-string reusing the outer quote character inside `{item["id"]}` — **valid since Python 3.12** (PEP 701); task pins 3.14. Verified. (SyntaxError claim = FP.)
- **T4, B:26.** "Non-strict `in_array` allows type juggling / `0` matches" — **wrong on PHP 8**: `0 == 'draft'` is `false` since the PHP 8 string↔int comparison change (verified), and both needle and haystack are strings anyway. Correct code.
- **T5, B:25.** "Arrow function missing `use ($status)`" — **wrong**: `fn()` auto-captures by value. Correct code.
- **T6, C:9.** "Unquoted `$dest` word-splits (it contains a space!)" — **wrong in zsh**: unquoted parameter expansions are NOT word-split (verified: `[wp 20260716]` stays one arg). Correct in zsh (would be a bug in bash — that's the bait).

**PART D exact output (verified by execution, deterministic across runs):**
```
M1
Q3
M2
S1-in
M3
C2
M4 False
S1-out
CB1
M5
```
Why the four counterintuitive lines: `S2-in` never prints (t2 cancelled before its first step ever runs); `Q3` — awaiting a bare coroutine runs it inline without yielding to the loop; `S1-in` lands before `M3` (t1's first step runs during main's `sleep(0)`); `M4 False` — awaiting the already-done `t2` returns without yielding, so t1's second step hasn't run yet; `CB1` before `M5` — the done-callback was registered before `main`'s await, so it's scheduled first.