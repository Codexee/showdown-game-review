#!/usr/bin/env python3
"""UserPromptSubmit hook: make Claude suggest fitting skills on EVERY prompt.

Reads the hook JSON on stdin, matches the prompt against .claude/skill-triggers.json,
and adds context that tells Claude to open its reply with one line of skill suggestions.
Unlike the PatriotHacks version, it fires on every prompt (no once-per-session limit).
It never blocks the prompt, and any failure exits silently.
"""
import json
import os
import re
import sys


def main() -> None:
    try:
        event = json.load(sys.stdin)
    except Exception:
        return
    prompt = (event.get("prompt") or "").strip().lower()
    if not prompt:
        return

    root = os.environ.get("CLAUDE_PROJECT_DIR") or event.get("cwd") or os.getcwd()
    try:
        with open(os.path.join(root, ".claude", "skill-triggers.json")) as f:
            triggers = json.load(f)["triggers"]
    except Exception:
        triggers = []

    named = set(re.findall(r"(?:^|\s)/([a-z][a-z0-9:-]+)", prompt))
    hits = []
    for t in triggers:
        name = t.get("skill")
        if not name or name in named:
            continue
        for pat in t.get("patterns", []):
            try:
                if re.search(pat, prompt):
                    hits.append(t)
                    break
            except re.error:
                continue

    lines = "\n".join(f"- /{t['skill']}: {t.get('why', '')}" for t in hits[:4])
    context = (
        "Skill rule (this project, every prompt, no exceptions): open your reply with ONE short line "
        "that names the skills fitting this prompt and why, e.g. \"Skills: /prototype (test the eval bar), "
        "/codex (review the training code).\" Pick from the full skill list, not only the keyword matches. "
        "If none fit, write \"Skills: none fit.\" Then continue. Run a skill the user did not name only "
        "after they say yes; skills the user named run without asking."
    )
    if named:
        context += "\nSkills the user already named: " + ", ".join("/" + n for n in sorted(named)) + "."
    if lines:
        context += "\nKeyword matches:\n" + lines
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": context}}))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
