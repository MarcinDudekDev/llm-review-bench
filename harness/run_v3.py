#!/usr/bin/env python3
"""Run the v3 command-generation benchmark: N trials x M models, execute-scored.

    python3 harness/run_v3.py --trials 10 --models opus-4-6,opus-4-8

Each model gets one call containing the system prompt + all 10 tasks and must
return 10 `Qn: <command>` lines. Every command is executed in a sandbox and its
stdout compared to the golden (see exec_score.py). Score is out of 10; latency
and cost are recorded but NOT part of the score, by design.
"""
import argparse
import json
import pathlib
import re
import time

from adapters import ADAPTERS
from exec_score import score_one

ROOT = pathlib.Path(__file__).resolve().parent.parent
LINE = re.compile(r"^\s*Q(\d+)\s*:\s*(.*?)\s*$")


def parse_commands(text: str) -> dict[int, str]:
    """Pull `Qn: <cmd>` lines from a model answer, stripping stray backtick fences."""
    out: dict[int, str] = {}
    for raw in text.splitlines():
        m = LINE.match(raw)
        if m:
            cmd = m.group(2).strip().strip("`").strip()
            out[int(m.group(1))] = cmd
    return out


def load_models(only: str) -> list[dict]:
    specs = json.loads((ROOT / "harness/models.json").read_text())["models"]
    specs = [s for s in specs if s.get("enabled", True) and not s["id"].startswith("_")]
    if only:
        want = {w.strip() for w in only.split(",") if w.strip()}
        specs = [s for s in specs if s["id"] in want]
    return specs


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--trials", type=int, default=10)
    ap.add_argument("--timeout", type=int, default=300)
    ap.add_argument("--models", default="opus-4-6,opus-4-8")
    args = ap.parse_args()

    spec = json.loads((ROOT / "tasks/v3/spec.json").read_text())
    tasks = spec["tasks"]
    prompt = spec["system_prompt"] + "\n\n" + "\n\n".join(
        f"{t['id']}. {t['prompt']}" for t in tasks
    )
    specs = load_models(args.models)
    if not specs:
        raise SystemExit(f"no models matched --models {args.models!r}; check spelling")
    print(f"v3: models={[s['id'] for s in specs]} trials={args.trials} tasks={len(tasks)}")

    rows = []
    for trial in range(1, args.trials + 1):
        for spec_m in specs:  # interleaved across models
            t0 = time.monotonic()
            try:
                text, cost = ADAPTERS[spec_m["adapter"]](spec_m, prompt, args.timeout)
                err = None
            except Exception as e:
                text, cost, err = "", None, f"{type(e).__name__}: {e}"
            elapsed = round(time.monotonic() - t0, 2)

            cmds = parse_commands(text)
            per_q = {}
            for t in tasks:
                n = int(t["id"][1:])
                s, why = score_one(cmds.get(n, ""), t.get("setup", ""), t["golden"])
                per_q[t["id"]] = {"score": s, "cmd": cmds.get(n, ""), "why": why}
            total = sum(v["score"] for v in per_q.values())

            rows.append({"trial": trial, "model_id": spec_m["id"], "label": spec_m["label"],
                         "elapsed_s": elapsed, "cost_usd": cost, "error": err,
                         "score": total, "per_q": per_q})
            print(f"  trial{trial:>2} {spec_m['id']:<10} score {total}/10  "
                  f"{elapsed:>7.2f}s  {('$%.4f' % cost) if cost is not None else 'n/a':>9}"
                  f"{'  ERR ' + err if err else ''}", flush=True)

    (ROOT / "results/v3_runs.json").write_text(json.dumps(rows, indent=2))
    print("\nwrote results/v3_runs.json")


if __name__ == "__main__":
    main()
