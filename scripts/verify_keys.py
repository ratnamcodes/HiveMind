#!/usr/bin/env python3
"""Verify HiveMind partner credentials resolve. One cheap read per service.

Run from repo root:
    python scripts/verify_keys.py

Exit code is 0 if every line says OK, 1 otherwise.
"""

from __future__ import annotations

import base64
import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth, HTTPDigestAuth

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

OK = "\033[92mOK  \033[0m"
FAIL = "\033[91mFAIL\033[0m"

_results: list[tuple[str, bool]] = []


def _report(name: str, ok: bool, detail: str = "") -> None:
    marker = OK if ok else FAIL
    print(f"  {marker}  {name:<10} {detail}")
    _results.append((name, ok))


def _env(*keys: str) -> tuple[str, ...] | None:
    """Return env values for all keys, or None (and report) if any are missing."""
    missing = [k for k in keys if not os.environ.get(k)]
    if missing:
        return None
    return tuple(os.environ[k] for k in keys)


# --- Gemini ----------------------------------------------------------------
def check_gemini() -> None:
    vals = _env("GOOGLE_API_KEY")
    if not vals:
        _report("Gemini", False, "missing GOOGLE_API_KEY")
        return
    (key,) = vals
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={key}"
    r = requests.get(url, timeout=10)
    if r.status_code == 200:
        n = len(r.json().get("models", []))
        _report("Gemini", True, f"({n} models visible)")
    else:
        _report("Gemini", False, f"HTTP {r.status_code} – {r.text[:120]}")


# --- MongoDB Atlas ---------------------------------------------------------
def check_mongodb() -> None:
    vals = _env("MDB_API_PUBLIC_KEY", "MDB_API_PRIVATE_KEY", "MDB_ORG_ID")
    if not vals:
        _report("MongoDB", False, "missing MDB_* env vars")
        return
    pub, priv, expected_org = vals
    # List all orgs accessible to this key — verifies auth + tells us which orgs exist.
    url = "https://cloud.mongodb.com/api/atlas/v2/orgs"
    headers = {"Accept": "application/vnd.atlas.2025-03-12+json"}
    r = requests.get(url, auth=HTTPDigestAuth(pub, priv), headers=headers, timeout=10)
    if r.status_code != 200:
        _report("MongoDB", False, f"HTTP {r.status_code} – {r.text[:120]}")
        return
    orgs = r.json().get("results", [])
    org_ids = [o.get("id") for o in orgs]
    if expected_org not in org_ids:
        _report(
            "MongoDB", False,
            f"MDB_ORG_ID not in accessible orgs (got {org_ids})",
        )
        return
    _report("MongoDB", True, f"({len(orgs)} org(s), MDB_ORG_ID matches)")


# --- Arize -----------------------------------------------------------------
def check_arize() -> None:
    vals = _env("ARIZE_SPACE_ID", "ARIZE_API_KEY")
    if not vals:
        _report("Arize", False, "missing ARIZE_* env vars")
        return
    space, api_key = vals
    # Arize uses different auth depending on endpoint. The OTel ingest endpoint
    # accepts the Service Key via the api_key + space_id headers. We probe it
    # with an unauthenticated method to see if auth is recognized at all.
    # 200/202 = accepted, 401 = key invalid, 405 = wrong method but auth ok.
    url = "https://otlp.arize.com/v1/traces"
    headers = {
        "api_key": api_key,
        "space_id": space,
        "Content-Type": "application/x-protobuf",
    }
    # Send minimal empty body — server will reject the payload but if auth
    # passes we'll get a 400/415, not a 401.
    r = requests.post(url, data=b"", headers=headers, timeout=10)
    if r.status_code == 401:
        _report("Arize", False, f"HTTP 401 – key not recognized – {r.text[:120]}")
    elif r.status_code in (200, 202, 400, 415, 422):
        # Any of these = the key was accepted; only the payload was rejected.
        _report("Arize", True, f"(ingest endpoint accepts key, HTTP {r.status_code})")
    else:
        _report("Arize", False, f"HTTP {r.status_code} – {r.text[:120]}")


# --- Elastic ---------------------------------------------------------------
def check_elastic() -> None:
    vals = _env("ELASTIC_CLOUD_ID", "ELASTIC_API_KEY")
    if not vals:
        _report("Elastic", False, "missing ELASTIC_* env vars")
        return
    cloud_id, api_key = vals
    # Cloud ID format: <name>:<base64(domain:port$es_uuid$kb_uuid)>
    try:
        _, encoded = cloud_id.split(":", 1)
        decoded = base64.b64decode(encoded).decode()
        domain_port, es_uuid, _kb_uuid = decoded.split("$")
        es_url = f"https://{es_uuid}.{domain_port}"
    except Exception as e:
        _report("Elastic", False, f"could not parse Cloud ID: {e}")
        return
    headers = {"Authorization": f"ApiKey {api_key}"}
    # /_security/_authenticate works for any valid key without needing
    # cluster:monitor — it just identifies who the caller is.
    r = requests.get(es_url + "/_security/_authenticate", headers=headers, timeout=10)
    if r.status_code == 200:
        body = r.json()
        user = body.get("username", "?")
        _report("Elastic", True, f"(authenticated as '{user}')")
    else:
        _report("Elastic", False, f"HTTP {r.status_code} – {r.text[:120]}")


# --- Dynatrace -------------------------------------------------------------
def check_dynatrace() -> None:
    vals = _env("DT_ENVIRONMENT", "DT_API_TOKEN")
    if not vals:
        _report("Dynatrace", False, "missing DT_* env vars")
        return
    env_url, token = vals
    env_url = env_url.rstrip("/")
    # /api/v1/cluster/version only exists on Managed Dynatrace, not SaaS.
    # Use /api/v2/problems which works on SaaS and matches the problems.read
    # scope we know the token has.
    url = f"{env_url}/api/v2/problems?pageSize=1"
    headers = {"Authorization": f"Api-Token {token}"}
    r = requests.get(url, headers=headers, timeout=10)
    if r.status_code == 200:
        total = r.json().get("totalCount", 0)
        _report("Dynatrace", True, f"(problems API works, {total} open)")
    else:
        _report("Dynatrace", False, f"HTTP {r.status_code} – {r.text[:120]}")


# --- GitLab ----------------------------------------------------------------
def check_gitlab() -> None:
    vals = _env("GITLAB_URL", "GITLAB_TOKEN")
    if not vals:
        _report("GitLab", False, "missing GITLAB_* env vars")
        return
    base, token = vals
    url = base.rstrip("/") + "/api/v4/user"
    headers = {"PRIVATE-TOKEN": token}
    r = requests.get(url, headers=headers, timeout=10)
    if r.status_code == 200:
        u = r.json().get("username", "?")
        _report("GitLab", True, f"(@{u})")
    else:
        _report("GitLab", False, f"HTTP {r.status_code} – {r.text[:120]}")


# --- Fivetran --------------------------------------------------------------
def check_fivetran() -> None:
    vals = _env("FIVETRAN_API_KEY", "FIVETRAN_API_SECRET")
    if not vals:
        _report("Fivetran", False, "missing FIVETRAN_* env vars")
        return
    key, secret = vals
    url = "https://api.fivetran.com/v1/groups"
    r = requests.get(url, auth=HTTPBasicAuth(key, secret), timeout=10)
    if r.status_code == 200:
        items = r.json().get("data", {}).get("items", [])
        _report("Fivetran", True, f"({len(items)} groups)")
    else:
        _report("Fivetran", False, f"HTTP {r.status_code} – {r.text[:120]}")


# --- Main ------------------------------------------------------------------
def main() -> int:
    print("\nVerifying HiveMind partner credentials...\n")

    checks = [
        check_gemini,
        check_mongodb,
        check_arize,
        check_elastic,
        check_dynatrace,
        check_gitlab,
        check_fivetran,
    ]

    for fn in checks:
        try:
            fn()
        except requests.exceptions.RequestException as e:
            name = fn.__name__.replace("check_", "").title()
            _report(name, False, f"network error: {e}")
        except Exception as e:
            name = fn.__name__.replace("check_", "").title()
            _report(name, False, f"{type(e).__name__}: {e}")

    ok = sum(1 for _, status in _results if status)
    total = len(_results)
    print(f"\n{ok}/{total} OK")

    return 0 if ok == total else 1


if __name__ == "__main__":
    sys.exit(main())
