#!/usr/bin/env python3
"""Adversarial difficulty filter for v4.

Two strong models (Fable, Grok) each propose candidate tasks. We:
  1. validate every candidate (reference_command must reproduce golden),
  2. have the OPPOSING strong model attempt each valid task one-shot,
  3. keep only tasks the opposing model gets WRONG — empirically hard.

The survivors become v4, then get run against the contenders (4.6/4.8).
A task a capable solver fails is a discriminator by construction; "make it
hard" prompting alone gave a 10/10 ceiling twice.
"""
import json
import pathlib
import re
import time

from adapters import ADAPTERS
from exec_score import score_one

ROOT = pathlib.Path(__file__).resolve().parent.parent
BENCH = pathlib.Path("/Users/cminds/claude-tmp/main/bench")
LINE = re.compile(r"^\s*([A-Z]?Q?\d+|G\d+)\s*:\s*(.*?)\s*$")

SOLVE_SYS = (
    "You are given ONE shell task. Think as long as you need, but emit exactly "
    "one line: the raw one-line shell command, no explanation, no code fences, "
    "no backticks. Target: macOS /bin/bash, BSD sed/awk/sort/wc/grep, python3 and "
    "jq available, NO GNU coreutils. Its stdout will be compared byte-for-byte to "
    "a hidden golden."
)


def solve_one(spec_model, task):
    prompt = SOLVE_SYS + "\n\nTASK:\n" + task["prompt"] + "\n\nOutput only the command."
    t0 = time.monotonic()
    try:
        text, _ = ADAPTERS[spec_model["adapter"]](spec_model, prompt, 240)
    except Exception as e:
        # infra failure — return None score so the caller does NOT count this as
        # an empirically-failed solve (which would falsely promote the task to v4)
        return "", None, f"solver_error: {type(e).__name__}", round(time.monotonic() - t0, 1)
    cmd = ""
    for ln in (text or "").splitlines():
        ln = ln.strip().strip("`").strip()
        if ln and not ln.lower().startswith(("here", "the ", "this", "note")):
            cmd = ln
            break  # take the FIRST command line (models emit the command first)
    if not cmd:
        cmd = text.strip().splitlines()[-1].strip("`").strip() if text.strip() else ""
    s, why = score_one(cmd, task.get("setup", ""), task["golden"])
    return cmd, s, why, round(time.monotonic() - t0, 1)


def load_specs():
    m = {s["id"]: s for s in json.loads((ROOT / "harness/models.json").read_text())["models"]}
    return m


def main():
    specs = load_specs()
    fable_tasks = json.loads((BENCH / "cand_fable.json").read_text())["tasks"]
    grok_tasks = json.loads((BENCH / "cand_grok.json").read_text())["tasks"]

    # 1) validate: reference must reproduce golden
    def valid(ts, tag):
        keep = []
        for t in ts:
            s, why = score_one(t["reference_command"], t.get("setup", ""), t["golden"])
            print(f"  validate {tag} {t['id']}: {'ok' if s else 'DROP ' + why}")
            if s:
                keep.append(t)
        return keep

    print("== validating candidate reference commands ==")
    fable_valid = valid(fable_tasks, "fable")
    grok_valid = valid(grok_tasks, "grok")

    # 2+3) opposing strong model attempts; keep the FAILURES
    rounds = [("grok", fable_valid, "fable-authored, grok-solving"),
              ("fable-5", grok_valid, "grok-authored, fable-solving")]
    survivors, attempts = [], []
    for solver_id, tasks, banner in rounds:
        print(f"\n== {banner} ==")
        for t in tasks:
            cmd, s, why, el = solve_one(specs[solver_id], t)
            attempts.append({"task": t["id"], "proposer": t["proposer"],
                             "solver": solver_id, "solved": s, "elapsed_s": el, "why": why})
            verdict = "SOLVED" if s == 1 else ("ERROR -> skip" if s is None else "FAILED -> KEEP")
            print(f"  {t['id']} ({t['proposer']}) vs {solver_id}: {verdict}  {el}s")
            if s == 0:  # opposing strong model genuinely failed -> empirically hard
                survivors.append(t)  # s is None (infra error) is skipped, not kept

    out = {"system_prompt": json.loads((BENCH / "cand_fable.json").read_text())["system_prompt"],
           "tasks": survivors, "attempts": attempts,
           "note": "v4 = candidate tasks that the OPPOSING strong proposer failed one-shot "
                   "(empirically hard). Validated: reference reproduces golden."}
    (ROOT / "tasks/v4/spec.json").write_text(json.dumps(out, indent=2))
    (ROOT / "results/v4_adversarial_filter.json").write_text(json.dumps(attempts, indent=2))
    print(f"\n== survivors (v4): {len(survivors)} tasks: {[t['id']+'/'+t['proposer'] for t in survivors]} ==")


if __name__ == "__main__":
    main()
