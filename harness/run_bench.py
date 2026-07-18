#!/usr/bin/env python3
"""Run a benchmark task across N models x M trials, recording output, latency and cost.

    python3 harness/run_bench.py --task v2 --trials 3
    python3 harness/run_bench.py --task v2 --models opus-4-6,opus-4-8 --trials 5

Trials are interleaved across models (round-robin), not batched per model, so
that drifting API conditions hit every model roughly equally.
"""
import argparse
import json
import pathlib
import subprocess
import time

from adapters import ADAPTERS

ROOT = pathlib.Path(__file__).resolve().parent.parent


def load_models(only):
    specs = json.loads((ROOT / "harness/models.json").read_text())["models"]
    specs = [s for s in specs if s.get("enabled", True) and not s["id"].startswith("_")]
    if only:
        want = {w.strip() for w in only.split(",") if w.strip()}
        specs = [s for s in specs if s["id"] in want]
    return specs


def run_one(spec, prompt, timeout):
    fn = ADAPTERS[spec["adapter"]]
    t0 = time.monotonic()
    try:
        text, cost = fn(spec, prompt, timeout)
        return {"elapsed_s": round(time.monotonic() - t0, 2), "timed_out": False,
                "cost_usd": cost, "output": text, "error": None}
    except Exception as e:  # timeout, API error, adapter failure
        return {"elapsed_s": round(time.monotonic() - t0, 2),
                "timed_out": isinstance(e, (subprocess.TimeoutExpired, TimeoutError)),
                "cost_usd": None, "output": "", "error": f"{type(e).__name__}: {e}"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", default="v2")
    ap.add_argument("--trials", type=int, default=3)
    ap.add_argument("--timeout", type=int, default=300,
                    help="Per-run cap in seconds. Keep generous: a tight cap "
                         "measures API weather, not the model (see README).")
    ap.add_argument("--models", default="")
    args = ap.parse_args()

    prompt = (ROOT / f"tasks/{args.task}/task.md").read_text()
    specs = load_models(args.models)
    if not specs:
        raise SystemExit(f"no models matched --models {args.models!r}; check spelling")
    print(f"task={args.task} models={[s['id'] for s in specs]} trials={args.trials}")

    rows = []
    for trial in range(1, args.trials + 1):
        for spec in specs:  # interleaved, not batched
            r = run_one(spec, prompt, args.timeout)
            r |= {"trial": trial, "model_id": spec["id"], "label": spec["label"]}
            rows.append(r)
            cost = f"${r['cost_usd']:.4f}" if r["cost_usd"] is not None else "n/a"
            print(f"  trial{trial} {spec['id']:<10} {r['elapsed_s']:>7.2f}s {cost:>9}"
                  f"{'  ERROR: ' + r['error'] if r['error'] else ''}", flush=True)

    out = ROOT / f"results/{args.task}_runs.json"
    out.write_text(json.dumps(rows, indent=2))
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
