"""The HiveMind agent roster — look up any specialist by id."""

from __future__ import annotations

from google.adk.agents import LlmAgent as Agent

from agents.code_arch import code_arch
from agents.customer_liaison import customer_liaison
from agents.detective import detective
from agents.log_diver import log_diver
from agents.reviewer import reviewer
from agents.scribe import scribe

_REGISTRY: dict[str, Agent] = {
    "detective": detective,
    "log_diver": log_diver,
    "code_arch": code_arch,
    "customer_liaison": customer_liaison,
    "scribe": scribe,
    "reviewer": reviewer,
}


def get(name: str) -> Agent:
    """Return the agent registered under `name` (raises KeyError if unknown)."""
    return _REGISTRY[name]


def list_all() -> list[str]:
    """Return every registered agent id."""
    return list(_REGISTRY)