"""Data flywheel: the Reviewer rewrites its own critic rubric.

Daily: collect `human_corrected` traces (the war-room feedback buttons write a
Phoenix span annotation), turn them into preference pairs, and append them to a
dated Phoenix dataset (`hivemind-corrections-YYYY-MM-DD`).

Weekly: the Reviewer reads recent corrections, drafts an improved critic rubric,
and upserts it to Phoenix as a new `hivemind-critic-rubric` version. An experiment
compares new vs production on the corrections (which rubric catches more
human-flagged misses); a winning new rubric gets the `production` tag, which the
Reviewer pulls at runtime. Each run is logged to MongoDB `flywheel_runs`.

"Arize" here means the self-hosted Phoenix (phoenix-client / phoenix-mcp).
"""
from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv

load_dotenv("/Users/ratnam/hivemind/.env")

PROMPT_NAME = "hivemind-critic-rubric"
PRODUCTION_TAG = "production"
PHOENIX_HOST = os.getenv("PHOENIX_HOST", "http://localhost:6006").rstrip("/")
JUDGE_MODEL = "gemini-3.5-flash"
GEMINI_KEY = os.environ.get("GOOGLE_API_KEY", "")
PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT", "")
LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION", "global")

# A "correction" is a critic miss a human flagged: an agent output the Reviewer wrongly
# approved. Shape: {agent, rejected_output, human_reason, preferred_output}


def _gemini(prompt: str, json_mode: bool = False) -> str:
    """One-shot Gemini call via Vertex AI; fresh client per call; retries transient 429s."""
    from google import genai

    config = {"response_mime_type": "application/json"} if json_mode else None
    last_err: Exception | None = None
    for attempt in range(4):
        try:
            client = genai.Client(vertexai=True, project=PROJECT, location=LOCATION)
            resp = client.models.generate_content(
                model=JUDGE_MODEL, contents=prompt, config=config
            )
            return resp.text or ""
        except Exception as e:  # noqa: BLE001
            last_err = e
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                time.sleep(8 * (attempt + 1))
                continue
            raise
    raise last_err  # type: ignore[misc]


def _draft_new_rubric(current_rubric: str, corrections: list[dict]) -> str:
    """Reviewer drafts an improved critic rubric from the recent human corrections."""
    pairs = "\n".join(
        f"- agent={c['agent']}: approved BAD output «{c['rejected_output'][:200]}» — "
        f"human said: {c['human_reason']}"
        for c in corrections
    )
    prompt = (
        "You are HiveMind's Reviewer improving your OWN critic rubric. Below is your "
        "current rubric, then recent cases where you (the critic) WRONGLY approved an "
        "agent output that a human rejected. Rewrite the rubric so it would catch these "
        "misses, while staying general and concise. Return ONLY the new rubric text.\n\n"
        f"CURRENT RUBRIC:\n{current_rubric}\n\n"
        f"RECENT CRITIC MISSES:\n{pairs}\n"
    )
    return _gemini(prompt).strip()


def _count_caught(rubric: str, corrections: list[dict]) -> int:
    """How many of these known-bad outputs would this rubric reject? Batched into a
    single call so the experiment is 2 calls total (old vs new), not 2*N."""
    items = "\n".join(
        f"{i}. [{c['agent']}] {c['rejected_output']}" for i, c in enumerate(corrections)
    )
    prompt = (
        f"Apply this critic rubric:\n{rubric}\n\n"
        f"For EACH agent output below decide approve or reject (a grounded critic should "
        f"REJECT the bad ones):\n{items}\n\n"
        'Return ONLY JSON: {"verdicts": ["approve"|"reject", ...]} in the same order.'
    )
    try:
        data = json.loads(_gemini(prompt, json_mode=True))
        return sum(1 for v in data.get("verdicts", []) if v == "reject")
    except Exception:  # noqa: BLE001
        return 0


def _phoenix():
    from phoenix.client import Client

    return Client(base_url=PHOENIX_HOST)


def current_production_rubric() -> tuple[str | None, str]:
    """Return (version_id, system_text) of the production-tagged critic rubric."""
    pv = _phoenix().prompts.get(prompt_identifier=PROMPT_NAME, tag=PRODUCTION_TAG)
    messages = pv._template["messages"]  # noqa: SLF001 (avoids the legacy .format() path)
    text = "\n\n".join(
        m["content"] for m in messages if m.get("role") == "system" and m.get("content")
    )
    return getattr(pv, "id", None), text


def upsert_rubric(text: str) -> str:
    """Create a new version of the critic rubric prompt in Phoenix. Returns its id."""
    from phoenix.client.types import PromptVersion

    version = _phoenix().prompts.create(
        name=PROMPT_NAME,
        prompt_description="HiveMind Reviewer critic rubric (flywheel-rewritten).",
        version=PromptVersion(
            [{"role": "system", "content": text}],
            model_name=JUDGE_MODEL,
            model_provider="GOOGLE",
            template_format="NONE",
        ),
    )
    return version.id


def promote(version_id: str) -> bool:
    """Move the `production` tag to `version_id` so every Reviewer reads it next pull."""
    try:
        _phoenix().prompts.tags.create(prompt_version_id=version_id, name=PRODUCTION_TAG)
        return True
    except Exception:  # noqa: BLE001
        return False


def append_to_dataset(corrections: list[dict]) -> str | None:
    """Append the preference pairs to a dated Phoenix dataset. Best-effort."""
    name = f"hivemind-corrections-{datetime.now(timezone.utc):%Y-%m-%d}"
    try:
        client = _phoenix()
        client.datasets.create_dataset(
            name=name,
            inputs=[{"agent": c["agent"], "output": c["rejected_output"]} for c in corrections],
            outputs=[{"preferred": c.get("preferred_output", ""), "reason": c["human_reason"]} for c in corrections],
        )
        return name
    except Exception:  # noqa: BLE001
        return None  # dataset API varies by Phoenix version; non-fatal for the loop


def collect_corrections(hours: int = 24) -> list[dict]:
    """Not implemented; callers pass corrections explicitly."""
    return []


async def log_run(event: dict) -> bool:
    try:
        from hivemind.mongo_client import close_mongo, get_db

        await get_db().flywheel_runs.insert_one(event)
        await close_mongo()
        return True
    except Exception:  # noqa: BLE001
        return False


async def run_loop(corrections: list[dict] | None = None) -> dict:
    """Run one full flywheel cycle. Returns a structured result (also logged to Mongo)."""
    ts = datetime.now(timezone.utc).isoformat()
    corrections = corrections if corrections is not None else collect_corrections()

    result: dict = {
        "ts": ts,
        "n_corrections": len(corrections),
        "dataset": None,
        "old_rubric_version": None,
        "new_rubric_version": None,
        "scores": {},
        "winner": None,
        "promoted": False,
        "notes": [],
    }

    if not corrections:
        result["notes"].append("no corrections in window; nothing to learn from")
        await log_run(result)
        return result

    result["dataset"] = append_to_dataset(corrections)

    old_id, old_rubric = current_production_rubric()
    result["old_rubric_version"] = old_id

    new_rubric = _draft_new_rubric(old_rubric, corrections)
    new_id = upsert_rubric(new_rubric)
    result["new_rubric_version"] = new_id

    # Which rubric catches more of the human-flagged critic misses?
    old_caught = _count_caught(old_rubric, corrections)
    new_caught = _count_caught(new_rubric, corrections)
    n = len(corrections)
    result["scores"] = {
        "old": {"caught": old_caught, "of": n, "rate": round(old_caught / n, 3)},
        "new": {"caught": new_caught, "of": n, "rate": round(new_caught / n, 3)},
    }

    if new_caught > old_caught:
        result["winner"] = "new"
        result["promoted"] = promote(new_id)
        result["notes"].append(
            f"new rubric caught {new_caught}/{n} vs old {old_caught}/{n} — promoted to production"
        )
    else:
        result["winner"] = "old"
        result["notes"].append(
            f"new rubric did NOT beat old ({new_caught} vs {old_caught}/{n}) — kept production as-is"
        )

    result["logged"] = await log_run(result)
    return result
