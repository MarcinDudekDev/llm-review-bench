---
title: "I tried to run Claude Code on an old model — and fell into a benchmarking rabbit hole"
description: "A one-shot code-review benchmark that scores restraint instead of recall, four models later, and the methodology mistakes that nearly shipped the wrong answer twice."
tags: [llm, benchmarks, claude, evaluation, methodology]
draft: true
---

It started with a boring question: **can I still run Claude Code on Opus 4.6?** It's not in the model picker anymore. Ten minutes of poking later I had my answer (yes — pass the full model ID to `--model`, the picker just hides it). But the real question underneath was the one that wouldn't let go: *is 4.6 actually worse than 4.8, or does it just feel older?*

So I built a benchmark. Then I built a better one. Then I discovered my benchmark was lying to me — twice — and had to fix it. By the end I'd tested four models across four task families, and the most interesting results weren't about which model won. They were about how easy it is to measure the wrong thing and believe the number.

Here's the whole thing, mistakes included. The code is at [github.com/MarcinDudekDev/llm-review-bench](https://github.com/MarcinDudekDev/llm-review-bench).

## The design: score restraint, not recall

Most "find the bugs" evals reward finding things. That's a problem, because frontier models are *very* good at finding things — so good that the eval saturates and tells you nothing. My first task had six planted bugs in a FastAPI + Datastar snippet. Every model found all six. Ceiling hit. Useless.

The half that actually separates good reviewers from noisy ones is the opposite skill: **knowing when to stay quiet.** A reviewer who flags every suspicious-looking line isn't thorough, they're exhausting. So every task in this benchmark ships three kinds of code:

- **Bugs** — real defects, credited only if the model names the actual mechanism.
- **Traps** — code that *looks* wrong but is provably correct on the pinned versions. Flagging a trap costs you a point. This is the discriminator.
- **Neutral** — real-but-stylistic observations that earn neither credit nor penalty.

The traps are the whole game. `in_array` "type juggling" that PHP 8 quietly killed. An unquoted `$var` that would word-split in bash but doesn't in zsh. A sync generator that "blocks the event loop" — except Starlette runs it in a threadpool. Bait a well-read model reflexively flags, and the good models are the ones that don't take it.

## Four tasks, escalating

- **v1** — 6 bugs + 2 traps, one code snippet. Easy. (It ceilinged, as you'll see. Kept as a documented failure.)
- **v2** — 10 obscure, version-specific bugs + 6 traps across Python 3.14 / PHP 8 / zsh, plus an exact-output asyncio prediction. Hard.
- **v3** — 10 shell-command-generation tasks, scored by *executing* the command and matching stdout. No judge.
- **v4** — 18 adversarially-filtered hard command tasks (more below).

v1 and v2 are code review, blind-judged by two other models. v3 and v4 are command generation — the model emits one shell command, the harness runs it in a sandbox and byte-compares stdout to a golden value. Binary, mechanical, no opinion.

## Mistake #1: my benchmark measured the weather, not the model

My very first head-to-head used a 60-second timeout. Result: Opus 4.6 timed out with no output, Opus 4.8 finished in 28 seconds. Clean win for 4.8, obviously.

It was noise. Re-running uncapped, the *same model on the same prompt* swung from 27 seconds to 132 seconds and back. Cost swung 8x on the same model — that's prompt-cache hit/miss state, not economics. My "4.8 is faster" conclusion was a pure artifact of an arbitrary timeout landing on the wrong side of a noisy distribution.

**A tight timeout doesn't measure the model. It measures the API weather that afternoon** — and it will hand you a confident, reproducible-looking, completely wrong answer. I nearly shipped it. The fix was boring: generous timeouts, more trials, report medians with the spread.

## Mistake #2: "make it hard" doesn't make it hard

To separate two frontier models I needed genuinely hard tasks. My first instinct — prompt a strong model to "design a brutal task" — produced a 10/10 ceiling twice. Frontier models are bad at knowing what's hard for other frontier models.

So I used them as **difficulty oracles** instead. Fable and Grok each proposed candidate tasks; every reference command was validated by execution; then each model attempted the *other's* tasks one-shot. Keep only the tasks the opposing strong model gets wrong — those are empirically hard, by construction.

The result was itself a finding: **17 of 18 candidates were solved.** Two capable models could not reliably author a shell task that stumps a frontier peer. The single survivor turned on a platform-specific `%.2f` rounding quirk — unknowable without executing it on that exact host. One-shot BSD shell-command generation is, essentially, saturated for frontier models.

## Mistake #3: I wasn't actually testing what I said I was

Then a simple question from a colleague: *"are you sure they only get one shot?"*

I wasn't. Claude Code runs with tools enabled by default. Nothing stopped a model from creating the input files, running its command, checking the output, and revising — before "answering." The tasks even describe the exact input files. My "one shot, no execution" framing wasn't a guarantee. It was a hope.

The fix made it structural: `--tools ""` so execution is impossible, plus an assertion that `num_turns == 1` on every call (a tool call forces a second turn, which now raises instead of scoring). One-shot is now *proven* per call, not assumed.

Did it change the result? I guessed it would — that tools had been propping up the accuracy ceiling. **I was wrong again.** Under the guaranteed condition both Opus models were still essentially perfect. The ceiling was real. But the "one shot" label is now true, which matters more than whether the number moved.

## The Opus result: a tie, and a price surprise

Under the enforced one-shot condition, across all four tasks:

- **v1 (easy review):** 4.6 wins, 8.0 vs 7.0
- **v2 (hard review):** 4.8 wins, 9.4 vs 8.2
- **v3 (short commands):** tie, both perfect
- **v4 (hard commands):** tie, both essentially perfect (4.6 180/180, 4.8 179/180 — its one miss was the unfair rounding gotcha)

The coherent read: **on review tasks, difficulty picks the model** — 4.6 is better on easy review, 4.8 on hard. On command generation they're indistinguishable. Averaged, it's a statistical tie.

And here's the kicker for anyone choosing between them to save money: **Opus 4.6 is not cheaper than 4.8.** Anthropic priced the entire Opus 4.x line identically — $5 per million input tokens, $25 per million output, both 1M context. There's no economic reason to stay on 4.6. Pick on behavior, not price.

## Sonnet 5 vs Haiku 4.5: finally, a real gap

The Opus tie made the obvious next question: what happens across a *tier* gap? So I ran all four tasks on Sonnet 5 vs Haiku 4.5.

Here the benchmark did exactly what it's supposed to:

- **v3 (short commands):** Sonnet **100/100**, Haiku **93/100** — a clear, consistent gap where both Opus models were perfect.
- **v4 (hard commands):** Sonnet **{{V4_SONNET_RAW}}**, Haiku **{{V4_HAIKU_RAW}}** — Haiku misses a large chunk of the hard set.
- **v1/v2 (review):** Sonnet beats Haiku on both — 8.0 vs 5.5 on easy review, 8.8 vs 6.5 on hard. A consistent ~2.5-point gap where the two Opus models were within a point of each other.

{{ACCURACY_CHART}}

## The surprise nobody expects: Haiku is the *slow* one

I expected Haiku to be less accurate. I did not expect it to be **slow**. On the short-command task:

- **Sonnet 5:** median **12.8s**, $0.0247/run
- **Haiku 4.5:** median **80.9s**, $0.0455/run

Read that again. Haiku — the model whose entire brand is "fast and cheap" — was **6x slower and cost more per run** than Sonnet 5, on the same tasks. It's priced at one-third of Sonnet's per-token rate, yet cost *more*, which means it generated far more tokens.

The culprit is **adaptive thinking.** Haiku 4.5 burns an enormous thinking-token budget on these problems — which simultaneously makes it slow and erases its price advantage. On this workload, the "fast, cheap" model is neither fast nor cheap. If you reach for Haiku to save latency and money on a task that needs any real reasoning, measure it first — you may be paying more for less.

{{LATENCY_CHART}}

## What this is, and what it isn't

Every number here is directional. Small n, one machine, one afternoon of API weather. The review accuracy rests on LLM judges scoring against a rubric another LLM wrote — I mitigate with two judges from different labs and blind shuffling; I don't pretend to eliminate it. v3 and v4 are mechanically scored, which I trust more. The command tasks saturate for frontier models, so they discriminate on precision, not raw capability.

But the methodology holds up, and the methodology is the point:

1. **Score restraint, not recall** — the traps are what separate models once recall saturates.
2. **Timeouts measure weather** — don't report a speed winner at small n.
3. **Enforce your constraints structurally** — "one shot" has to be `--tools ""` + a turn-count assertion, not a promise in the prompt.
4. **Use strong models as difficulty oracles** — but know that they mostly can't stump each other.
5. **"Fast and cheap" is a workload-dependent claim** — Haiku's adaptive thinking made it the slowest and not the cheapest here.

Full harness, all four tasks, every result file, and the mistakes documented in the README: [github.com/MarcinDudekDev/llm-review-bench](https://github.com/MarcinDudekDev/llm-review-bench).
