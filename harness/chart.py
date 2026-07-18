#!/usr/bin/env python3
"""Render the model-comparison charts from results/ALL_RESULTS.json.

Two figures, the standard benchmark-comparison style:
  1. accuracy_by_task.png  — grouped bars, accuracy % per task, 4 models
  2. latency_by_task.png   — grouped bars, median latency (s) per task
"""
import json
import pathlib

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = json.loads((ROOT / "results/ALL_RESULTS.json").read_text())
OUT = ROOT / "blog/assets"

TASK_LABELS = {"v1": "v1\neasy review", "v2": "v2\nhard review",
               "v3": "v3\nshort commands", "v4": "v4\nhard commands"}
TASKS = ["v1", "v2", "v3", "v4"]
MODELS = DATA["models"]
LABELS = [DATA["labels"][m] for m in MODELS]
# colourblind-safe, distinct: two Opus warm, Sonnet blue, Haiku grey-green
COLORS = {"opus-4-6": "#E8833A", "opus-4-8": "#C0392B",
          "sonnet-5": "#2E86C1", "haiku-4-5": "#7F8C8D"}


def grouped(metric, title, ylabel, fname, fmt="{:.0f}", ymax=None):
    x = np.arange(len(TASKS))
    n = len(MODELS)
    w = 0.8 / n
    fig, ax = plt.subplots(figsize=(11, 6))
    for i, m in enumerate(MODELS):
        raw = [DATA["tasks"][t][m].get(metric) for t in TASKS]
        # a missing metric is a data GAP (np.nan → no bar), not a real zero
        vals = [v if v is not None else np.nan for v in raw]
        bars = ax.bar(x + i * w - 0.4 + w / 2, vals, w,
                      label=DATA["labels"][m], color=COLORS[m], edgecolor="white", linewidth=0.5)
        span = ymax or max([v for v in raw if v is not None] or [1])
        for b, v in zip(bars, raw):
            if v is not None:  # label real values, including a genuine 0
                ax.text(b.get_x() + b.get_width() / 2, v + span * 0.01,
                        fmt.format(v), ha="center", va="bottom", fontsize=8, color="#333")
    ax.set_xticks(x)
    ax.set_xticklabels([TASK_LABELS[t] for t in TASKS], fontsize=10)
    ax.set_ylabel(ylabel, fontsize=11)
    ax.set_title(title, fontsize=13, fontweight="bold", pad=14)
    if ymax:
        ax.set_ylim(0, ymax)
    ax.legend(frameon=False, ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.09))
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", alpha=0.25)
    ax.set_axisbelow(True)
    fig.tight_layout()
    fig.savefig(OUT / fname, dpi=150, bbox_inches="tight")
    print("wrote", OUT / fname)


if __name__ == "__main__":
    grouped("accuracy_pct",
            "One-shot code-review and command benchmark: accuracy by task",
            "Accuracy (%)", "accuracy_by_task.png", fmt="{:.0f}", ymax=105)
    grouped("latency_median_s",
            "Median latency by task (one-shot, tools disabled)",
            "Median latency (seconds)", "latency_by_task.png", fmt="{:.0f}")
    grouped("cost_median_usd",
            "Median cost per run by task (one-shot, tools disabled)",
            "Median cost (USD per run)", "cost_by_task.png", fmt="${:.3f}")
