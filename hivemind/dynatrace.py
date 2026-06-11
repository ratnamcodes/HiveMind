"""Thin synchronous Grail/Davis-CoPilot HTTP helpers, deliberately not routed through MCP."""

from __future__ import annotations

import json
import os
import re
import time
import urllib.parse
import urllib.request

from dotenv import load_dotenv

load_dotenv()


def _tenant() -> str:
    m = re.search(r"https?://([a-z0-9]+)\.", os.getenv("DT_ENVIRONMENT", ""))
    return m.group(1) if m else ""


_TID = _tenant()
_PLAT = os.getenv("DT_PLATFORM_TOKEN", "")
_APPS = f"https://{_TID}.apps.dynatrace.com" if _TID else ""
_LIVE = f"https://{_TID}.live.dynatrace.com" if _TID else ""
# Classic dt0c01 token with problems.read for the Problems API v2.
_CLASSIC = (
    os.getenv("DT_CONTROL_TOKEN")
    or os.getenv("DT_API_TOKEN_OTLP")
    or os.getenv("DT_API_TOKEN", "")
)


def available() -> bool:
    """True when the platform token + tenant are configured (so callers can no-op gracefully)."""
    return bool(_TID and _PLAT)


def _req(url: str, method: str = "GET", body: dict | None = None, timeout: float = 30.0) -> dict:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={"Authorization": f"Bearer {_PLAT}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310 (trusted host)
        return json.loads(r.read() or b"{}")


def _classic_get(path: str, timeout: float = 20.0) -> dict:
    """GET the classic Environment API v2 (live domain) with an Api-Token (problems/metrics/etc.)."""
    req = urllib.request.Request(
        f"{_LIVE}{path}",
        method="GET",
        headers={"Authorization": f"Api-Token {_CLASSIC}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310
        return json.loads(r.read() or b"{}")


def open_problems(service_name: str | None = None, hours: int = 2) -> list[dict]:
    """Open Davis problems from the Problems API v2. Returns [{id,title,severity,status,impact}].

    Best-effort: returns [] on any error or when no classic token / tenant is configured.
    """
    if not (_TID and _CLASSIC):
        return []
    sel = 'status("OPEN")'
    try:
        d = _classic_get(
            f"/api/v2/problems?from=now-{hours}h&problemSelector={urllib.parse.quote(sel)}"
        )
        out = []
        for p in d.get("problems", []):
            entities = [e.get("name", "") for e in p.get("affectedEntities", [])]
            # Match by affected entity or problem title: a log-event problem opens on
            # the environment entity, but its title names the service.
            haystack = " ".join(entities) + " " + (p.get("title") or "")
            if service_name and service_name not in haystack:
                continue
            out.append({
                "id": p.get("displayId") or p.get("problemId"),
                "title": p.get("title"),
                "severity": p.get("severityLevel"),
                "status": p.get("status"),
                "impact": p.get("impactLevel"),
                "entities": entities,
                "start": p.get("startTime"),
            })
        return out
    except Exception:  # noqa: BLE001
        return []


def dql(query: str, timeout: float = 20.0) -> list[dict]:
    """Execute a DQL query against Grail and poll to completion. Returns records ([] on miss).

    Best-effort: any transport/quota error returns [] so an incident run never crashes on telemetry.
    """
    if not available():
        return []
    try:
        r = _req(f"{_APPS}/platform/storage/query/v1/query:execute", "POST", {"query": query})
        token = r.get("requestToken")
        steps = max(1, int(timeout / 0.8))
        for _ in range(steps):
            if r.get("state") == "SUCCEEDED":
                break
            if not token:
                break
            time.sleep(0.8)
            r = _req(
                f"{_APPS}/platform/storage/query/v1/query:poll?"
                + urllib.parse.urlencode({"request-token": token})
            )
        return r.get("result", {}).get("records", []) or []
    except Exception:  # noqa: BLE001
        return []


def nl2dql(text: str, timeout: float = 30.0) -> str:
    """Davis CoPilot: translate natural language → DQL. Returns the generated DQL ('' on failure)."""
    if not available():
        return ""
    try:
        r = _req(
            f"{_APPS}/platform/davis/copilot/v0.2/skills/nl2dql:generate",
            "POST",
            {"text": text},
            timeout,
        )
        return (r.get("dql") or "").strip()
    except Exception:  # noqa: BLE001
        return ""


def _svc_filter(service: str) -> str:
    """Match a service across both ingest paths: OTLP app logs carry it in `service.name`
    (log.source is null), the classic-ingest seed carries it in `log.source`. coalesce + a
    forgiving substring so "checkout" matches the app's "checkout-service"."""
    s = service.replace('"', "")
    return f'| fieldsAdd _svc = coalesce(`service.name`, log.source) | filter contains(_svc, "{s}")'


def count_service_errors(service: str, minutes: int = 60) -> int:
    """Count of error/warn logs Grail holds for a service over the window."""
    recs = dql(
        f"fetch logs, from:now()-{minutes}m {_svc_filter(service)} "
        f'| filter loglevel=="ERROR" or loglevel=="WARN" or status=="ERROR" '
        f"| summarize c=count() | fields c",
        timeout=20.0,
    )
    if recs:
        try:
            return int(recs[0].get("c") or 0)
        except (TypeError, ValueError):
            return 0
    return 0


def peak_latency(service: str = "checkout", minutes: int = 30) -> int | None:
    """Worst latency (ms) over the window from the OTLP `checkout.latency_ms` attribute."""
    recs = dql(
        f"fetch logs, from:now()-{minutes}m {_svc_filter(service)} "
        f"| filter isNotNull(`checkout.latency_ms`) "
        f"| summarize peak=max(toLong(`checkout.latency_ms`)) | fields peak",
        timeout=20.0,
    )
    if recs:
        try:
            return int(recs[0].get("peak") or 0)
        except (TypeError, ValueError):
            return None
    return None


_MS = re.compile(r"(\d{1,6})\s*ms")


def srg_validate(slo_ms: int = 300, minutes: int = 5) -> tuple[str, float] | None:
    """Evaluate the Site Reliability Guardian's objective against live Grail: the same DQL and
    threshold the "Checkout SLO recovery guardian" defines (avg checkout latency <= SLO). Returns
    (verdict, value_ms) where verdict is PASS|FAIL, or None on no data."""
    recs = dql(
        f'fetch logs, from:now()-{minutes}m | filter `service.name`=="checkout-service" '
        f"| filter isNotNull(`checkout.latency_ms`) "
        f"| summarize value = avg(toDouble(`checkout.latency_ms`))",
        timeout=20.0,
    )
    if not recs:
        return None
    try:
        val = float(recs[0].get("value"))
    except (TypeError, ValueError):
        return None
    return ("PASS" if val <= slo_ms else "FAIL", round(val, 1))


def recent_latency(service: str = "checkout", minutes: int = 15) -> tuple[int, str, str] | None:
    """Most-recent latency (ms) for a service from Grail, or None.

    Prefers the structured OTLP attribute `checkout.latency_ms`; falls back to parsing 'NNNms'
    out of the log line, so it works for both the OTLP app logs and the classic-ingest seeds.
    """
    recs = dql(
        f"fetch logs, from:now()-{minutes}m {_svc_filter(service)} "
        f"| sort timestamp desc | limit 40",
        timeout=20.0,
    )
    for r in recs:
        v = r.get("checkout.latency_ms")
        if v is not None:
            try:
                return int(float(v)), str(r.get("content", "")), str(r.get("timestamp", ""))
            except (TypeError, ValueError):
                pass
        m = _MS.search(str(r.get("content", "")))
        if m:
            return int(m.group(1)), str(r.get("content", "")), str(r.get("timestamp", ""))
    return None


if __name__ == "__main__":
    print("available:", available(), "tenant:", _TID)
    q = nl2dql(
        "Show checkout-service error logs in the last hour where checkout latency breached the "
        "300ms SLO, most recent first"
    )
    print("\nDavis CoPilot nl2dql ->\n", q)
    print("\ncheckout-service error count (60m):", count_service_errors("checkout-service", 60))
    print("recent checkout latency:", recent_latency("checkout-service", 1440))
