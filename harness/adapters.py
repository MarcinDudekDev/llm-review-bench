"""Model adapters. Each returns (text, cost_usd_or_None).

Add a new provider by writing one function and registering it in ADAPTERS.
The harness treats every model as a black box: prompt in, text out.
"""
import json
import os
import subprocess
import urllib.request


def claude_cli(spec, prompt, timeout):
    """Anthropic models via the Claude Code CLI.

    Tools are hard-disabled (`--tools ""`) so the model CANNOT execute, test, or
    revise a command before answering — the "one shot, no execution" guarantee is
    structural, not behavioral. We also assert num_turns == 1 (a tool call would
    force a second turn), so any accidental tool use raises instead of scoring.

    Note: the [1m] suffix is not part of the model ID. The CLI strips it and
    translates it into the anthropic-beta context-1m-2025-08-07 header.
    An unrecognized suffix is silently dropped (no error, no 1M window).
    """
    p = subprocess.run(
        ["claude", "--model", spec["model"], "--tools", "", "-p", prompt,
         "--output-format", "json"],
        capture_output=True, text=True, timeout=timeout, cwd="/tmp", stdin=subprocess.DEVNULL,
    )
    d = json.loads(p.stdout)
    if d.get("is_error"):
        raise RuntimeError(f"{spec['id']}: API error {d.get('api_error_status')}")
    if d.get("num_turns", 1) != 1:  # a tool call would have forced >1 turn
        raise RuntimeError(f"{spec['id']}: num_turns={d.get('num_turns')} — not one-shot")
    return d.get("result", ""), d.get("total_cost_usd")


def grok_cli(spec, prompt, timeout):
    """xAI Grok via the Grok Build CLI. Cost is not reported by the CLI."""
    p = subprocess.run(
        ["grok", "--always-approve", "-p", prompt],
        capture_output=True, text=True, timeout=timeout, cwd="/tmp",
    )
    return p.stdout.strip(), None


def openrouter(spec, prompt, timeout):
    """Any model on OpenRouter. Set OPENROUTER_API_KEY."""
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY not set")
    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=json.dumps({
            "model": spec["model"],
            "messages": [{"role": "user", "content": prompt}],
        }).encode(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        d = json.loads(r.read())
    return d["choices"][0]["message"]["content"], d.get("usage", {}).get("cost")


ADAPTERS = {"claude_cli": claude_cli, "grok_cli": grok_cli, "openrouter": openrouter}
