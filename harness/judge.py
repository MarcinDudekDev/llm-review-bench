#!/usr/bin/env python3
"""Blind-judge benchmark answers against the answer key.

    python3 harness/judge.py --task v2 --judges fable-5,grok

Answers are anonymised to A/B/C..., shuffled with a fixed seed, and the
model->letter map is withheld from the judge and only restored when scoring.
Judges should not be contenders in the same run; if one is, its own answer
still appears anonymised, which it may or may not recognise. Prefer a judge
that is not in the contender set.
"""
import argparse
import json
import pathlib
import random
import re
import string

from adapters import ADAPTERS

ROOT = pathlib.Path(__file__).resolve().parent.parent
LETTERS = string.ascii_uppercase

TEMPLATE = """You are grading anonymous model answers to a code-review benchmark.
Grade ONLY against the key and rubric below. Do not speculate about which model
wrote which answer; identity is irrelevant and unknown to you.

===ANSWER_KEY===
{key}

===RUBRIC===
{rubric}

{answers}

Grade every answer independently. Output ONLY lines in this exact form, one block per answer:
<LETTER>_SCORE: <n>/10
<LETTER>_FOUND: <ids of correct findings>
<LETTER>_FALSE_POSITIVES: <ids/desc with penalties applied, or none>
Then a final line:
RANKING: <letters best to worst, comma separated>
"""


def build_prompt(task, answers):
    key = (ROOT / f"tasks/{task}/answer_key.md").read_text()
    rubric = (ROOT / f"tasks/{task}/rubric.md").read_text()
    blocks = "\n\n".join(
        f"===ANSWER_{L}===\n{txt}" for L, txt in answers
    )
    return TEMPLATE.format(key=key, rubric=rubric, answers=blocks)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", default="v2")
    ap.add_argument("--judges", default="fable-5,grok")
    ap.add_argument("--trial", type=int, default=1, help="Which trial's answers to grade")
    ap.add_argument("--seed", type=int, default=1337)
    args = ap.parse_args()

    rows = json.loads((ROOT / f"results/{args.task}_runs.json").read_text())
    picked = [r for r in rows if r["trial"] == args.trial and r["output"] and not r["error"]]
    if len(picked) < 2:
        raise SystemExit(f"need >=2 usable answers for trial {args.trial}, got {len(picked)}")

    if len(picked) > len(LETTERS):
        raise SystemExit(f"{len(picked)} answers exceeds {len(LETTERS)} anonymisation letters")
    random.Random(args.seed).shuffle(picked)
    mapping = {LETTERS[i]: r["model_id"] for i, r in enumerate(picked)}
    answers = [(LETTERS[i], strip_ts(r["output"])) for i, r in enumerate(picked)]
    prompt = build_prompt(args.task, answers)

    specs = {s["id"]: s for s in json.loads((ROOT / "harness/models.json").read_text())["models"]}
    verdicts = {}
    for jid in args.judges.split(","):
        spec = specs[jid]
        print(f"--- judge: {jid} ---", flush=True)
        text, _ = ADAPTERS[spec["adapter"]](spec, prompt, 600)
        verdicts[jid] = text
        print(text.strip()[:800], flush=True)

    out = {"mapping": mapping, "verdicts": verdicts, "trial": args.trial}
    (ROOT / f"results/{args.task}_judgement.json").write_text(json.dumps(out, indent=2))
    print("\n=== BLIND REVEAL ===")
    for L, m in mapping.items():
        print(f"  {L} = {m}")


def strip_ts(text):
    """Drop the trailing 'Stopped at: ...' line some CLI configs append."""
    return re.split(r"\nStopped at:", text)[0].strip()


if __name__ == "__main__":
    main()
