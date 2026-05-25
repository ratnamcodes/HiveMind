#!/usr/bin/env python3
"""Verify the hivemind-target GitLab repo exists and is push-able.

Two checks:
1. API: project exists + token has Developer-or-higher access
2. Git: can authenticate to git over HTTPS with the token (ls-remote, read-only)

Both must pass to prove the agent can push MRs to the repo.
No commits or pushes are made — ls-remote just exercises the auth path.
"""

from __future__ import annotations

import os
import subprocess
import sys
import urllib.parse
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

OK = "\033[92mOK  \033[0m"
FAIL = "\033[91mFAIL\033[0m"

ACCESS_LEVELS = {
    10: "Guest",
    20: "Reporter",
    30: "Developer",  # minimum for push
    40: "Maintainer",
    50: "Owner",
}


def main() -> int:
    base = (os.environ.get("GITLAB_URL") or "").rstrip("/")
    token = os.environ.get("GITLAB_TOKEN")
    project = os.environ.get("GITLAB_TARGET_PROJECT")

    if not (base and token and project):
        print(f"  {FAIL}  Missing GITLAB_URL, GITLAB_TOKEN, or GITLAB_TARGET_PROJECT")
        return 1

    print(f"\nVerifying GitLab project '{project}' is push-able...\n")

    # --- Check 1: project exists ------------------------------------------
    encoded = urllib.parse.quote(project, safe="")
    url = f"{base}/api/v4/projects/{encoded}"
    headers = {"PRIVATE-TOKEN": token}

    try:
        r = requests.get(url, headers=headers, timeout=10)
    except requests.RequestException as e:
        print(f"  {FAIL}  Project lookup failed: {e}")
        return 1

    if r.status_code != 200:
        print(f"  {FAIL}  Project exists check: HTTP {r.status_code} – {r.text[:150]}")
        return 1

    data = r.json()
    project_id = data["id"]
    default_branch = data.get("default_branch") or "main"
    print(f"  {OK}  Project exists (id={project_id}, default branch='{default_branch}')")

    # --- Check 2: token has push permission -------------------------------
    perms = data.get("permissions") or {}
    levels = [
        (perms.get("project_access") or {}).get("access_level") or 0,
        (perms.get("group_access") or {}).get("access_level") or 0,
    ]
    max_level = max(levels)
    level_name = ACCESS_LEVELS.get(max_level, f"unknown({max_level})")

    if max_level < 30:
        print(f"  {FAIL}  Token has '{level_name}' access — need Developer (30) or higher to push")
        return 1
    print(f"  {OK}  Token has '{level_name}' access (level {max_level}) — push permitted")

    # --- Check 3: git auth works (read-only ls-remote) --------------------
    host = base.replace("https://", "").replace("http://", "").rstrip("/")
    git_url = f"https://oauth2:{token}@{host}/{project}.git"

    try:
        result = subprocess.run(
            ["git", "ls-remote", "--heads", git_url],
            capture_output=True,
            text=True,
            timeout=20,
        )
    except subprocess.TimeoutExpired:
        print(f"  {FAIL}  git ls-remote timed out")
        return 1
    except FileNotFoundError:
        print(f"  {FAIL}  git command not found in PATH")
        return 1

    if result.returncode != 0:
        err = result.stderr.replace(token, "<TOKEN>")
        print(f"  {FAIL}  git ls-remote failed: {err[:200]}")
        return 1

    branches = [
        line for line in result.stdout.strip().split("\n") if line
    ]
    print(f"  {OK}  git auth works (ls-remote returned {len(branches)} branch(es))")

    print(f"\nAll checks passed. The agent can push MRs to {project}.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
