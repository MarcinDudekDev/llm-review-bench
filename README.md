# llm-review-bench

A small, honest harness for comparing LLMs head-to-head on **subtle code review** — finding real bugs
in code that looks fine, without inventing bugs that aren't there.

It was built to answer one question: *is Claude Opus 4.6 actually worse than 4.8?* The answer turned
out to be less obvious than expected, and the **methodology failures were more interesting than the
result**. Both are documented here, including the ones that made us throw away our first conclusion.

Works with any model — Anthropic via the Claude Code CLI, xAI Grok via its CLI, and anything on
OpenRouter. Adding a model is a config entry, not a code change.

---

## Why precision, not recall

Most "find the bugs" evals reward finding things. Frontier models are already very good at that — in
our v1 task, **every model found 6/6 planted bugs and the eval told us nothing**. Ceiling hit.

So this benchmark scores the other half: **planted traps** — code that looks wrong but is provably
correct on the pinned versions. Flagging a trap costs you a point. This measures the thing that
actually matters in review: knowing when to stay quiet. A model that reports everything is not a good
reviewer, it's a noisy one.

Every task therefore ships:

- **bugs** — real defects, with the exact mechanism required for credit
- **traps** — correct code that bait-flags a well-read model (`in_array` "type juggling" that PHP 8
  killed; unquoted zsh vars that zsh doesn't word-split; a sync generator that Starlette threadpools)
- **neutral** — real-but-stylistic observations that earn neither credit nor penalty

## Tasks

| Task | Content | Discriminates? |
|---|---|---|
| `tasks/v1` | FastAPI + Datastar SSE snippet: 6 bugs, 2 traps | **No** — all contenders hit 6/6. Kept as a documented ceiling failure. |
| `tasks/v2` | 4 parts (Python 3.14 / PHP 8.3+WP / zsh / exact-output asyncio prediction): 10 bugs, 6 traps | Designed to break the ceiling. |

v2 leans on **version-specific semantics** rather than classic footguns, because the classics
(mutable default arg, dict-mutation-during-iteration, `lru_cache` on async) are free points for any
frontier model. Instead: `asyncio.get_event_loop()` raising on 3.14, PHP 8's unparenthesized-ternary
fatal, `wp_verify_nonce()` returning `1|2|false` and never `true`, Datastar 1.0's renamed SSE events.

Part D asks for the **exact stdout** of a deterministic asyncio program. Exact-match scoring resists
partial-credit ceilings. Its answer key is not taken on faith — run it:

```bash
python3 tasks/v2/verify_part_d.py   # must match answer_key.md byte for byte
```

The task and key were authored by a *third* model (Claude Fable 5), not by either contender, then
independently verified.

## Usage

```bash
python3 harness/run_bench.py --task v2 --trials 3
python3 harness/run_bench.py --task v2 --models opus-4-6,opus-4-8 --trials 5
python3 harness/judge.py --task v2 --judges fable-5,grok
```

Add a model in `harness/models.json`:

```json
{ "id": "gpt-5", "adapter": "openrouter", "model": "openai/gpt-5", "label": "GPT-5" }
```

Adapters live in `harness/adapters.py`; a new provider is one function returning `(text, cost)`.

Judging is **blind**: answers are anonymised to A/B/C, shuffled with a fixed seed, and the
model→letter map is withheld until scoring. Use two judges from different labs and check they agree.

---

## Results

### v1 — the ceiling failure

| | Opus 4.6 | Opus 4.8 |
|---|---|---|
| Bugs found | 6/6 | 6/6 |
| Traps avoided | 2/2 | 2/2 |
| False positives | 0 | 1 |
| Score (Fable / Grok, blind) | **10.0 / 10.0** | 9.0 / 9.0 |

Both judges independently returned identical scores and the same winner: **4.6**, purely because 4.8
invented a bug. It claimed `purge_expired` races with `get_cached` by touching a dict without the
lock — but `purge_expired` contains no `await`, so under asyncio's single-threaded loop it cannot be
preempted. There is no race. On this task the difference wasn't knowledge, it was **restraint**.

Caveat that matters more than the result: **n=1 task, both at the recall ceiling, decided by a single
false positive.** That is directional, not a verdict. Which is exactly why v2 exists.

### The mistake worth copying

Our first run used a **60-second timeout**. Result: 4.6 timed out with no output, 4.8 finished in
27.8s. Clean win for 4.8, obviously.

It was noise. Re-running uncapped:

| Model | Trial 1 | Trial 2 | Trial 3 |
|---|---|---|---|
| Opus 4.6 | 48.0s / $0.069 | 57.1s / $0.262 | — |
| Opus 4.8 | 27.8s / $0.277 | **132.5s** / $0.032 | 27.1s / $0.265 |

The *same model* on the *same prompt* varied **5x in latency** and **8x in cost**. The cost swing is
prompt-cache hit/miss state; the latency swing is API weather. Both dwarf any between-model
difference at this sample size.

**So this harness does not report a speed or cost winner, and neither should you at n<10.** A tight
timeout doesn't measure the model, it measures the weather — and it will hand you a confident,
reproducible-looking, completely wrong answer. We nearly shipped one.

`--timeout` defaults to a generous 300s for that reason. If you want latency numbers, run ≥10
interleaved trials and report medians with the spread, not means.

## Known limitations

- **Small n.** Everything here is directional. Model-vs-model gaps at n=1–3 are not real.
- **Judge bias.** Judges are LLMs scoring against a rubric written by another LLM. We mitigate with
  two judges from different labs + blind shuffling; we don't eliminate it.
- **Answer keys can be wrong.** v2's Part D is executable and verified. The prose findings are not
  machine-checkable — they were cross-checked by hand, but treat them as fallible.
- **Contender-as-judge.** Prefer judges outside the contender set.
- **Trap design is the hard part.** A bad trap (one that's actually a real bug) silently punishes the
  best model. Traps deserve more scrutiny than bugs.

## License

MIT.
