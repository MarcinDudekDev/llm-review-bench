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

### v2 — the ceiling broke, and so did the verdict

v2 discriminated: no model got a stable 10/10, and the four models spread out. It also produced the
most honest possible outcome — **the winner between 4.6 and 4.8 flips depending on the trial.**

Blind-judged by Fable 5 and Grok (both judges agreed on every score to the decimal):

| Model | Trial 2 | Trial 3 | Mean | What separated it |
|---|---|---|---|---|
| Opus 4.8 | **10.0** | 8.5 | **9.25** | Only model to hit a clean 10/10 (trial 2). Fell into trap T6 in trial 3 — flagged unquoted zsh `$dest` as word-splitting (zsh doesn't), −1.5. |
| Opus 4.6 | 8.8 | **9.4** | **9.1** | Consistently missed **A:35** (Datastar 1.0 event rename) both trials. No false positives. |
| Grok | 8.8 | 8.8 | 8.8 | Most stable. Missed `B:5`, `B:27` (PHP-specific) both trials. |
| Fable 5 | 9.5 | 10.0 | 9.5 | Highest — but see self-bias note. Botched its *own* Part D in trial 2 (dropped `S1-out`). |

**4.8 (9.25) vs 4.6 (9.1) is a tie at this sample size.** 4.8 has the higher ceiling — it's the only
model that produced a flawless answer — but it's also the one that took trap bait when it slipped.
4.6 never scored a 10 (it kept missing the Datastar rename) but never fell below 8.8 either. Higher
variance, higher peak vs. lower variance, lower peak. Two trials cannot rank these two models, and the
harness is honest enough to show that rather than average it away.

Latency was the one consistent signal: on v2, **4.8 ran ~2-3x faster** (48-105s vs 159-182s, plus one
4.6 timeout at the 300s cap). Unlike v1, this held across every trial — the harder task pulled the
latency gap out of the noise floor, even as the accuracy gap stayed inside it.

**Two documented judge-integrity issues, both visible in the data above:**
1. **Self-bias.** Fable judged a field that included its own (anonymised) answer. In trial 2 it scored
   itself 9.5 while Grok scored the same answer 8.5. Prefer judges outside the contender set.
2. **The key can bite its author.** Fable *wrote* the Part D key and then got Part D wrong as a
   contender — proof that authoring ground truth doesn't make a model immune to the task.

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

### v3 — deterministic, execution-scored, n=10

v3 removes the judge entirely. Each of 10 tasks asks for **one shell command**; the harness runs it in
a sandbox and compares stdout to a golden value (`harness/exec_score.py`). Binary 1/0, no opinion. The
tasks are BSD-vs-GNU and field-splitting traps (Q5's `\+` doing nothing on BSD sed, Q7's `comm`
needing sorted input, Q10's unterminated-line `wc -l`). Reference commands are validated against the
goldens before any model runs. Ran at **n=10** — the sample size v1/v2 lacked.

| Model | Accuracy (n=10) | Latency median | mean | sd | min–max |
|---|---|---|---|---|---|
| Opus 4.6 | **100/100** | **17.0s** | 18.1s | 5.5 | 10.1–26.9 |
| Opus 4.8 | **100/100** | 23.9s | 25.4s | 2.9 | 22.1–30.2 |

**Accuracy tied at ceiling** (both perfect) — v3 doesn't discriminate on correctness. But the point
was speed, measured properly:

**On short tasks, Opus 4.6 is reliably *faster* — the opposite of v2.** Paired per-trial delta
(4.8 − 4.6) averages **+7.3s**, 4.6 wins **8/10** trials, paired **t(9)=3.80, p≈0.0001**. This is not
noise; n=10 pulled a real effect out of the variance that swamped v1.

And it **reverses the v2 latency finding**, where 4.8 ran 2-3x faster on the *hard* task. Both are true:

> **Latency ranking depends on task difficulty.** 4.6 is snappier on easy work but spends much longer
> thinking on hard problems; 4.8's latency is flatter across both (note 4.8's sd is ~half of 4.6's).
> "Which model is faster" has no task-independent answer — which is exactly the kind of claim a single
> short benchmark run will confidently get wrong.

The earlier "4.8 is faster" line from the v2 section is therefore not general. On this machine, for
short deterministic commands, 4.6 wins on speed and ties on accuracy.

### v4 — adversarially filtered, one-shot GUARANTEED, n=10

v4 tests whether harder tasks separate the models, and fixes a validity hole the earlier versions had.

**The one-shot hole.** v1–v3 called models through `claude -p` with **tools enabled by default**. Nothing
stopped a model from creating the described input files, running its command, and revising before
answering — which would make the "one shot, no execution" framing false and could inflate accuracy. A
`num_turns` probe showed the models happened to answer in a single turn, but that was luck, not a
guarantee. v4 closes it: **`--tools ""`** makes execution structurally impossible, and the harness
**asserts `num_turns == 1`** on every call (a tool call forces a second turn), so one-shot is proven,
not assumed.

**It did not change the ceiling.** I initially guessed tools had propped up the 18/18 scores. Wrong —
under the guaranteed condition both models are still essentially perfect. The ceiling is real.

**Building hard tasks (adversarial filter).** "Make it hard" prompting gave a 10/10 ceiling twice, so
v4 uses Fable and Grok as difficulty oracles: each proposes candidates, every reference command is
validated by execution, then each model attempts the *other's* tasks one-shot. **17 of 18 were solved.**
Only Fable's Q5 stumped the opposing peer (Grok) — and Q5 turns on this host's libm `%.2f` rounding,
unknowable without running it. Finding: **frontier models can't easily author a shell task that stumps
a frontier peer.** v4 runs all 18 validated tasks against the contenders.

**Result (n=10, tools off, one-shot proven):**

| Model | Accuracy | Latency median | The one miss |
|---|---|---|---|
| Opus 4.6 | **180/180** | 142.5s | — never missed |
| Opus 4.8 | 179/180 | 124.2s | Q5 once (the platform rounding gotcha) |

**Accuracy is saturated even here** — 4.6 perfect, 4.8's lone slip is an arguably unfair task. Shell
command generation does not separate these two models on correctness, at any difficulty this method
could produce.

**Latency flips the other way from v3:** on the *hard* set 4.8 is faster (median 124s vs 142s), but only
a trend (paired t(9)=−1.69, not significant). v3 had 4.6 *significantly* faster on *easy* tasks. Taken
together that supports "latency ranking depends on task difficulty" — 4.6 quicker on easy work, 4.8
quicker on hard — though only the easy-task direction clears significance at n=10.

> **One-shot caveat for v1–v3:** those runs had tools available (fair, since both models did, but the
> "one shot" label was not strictly enforced). Only v4 guarantees it. Re-running v1–v3 under `--tools ""`
> is left as future work; v4's result (ceiling holds without tools) suggests it would not move much.

### v1–v3 re-run under enforced one-shot (with cost + total time)

The earlier caveat — v1–v3 ran with tools available — is now closed. All three were re-run at n=5 under
`--tools ""` + `num_turns==1` assertion. v1/v2 accuracy is blind-judged (Fable + Grok agreed on every
score); v1/v2 accuracy is trial-1 only, cost/time is all 5 runs; v3 is exec-scored across all 5.

**Cost + total time to answer the full question set (median per run, tools off):**

| Task | Model | Time (median) | Cost (median) | Cost (5-run total) |
|---|---|---|---|---|
| v1 (6-bug review) | 4.6 | 46.7s | $0.069 | $0.61 |
| v1 | 4.8 | **24.7s** | $0.079 | $0.89 |
| v2 (hard review) | 4.6 | 224.0s | $0.301 | $1.89 |
| v2 | 4.8 | **174.0s** | $0.394 | $2.11 |
| v3 (10 commands) | 4.6 | **17.8s** | $0.036 | $0.49 |
| v3 | 4.8 | 22.4s | $0.054 | $0.38 |

**Accuracy under enforced one-shot:**

| Task | 4.6 | 4.8 | Winner |
|---|---|---|---|
| v1 easy review | **8.0** | 7.0 | 4.6 |
| v2 hard review | 8.2 | **9.4** | 4.8 |
| v3 commands | 50/50 | 50/50 | tie |

**What enforcing one-shot changed:** the winner *direction* held vs the tools-enabled runs (easy→4.6,
hard→4.8, commands→tie), but absolute review scores dropped now that models can't verify — v1 went from
10/9 to 8/7. So tools *were* inflating the review scores, just not the winner.

**The coherent finding — on review tasks, difficulty picks the model:** 4.6 is better on *easy* review,
4.8 on *hard* review. Command generation is tied at ceiling.

**Latency is task-TYPE dependent, not difficulty-dependent** — correcting the tidier story from the v3/v4
sections. 4.8 is faster on *both* review tasks (v1 and v2), but 4.6 is faster on command generation (v3).
There is no stable "faster model"; it flips with the kind of task, not just its hardness.

### Four-model comparison: Sonnet 5 and Haiku 4.5

The Opus tie raised the obvious question — what happens across a real *tier* gap? So all four tasks
were run on **Claude Sonnet 5** and **Claude Haiku 4.5** under the same enforced one-shot condition
(`--tools ""` + `num_turns==1`). This is where the benchmark finally separated models cleanly.

Accuracy — review tasks are the 0–10 judged score (both judges agreed); command tasks are exec-scored totals:

| Task | Opus 4.6 | Opus 4.8 | Sonnet 5 | Haiku 4.5 |
|---|---|---|---|---|
| v1 easy review | 8.0 | 7.0 | 8.0 | **5.5** |
| v2 hard review | 8.2 | 9.4 | 8.8 | **6.5** |
| v3 short commands | 100/100 | 100/100 | 100/100 | 93/100 |
| v4 hard commands | 180/180 | 179/180 | 179/180 | **122/180** |

Median latency (seconds), same runs:

| Task | Opus 4.6 | Opus 4.8 | Sonnet 5 | Haiku 4.5 |
|---|---|---|---|---|
| v1 | 46.7 | 24.7 | **10.6** | 112.2 |
| v2 | 224 | 174 | **115** | 153 |
| v3 | 17.8 | 22.4 | **12.8** | 80.9 |
| v4 | 143 | 124 | **93** | 193 |

Charts: `blog/chart-1.png` (accuracy) and `blog/chart-2.png` (latency).

**Two findings the Opus-vs-Opus pairing never produced:**

1. **Sonnet 5 is the value winner.** It matched Opus 4.8 on the hard command set (179/180), stayed within
   a point on hard review, ran the **fastest of all four models on every task**, and lists at a third of
   Opus pricing ($3/$15 vs $5/$25). On this data it's the sensible default for review + command work.
2. **Haiku 4.5 is both the least accurate *and* the slowest model.** It drops to 122/180 on hard commands
   and 5.5/10 on easy review, and it's the slowest model on v1/v3/v4 — 80.9s vs Sonnet's 12.8s on short
   commands. The cause is **adaptive thinking**: Haiku burns a large thinking-token budget even on simple
   tasks. On short commands (v3) that budget makes it *cost more per run than Sonnet* despite a third the
   per-token rate. Cost nuance: this inversion only happens on v3 — on v1/v2/v4 Haiku is still the cheapest
   of the four, just the slowest and least accurate. It's slow everywhere; it's only not-cheap on the one
   task where you'd least expect it. Reach for it on work that needs real reasoning and measure first.

Consolidated data for all four models is in `results/ALL_RESULTS.json`; the Sonnet/Haiku summary is in
`results/sonnet_haiku_summary.json`. A full research-paper writeup of the whole investigation lives in `blog/`.

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
