#!/usr/bin/env python3
"""Consolidate every model x task result into one dataset + summary.

Reads the per-pairing result files (Opus and Sonnet/Haiku) plus the judged
review scores, and writes results/ALL_RESULTS.json — the single source for the
blog post and the comparison chart.

v3/v4 are exec-scored (accuracy read straight from the run files). v1/v2 are
review tasks whose accuracy is blind-judged; those scores are passed in via the
JUDGED dict below (filled from judge.py output, both judges agreeing).
"""
import json
import pathlib
import statistics as st

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"

# Blind-judged review accuracy (0-10), both Fable+Grok agreed. Opus from the
# enforced-one-shot re-run; Sonnet/Haiku filled after judging completes.
JUDGED = {
    "v1": {"opus-4-6": 8.0, "opus-4-8": 7.0, "sonnet-5": 8.0, "haiku-4-5": 5.5},
    "v2": {"opus-4-6": 8.2, "opus-4-8": 9.4, "sonnet-5": 8.8, "haiku-4-5": 6.5},
}

MODELS = ["opus-4-6", "opus-4-8", "sonnet-5", "haiku-4-5"]
LABEL = {"opus-4-6": "Opus 4.6", "opus-4-8": "Opus 4.8",
         "sonnet-5": "Sonnet 5", "haiku-4-5": "Haiku 4.5"}
# max score per task for normalisation to a 0-100 accuracy %
MAXP = {"v1": 10, "v2": 10, "v3": 10, "v4": 18}


def load(path):
    p = R / path
    return json.loads(p.read_text()) if p.exists() else None


def exec_scores(task, model):
    """Return list of per-trial scores for an exec-scored task/model, or None."""
    for cand in (f"{task}_runs_sonnet_haiku.json", f"{task}_runs_opus.json", f"{task}_runs.json"):
        rows = load(cand)
        if not rows:
            continue
        rs = [r for r in rows if r["model_id"] == model and "score" in r]
        if rs:
            return rs
    return None


def latency_cost(task, model):
    for cand in (f"{task}_runs_sonnet_haiku.json", f"{task}_runs_opus.json", f"{task}_runs.json"):
        rows = load(cand)
        if not rows:
            continue
        rs = [r for r in rows if r["model_id"] == model]
        if rs:
            lat = [r["elapsed_s"] for r in rs if r.get("elapsed_s")]
            cost = [r["cost_usd"] for r in rs if r.get("cost_usd")]
            return (round(st.median(lat), 1) if lat else None,
                    round(st.median(cost), 4) if cost else None)
    return (None, None)


def main():
    out = {"models": MODELS, "labels": LABEL, "tasks": {}}
    for task in ("v1", "v2", "v3", "v4"):
        out["tasks"][task] = {}
        for m in MODELS:
            entry = {}
            if task in ("v3", "v4"):
                rs = exec_scores(task, m)
                if rs:
                    scores = [r["score"] for r in rs]
                    entry["accuracy_pct"] = round(100 * sum(scores) / (len(scores) * MAXP[task]), 1)
                    entry["raw"] = f"{sum(scores)}/{len(scores) * MAXP[task]}"
            else:
                j = JUDGED[task].get(m)
                if j is not None:
                    entry["accuracy_pct"] = round(100 * j / MAXP[task], 1)
                    entry["raw"] = f"{j}/10 (judged)"
            lat, cost = latency_cost(task, m)
            entry["latency_median_s"] = lat
            entry["cost_median_usd"] = cost
            out["tasks"][task][m] = entry
    (R / "ALL_RESULTS.json").write_text(json.dumps(out, indent=2))
    # console table
    print(f"{'task':<5}{'model':<11}{'acc%':>7}{'raw':>14}{'lat_s':>8}{'cost$':>9}")
    for task in ("v1", "v2", "v3", "v4"):
        for m in MODELS:
            e = out["tasks"][task][m]
            print(f"{task:<5}{LABEL[m]:<11}{str(e.get('accuracy_pct','-')):>7}"
                  f"{str(e.get('raw','-')):>14}{str(e.get('latency_median_s','-')):>8}"
                  f"{str(e.get('cost_median_usd','-')):>9}")
    print("\nwrote results/ALL_RESULTS.json")


if __name__ == "__main__":
    main()
