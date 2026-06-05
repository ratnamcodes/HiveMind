#!/usr/bin/env python3
"""Seed the Reviewer's critic rubric into Phoenix prompt management (T13).

Creates the `hivemind-critic-rubric` prompt (v1 = the Reviewer's T08 system
prompt) and tags it `production`. The Reviewer pulls the `production`-tagged
version at runtime (T13 step 5); T18's meta-loop will upsert improved versions
and move the `production` tag to ship a better rubric WITHOUT a redeploy.

Idempotent: if a `production`-tagged version already exists, it does nothing
(re-running won't pile up duplicate versions).

Prereq: Phoenix running (docker run ... arizephoenix/phoenix) and PHOENIX_HOST
in .env (defaults to http://localhost:6006).

Run:  python scripts/seed_critic_prompt.py
"""
from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv("/Users/ratnam/hivemind/.env")

from phoenix.client import Client  # noqa: E402  (after load_dotenv)
from phoenix.client.types import PromptVersion  # noqa: E402

PROMPT_NAME = "hivemind-critic-rubric"
PRODUCTION_TAG = "production"

# v1 == the Reviewer's T08 system prompt, snapshotted verbatim. After this seed
# Phoenix is the source of truth; reviewer.py pulls the production tag at runtime.
CRITIC_RUBRIC_V1 = (
    "You are Reviewer, the critic of HiveMind. You score every agent output "
    "against the rubric and reject anything ungrounded, contradicted by "
    "evidence, or below the quality bar. Your verdict is one of {approve, "
    "revise, escalate}. You always cite the specific rubric line and the "
    "offending fragment."
)


def main() -> int:
    base_url = os.getenv("PHOENIX_HOST", "http://localhost:6006")
    client = Client(base_url=base_url)
    print(f"Phoenix: {base_url}")

    # Idempotency: bail if a production-tagged version already exists.
    try:
        existing = client.prompts.get(
            prompt_identifier=PROMPT_NAME, tag=PRODUCTION_TAG
        )
        print(
            f"already seeded — '{PROMPT_NAME}' @{PRODUCTION_TAG} exists "
            f"(id={existing.id}); leaving as-is."
        )
        return 0
    except Exception:
        pass  # not found -> create it below

    version = client.prompts.create(
        name=PROMPT_NAME,
        prompt_description="HiveMind Reviewer critic rubric (scores agent outputs).",
        version=PromptVersion(
            [{"role": "system", "content": CRITIC_RUBRIC_V1}],
            model_name="gemini-3.5-flash",
            model_provider="GOOGLE",
            # NONE: static system prompt with literal braces
            # ({approve, revise, escalate}) and no template variables — don't
            # let MUSTACHE/F_STRING try to interpolate them.
            template_format="NONE",
        ),
    )
    print(f"created '{PROMPT_NAME}' v1 (version id={version.id})")

    client.prompts.tags.create(prompt_version_id=version.id, name=PRODUCTION_TAG)
    print(f"tagged version {version.id} as '{PRODUCTION_TAG}'")

    # Verify the runtime pull path the Reviewer will use in step 5.
    pulled = client.prompts.get(prompt_identifier=PROMPT_NAME, tag=PRODUCTION_TAG)
    print(f"verify: pulled '{PROMPT_NAME}' @{PRODUCTION_TAG} -> id={pulled.id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
