#!/usr/bin/env python3
"""Verify the hivemind-bot GitLab identity (step 2) and its repo access (step 3).

Step 2 — identity: GITLAB_BOT_TOKEN is a valid PAT that authenticates AS the bot,
         so every MR/comment CodeArch makes is attributed to the bot, not to you.
Step 3 — access:   the bot has Developer-or-higher on GITLAB_TARGET_PROJECT.
         Expected to FAIL until you add the bot as a Developer on the repo.

Read-only: GET /user, GET /projects/:id. No writes, no pushes.
"""

from __future__ import annotations

import os
import sys
import urllib.parse
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

OK = "\033[92mOK  \033[0m"
FAIL = "\033[91mFAIL\033[0m"
INFO = "\033[93m--  \033[0m"

ACCESS_LEVELS = {
    10: "Guest",
    20: "Reporter",
    30: "Developer",  # minimum to push
    40: "Maintainer",
    50: "Owner",
}


def main() -> int:
    base = (os.environ.get("GITLAB_URL") or "").rstrip("/")
    token = os.environ.get("GITLAB_BOT_TOKEN")
    expected_username = os.environ.get("GITLAB_BOT_USERNAME")
    project = os.environ.get("GITLAB_TARGET_PROJECT")

    if not (base and token and project):
        print(f"  {FAIL}  Missing GITLAB_URL, GITLAB_BOT_TOKEN, or GITLAB_TARGET_PROJECT")
        return 1

    headers = {"PRIVATE-TOKEN": token}

    # --- Step 2: token valid + identifies the bot -------------------------
    print("\nStep 2 — bot identity\n")
    try:
        r = requests.get(f"{base}/api/v4/user", headers=headers, timeout=10)
    except requests.RequestException as e:
        print(f"  {FAIL}  /user request failed: {e}")
        return 1

    if r.status_code == 401:
        print(f"  {FAIL}  Token rejected (401) — GITLAB_BOT_TOKEN is wrong, expired, or mistyped.")
        return 1
    if r.status_code != 200:
        print(f"  {FAIL}  /user returned HTTP {r.status_code} - {r.text[:150]}")
        return 1

    me = r.json()
    username = me.get("username")
    name = me.get("name")
    uid = me.get("id")
    print(f'  {OK}  Token valid - authenticates as @{username} ("{name}", id={uid})')
    print(f"  {INFO}  Every MR + comment CodeArch makes will be authored by @{username}.")

    if not expected_username:
        print(f"  {INFO}  GITLAB_BOT_USERNAME is not set yet - add this line to .env:")
        print(f"           GITLAB_BOT_USERNAME={username}")
    elif expected_username != username:
        print(f"  {INFO}  Mismatch: GITLAB_BOT_USERNAME=@{expected_username} but token is @{username}. Fix .env.")

    # --- Step 3: bot has push access to the target repo -------------------
    print("\nStep 3 - bot access to target repo\n")
    encoded = urllib.parse.quote(project, safe="")
    try:
        pr = requests.get(f"{base}/api/v4/projects/{encoded}", headers=headers, timeout=10)
    except requests.RequestException as e:
        print(f"  {FAIL}  Project lookup failed: {e}")
        return 1

    if pr.status_code == 404:
        print(f"  {FAIL}  Bot can't see '{project}' (404) - @{username} is not a member yet.")
        print(f"           -> Step 3: invite @{username} to the repo as Developer.")
        return 2
    if pr.status_code != 200:
        print(f"  {FAIL}  Project lookup: HTTP {pr.status_code} - {pr.text[:150]}")
        return 1

    data = pr.json()
    perms = data.get("permissions") or {}
    levels = [
        (perms.get("project_access") or {}).get("access_level") or 0,
        (perms.get("group_access") or {}).get("access_level") or 0,
    ]
    max_level = max(levels)
    level_name = ACCESS_LEVELS.get(max_level, f"none({max_level})")

    if max_level < 30:
        print(f"  {FAIL}  Bot has '{level_name}' access (level {max_level}) - need Developer (30)+ to push.")
        print(f"           -> Step 3: add @{username} as Developer on '{project}'.")
        return 2
    print(f"  {OK}  Bot has '{level_name}' access (level {max_level}) - push permitted.")
    print(f"\nAll good - @{username} can author MRs on {project}.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
