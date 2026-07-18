#!/usr/bin/env python3
"""Run v4 (18 validated hard command-gen tasks) across contenders, N trials.

    python3 harness/run_v4.py --trials 10 --models opus-4-6,opus-4-8

One model call returns all 18 commands (`<ID>: <cmd>`); each is executed and
compared to its golden. Score out of 18. Per-task pass rates expose exactly
which tasks (if any) separate the models.
"""
import argparse
import json
import pathlib
import re
import time

from adapters import ADAPTERS
from exec_score import score_one

ROOT = pathlib.Path(__file__).resolve().parent.parent
LINE = re.compile(r"^\s*([QG]\d+)\s*:\s*(.*?)\s*$")


def _unwrap(cmd: str) -> str:
    """Strip a balanced whole-command backtick wrap only; keep edge/interior
    command-substitution backticks (e.g. `echo `date`` must not lose its tick)."""
    cmd = cmd.strip()
    if len(cmd) > 1 and cmd.startswith("`") and cmd.endswith("`"):
        cmd = cmd[1:-1].strip()
    return cmd


def parse_commands(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for raw in (text or "").splitlines():
        m = LINE.match(raw)
        if m:
            out[m.group(1)] = _unwrap(m.group(2))
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--trials", type=int, default=10)
    ap.add_argument("--timeout", type=int, default=300)
    ap.add_argument("--models", default="opus-4-6,opus-4-8")
    args = ap.parse_args()

    spec = json.loads((ROOT / "tasks/v4/spec.json").read_text())
    tasks = spec["tasks"]
    ids = [t["id"] for t in tasks]
    prompt = (spec["system_prompt"].replace("EXACTLY 10 lines", f"EXACTLY {len(tasks)} lines")
              + "\n\n" + "\n\n".join(f"{t['id']}. {t['prompt']}" for t in tasks)
              + f"\n\nAnswer with exactly {len(tasks)} lines, one per task id "
                f"({', '.join(ids)}), each `<ID>: <command>`.")
    allm = {s["id"]: s for s in json.loads((ROOT / "harness/models.json").read_text())["models"]}
    names = [m.strip() for m in args.models.split(",") if m.strip()]
    missing = [n for n in names if n not in allm]
    if missing:
        raise SystemExit(f"unknown model id(s): {missing}; known: {sorted(allm)}")
    specs = [allm[n] for n in names]
    print(f"v4: {len(tasks)} tasks, models={args.models}, trials={args.trials}")

    rows = []
    for trial in range(1, args.trials + 1):
        for sm in specs:
            t0 = time.monotonic()
            try:
                text, cost = ADAPTERS[sm["adapter"]](sm, prompt, args.timeout)
                err = None
            except Exception as e:
                text, cost, err = "", None, f"{type(e).__name__}: {e}"
            elapsed = round(time.monotonic() - t0, 2)
            cmds = parse_commands(text)
            per = {}
            for t in tasks:
                s, why = score_one(cmds.get(t["id"], ""), t.get("setup", ""), t["golden"])
                per[t["id"]] = s
            total = sum(per.values())
            rows.append({"trial": trial, "model_id": sm["id"], "elapsed_s": elapsed,
                         "cost_usd": cost, "error": err, "score": total, "per_q": per})
            print(f"  trial{trial:>2} {sm['id']:<10} {total}/{len(tasks)}  {elapsed:>7.2f}s"
                  f"{'  ERR ' + err if err else ''}", flush=True)

    (ROOT / "results/v4_runs.json").write_text(json.dumps(rows, indent=2))
    print("\nwrote results/v4_runs.json")


if __name__ == "__main__":
    main()
