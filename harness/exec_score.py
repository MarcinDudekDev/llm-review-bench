#!/usr/bin/env python3
"""Execute-and-compare scorer for v3 command-generation tasks.

For each task: make a throwaway temp dir, run the task's setup, run the
candidate command in that dir, capture stdout, trim ONE trailing newline,
compare to golden. Returns 1 (match) or 0 (mismatch/error/blocked).

Safety: candidate commands are model-generated. Each runs in an isolated
temp dir with a hard timeout and a denylist of obviously destructive tokens.
This is a guardrail, not a jail — the tasks are pure text transforms, so a
correct command never needs anything the denylist blocks.
"""
import pathlib
import re
import shutil
import subprocess
import tempfile

DENY = re.compile(
    r"""(\brm\s+-|\bmkfs\b|\bdd\b|\b:\s*\(\s*\)\s*\{|>/dev/sd|\bshutdown\b|\breboot\b
        |\bcurl\b|\bwget\b|\bnc\b|\bssh\b|\bscp\b|/dev/tcp|\bchmod\s+-R|\bchown\s+-R
        |\bsudo\b|\bkillall\b|\bpkill\b|\bcrontab\b|~/|\$HOME|\.\./\.\.)""",
    re.X,
)


def score_one(command, setup, golden, timeout=20):
    if not command or DENY.search(command):
        return 0, "blocked_or_empty"
    d = tempfile.mkdtemp(prefix="v3sbx_")
    try:
        if setup:
            s = subprocess.run(["bash", "-c", setup], cwd=d,
                               capture_output=True, text=True, timeout=timeout)
            if s.returncode != 0:
                return 0, f"setup_failed: {s.stderr[:120]}"
        p = subprocess.run(["bash", "-c", command], cwd=d,
                           capture_output=True, text=True, timeout=timeout)
        got = p.stdout
        if got.endswith("\n"):
            got = got[:-1]
        exp = golden[:-1] if golden.endswith("\n") else golden
        return (1, "ok") if got == exp else (0, f"got={got!r}")
    except subprocess.TimeoutExpired:
        return 0, "timeout"
    except Exception as e:
        return 0, f"error: {type(e).__name__}: {e}"
    finally:
        shutil.rmtree(d, ignore_errors=True)


if __name__ == "__main__":  # self-validate: reference_command must yield golden
    import json
    spec = json.loads((pathlib.Path(__file__).resolve().parent.parent
                       / "tasks/v3/spec.json").read_text())
    ok = 0
    for t in spec["tasks"]:
        s, why = score_one(t["reference_command"], t.get("setup", ""), t["golden"])
        ok += s
        print(f"  {t['id']}: {'PASS' if s else 'FAIL'}  {'' if s else why}")
    print(f"\nreference validation: {ok}/{len(spec['tasks'])} tasks self-consistent")
