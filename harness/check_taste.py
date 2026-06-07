#!/usr/bin/env python3
"""Mechanically-enforced taste (T19-D) — the structural checks the CI gate runs.

Taste is enforced by the gate, not by asking the model nicely. Fails (exit 1) if:
  1. AGENTS.md is missing a required section,
  2. harness/contract.schema.json is not a valid JSON Schema,
  3. any agent declares a tool OUTSIDE an MCPToolset (static AST check — the
     "no tool call outside an MCPToolset" anti-pattern from AGENTS.md).

Run:  python harness/check_taste.py
"""
from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REQUIRED_SECTIONS = ["## Architecture", "## Anti-patterns", "## Contract"]
# Agents with no tools at all (pure synthesis) — nothing to check.
NO_TOOL_AGENTS = {"__init__.py", "registry.py", "scribe.py", "hello.py"}

# Documented, justified exceptions to "no tool outside an MCPToolset" (mirrored in AGENTS.md).
# An undocumented non-MCP tool still fails the gate; only these named, reasoned ones pass.
ALLOWED_NON_MCP_TOOLS = {
    "query_customer_data": "read-only BigQuery read path — the Fivetran MCP can't query BQ",
}


def check_agents_md(errors: list[str]) -> None:
    p = ROOT / "AGENTS.md"
    if not p.exists():
        errors.append("AGENTS.md missing at repo root")
        return
    text = p.read_text()
    for s in REQUIRED_SECTIONS:
        if s not in text:
            errors.append(f"AGENTS.md missing required section: {s}")


def check_contract_schema(errors: list[str]) -> None:
    p = ROOT / "harness" / "contract.schema.json"
    if not p.exists():
        errors.append("harness/contract.schema.json missing")
        return
    try:
        schema = json.loads(p.read_text())
    except Exception as e:  # noqa: BLE001
        errors.append(f"contract.schema.json is not valid JSON: {e}")
        return
    try:
        from jsonschema import Draft202012Validator

        Draft202012Validator.check_schema(schema)
    except ImportError:
        errors.append("jsonschema not installed (needed to validate contract.schema.json)")
    except Exception as e:  # noqa: BLE001
        errors.append(f"contract.schema.json is not a valid JSON Schema: {e}")


def _is_mcptoolset(node: ast.expr, mcp_vars: set[str]) -> bool:
    if isinstance(node, ast.Name):
        return node.id in mcp_vars
    if isinstance(node, ast.Call):  # inline McpToolset(...)
        return getattr(node.func, "id", "") == "McpToolset"
    return False


def check_agent_tools(errors: list[str]) -> None:
    for f in sorted((ROOT / "agents").glob("*.py")):
        if f.name in NO_TOOL_AGENTS:
            continue
        tree = ast.parse(f.read_text())
        mcp_vars = {
            t.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Assign)
            and isinstance(node.value, ast.Call)
            and getattr(node.value.func, "id", "") == "McpToolset"
            for t in node.targets
            if isinstance(t, ast.Name)
        }
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and getattr(node.func, "id", "") in ("Agent", "LlmAgent"):
                for kw in node.keywords:
                    if kw.arg == "tools" and isinstance(kw.value, ast.List):
                        for elt in kw.value.elts:
                            if _is_mcptoolset(elt, mcp_vars):
                                continue
                            if getattr(elt, "id", None) in ALLOWED_NON_MCP_TOOLS:
                                continue  # documented, justified exception
                            errors.append(
                                f"{f.name}: agent declares a tool outside an MCPToolset "
                                f"({ast.dump(elt)[:50]})"
                            )


def main() -> int:
    errors: list[str] = []
    check_agents_md(errors)
    check_contract_schema(errors)
    check_agent_tools(errors)
    if errors:
        print("❌ TASTE CHECK FAILED:")
        for e in errors:
            print("  -", e)
        return 1
    print("✅ taste check passed — AGENTS.md sections present, contract schema valid, "
          "every agent tool is an MCPToolset")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
