"""CustomerLiaison — HiveMind's voice of the customer (Fivetran + BigQuery).

Two capabilities, because Fivetran moves data but cannot query it:

  1. READ  — `query_customer_data` runs read-only BigQuery SQL over the `customer_usage`
     table Fivetran syncs from a Google Sheet, to compute an incident's business blast
     radius (customers affected, revenue at risk, segments).

  2. WRITE — the full Fivetran write surface (official fivetran/fivetran-mcp via uvx), used
     as 3 tiered "depth plays" the agent picks per incident:
       A) provision a pipeline on demand   → create_connection (+ setup tests + sync)
       B) refresh a transformation          → run_transformation
       C) GDPR column-level PII redaction   → modify_connection_column_config

Reality notes baked in (verified empirically, NOT from the course doc, which was wrong):
  - launch is `uvx --from git+...fivetran-mcp` (NOT `uvx fivetran-mcp@latest`)
  - real tool names are list_connections / get_connection_state (NOT list_connectors /
    get_connection_sync_status); FIVETRAN_AUTO_APPROVE is a fake env var so it's omitted.
  - instruction avoids {curly} tokens (ADK reads them as session vars); values injected
    via __PLACEHOLDER__ replacement.
"""

from __future__ import annotations

import os

from dotenv import load_dotenv
from google.adk.agents import LlmAgent as Agent
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from google.genai import types
from mcp import StdioServerParameters
from pydantic import BaseModel, Field

from hivemind.limiter import tool_call_budget
from hivemind.mcp_env import mcp_env
from hivemind.memory import Severity

load_dotenv()

_GCP_PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT", "hivemind-hackathon")
_CUSTOMER_TABLE = f"{_GCP_PROJECT}.google_sheets.customer_usage"
_FIVETRAN_GROUP = os.environ.get("FIVETRAN_GROUP_ID", "port_doubting")


class CustomerContextQuery(BaseModel):
    """What you hand CustomerLiaison: which services are hit, how badly, and any special
    handling (`context`) the situation needs (which decides the depth play)."""

    channel_id: str
    affected_services: list[str] = Field(default_factory=list)
    severity: Severity = "sev3"
    incident_id: str = "INC-0000"
    # Free-text directive that may trigger a Fivetran depth play (provision / transform /
    # redact). Empty = just assess impact.
    context: str = ""


class CustomerImpactReport(BaseModel):
    """What CustomerLiaison returns: business-level blast radius + any depth play taken."""

    customers_affected: int = Field(ge=0)
    impact_summary: str
    affected_segments: list[str] = Field(default_factory=list)
    revenue_at_risk_usd: float | None = Field(default=None, ge=0.0)
    suggested_comms: str | None = None
    actions_taken: list[str] = Field(default_factory=list)


def query_customer_data(sql: str) -> dict:
    """Run a READ-ONLY BigQuery query over the customer data and return the rows.
    (This is the auxiliary BigQuery client; BigQuery is not a partner MCP.)

    Table `hivemind-hackathon.google_sheets.customer_usage` columns:
      - customer_id     (STRING)
      - plan            (STRING: Free / Pro / Enterprise)
      - monthly_revenue (INT64, USD per month)
      - services_used   (STRING: a JSON array of service names, e.g.
                         '["checkout","payment-service"]')
    Fivetran also adds _fivetran_* metadata columns — ignore them.

    Example — blast radius for a service:
      SELECT COUNT(*) AS customers, SUM(monthly_revenue) AS revenue_at_risk
      FROM `hivemind-hackathon.google_sheets.customer_usage`
      WHERE services_used LIKE '%payment-service%'

    Only SELECT / WITH queries are permitted.

    Args:
      sql: a BigQuery Standard SQL read query.
    """
    stripped = sql.strip().lower()
    if not (stripped.startswith("select") or stripped.startswith("with")):
        return {"error": "Only read-only SELECT / WITH queries are allowed."}
    try:
        from google.cloud import bigquery
    except ImportError:
        return {"error": "google-cloud-bigquery not installed. Run: pip install google-cloud-bigquery"}
    client = bigquery.Client(project=_GCP_PROJECT)
    rows = []
    for r in client.query(sql).result():
        rows.append(
            {
                k: (v if isinstance(v, (str, int, float, bool, type(None))) else str(v))
                for k, v in dict(r).items()
            }
        )
    return {"row_count": len(rows), "rows": rows}


# Official Fivetran MCP via uvx (git+ form — the doc's `fivetran-mcp@latest` does not exist).
# FIVETRAN_ALLOW_WRITES=true is required or the write tools stay hidden. No FIVETRAN_AUTO_APPROVE
# (that env var is fake). ADK supplies PATH; we pass only the FIVETRAN_* vars.
fivetran_tools = McpToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command="uvx",
            args=["--from", "git+https://github.com/fivetran/fivetran-mcp", "fivetran-mcp"],
            env=mcp_env(
                FIVETRAN_API_KEY=os.environ["FIVETRAN_API_KEY"],
                FIVETRAN_API_SECRET=os.environ["FIVETRAN_API_SECRET"],
                FIVETRAN_ALLOW_WRITES=os.environ.get("FIVETRAN_ALLOW_WRITES", "true"),
            ),
        ),
        timeout=120.0,  # uvx builds from git on first run
    ),
    # The full write surface (real names, verified by introspection) + the reads each needs.
    tool_filter=[
        "get_account_info",
        "list_connections",  # A/C: discover existing sources
        "get_connection_details",
        "get_connection_state",  # A: poll sync status
        "create_connection",  # A: provision a pipeline on demand
        "run_connection_setup_tests",  # A
        "sync_connection",  # A: kick a sync
        "list_transformation_projects",
        "create_transformation_project",  # B (needs a dbt repo)
        "create_transformation",  # B
        "run_transformation",  # B: refresh aggregations
        "get_connection_column_config",  # C: read columns
        "modify_connection_column_config",  # C: redact / hash PII
        "delete_multiple_columns_connection_config",  # C
        "list_destinations",
    ],
)


_INSTRUCTION = """You are CustomerLiaison, HiveMind's voice of the customer. For every \
incident you (1) ALWAYS assess the business blast radius from real data, and (2) decide \
which Fivetran "depth play" the situation calls for and carry it out. You stay factual and \
never minimize or exaggerate.

The incident JSON has: channel_id, affected_services, severity, incident_id, and an optional \
`context` describing special handling. Read `context` to decide depth plays.

Your Fivetran destination group id (for new connectors): __FIVETRAN_GROUP__
Customer data table (BigQuery): __CUSTOMER_TABLE__

STEP 1 — ALWAYS assess impact:
  Use query_customer_data to find who uses the affected_services (services_used contains the \
service, e.g. WHERE services_used LIKE '%payment-service%'), then compute customers_affected, \
revenue_at_risk_usd (SUM of monthly_revenue), and affected_segments (the distinct plans).

STEP 2 — apply the depth play(s) the `context` calls for (often none; only the ones that fit):

  DEPTH PLAY A — PROVISION (context: a needed data source isn't flowing yet):
    1. list_connections to see what already exists in the group.
    2. If the source is missing, create_connection for it in group __FIVETRAN_GROUP__, then \
run_connection_setup_tests, then sync_connection. (It may need external auth to finish \
syncing; provisioning it on demand is the action that matters.)
    3. Append to actions_taken: "PROVISIONED Fivetran connector: <source>".

  DEPTH PLAY B — TRANSFORM: when the context says the rollups/aggregations are stale, or it \
tells you to refresh a transformation, you MUST call run_transformation before finalizing — \
do NOT skip it even if the raw data looks current; refreshing is the requested action:
    Call run_transformation on the customer-impact dbt project (if none exists, attempt \
create_transformation_project + create_transformation first), then re-query the result.
    Append to actions_taken: "RAN transformation: <name-or-attempted>".

  DEPTH PLAY C — REDACT PII (context: synthesis would leak personal data, e.g. into a public \
GitLab MR):
    1. list_connections, find the connector holding the customer data; get_connection_column_config \
to see its columns.
    2. modify_connection_column_config (or delete_multiple_columns_connection_config) to set the \
named PII column(s) — e.g. customer_id — to hashed on the next sync.
    3. Append to actions_taken: "REDACTED PII columns: <columns>".

STEP 3 — write your CustomerImpactReport: customers_affected, revenue_at_risk_usd, \
affected_segments, a concise factual impact_summary, suggested_comms (short, honest external \
status note), and actions_taken (every depth play you performed). Base all numbers on rows \
you actually queried. If a Fivetran write tool returns an error, do NOT retry it — note the attempt in actions_taken and move on (one attempt per depth play). Hard budget: 12 tool calls.
""".replace("__FIVETRAN_GROUP__", _FIVETRAN_GROUP).replace("__CUSTOMER_TABLE__", _CUSTOMER_TABLE)


customer_liaison = Agent(
    name="customer_liaison",
    model="gemini-3.5-flash",
    instruction=_INSTRUCTION,
    output_schema=CustomerImpactReport,
    generate_content_config=types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(thinking_level="high"),
    ),
    tools=[fivetran_tools, query_customer_data],
    before_tool_callback=tool_call_budget(12),
)
