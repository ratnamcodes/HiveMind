# syntax=docker/dockerfile:1

# --- Stage 1: builder ------------------------------------------------------
FROM python:3.12-slim AS builder

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# --- Stage 2: runtime ------------------------------------------------------
FROM python:3.12-slim AS runtime

WORKDIR /app

# Runtime system deps:
#   redis-server  — bundled broker for the event bus (core pub/sub). The LangGraph checkpointer
#                   prefers RediSearch, but stock redis-server lacks it, so the orchestrator's
#                   _checkpointer() falls back to an in-process MemorySaver (fine on this single
#                   pinned instance — it survives the pause->approve->resume hop in-process).
#   nodejs/npx    — the Detective/CodeArch/Reviewer agents spawn MCP servers via npx
#   git           — uvx clones the Fivetran MCP from GitHub for the Liaison agent
#   curl/ca-certs — node install + outbound HTTPS to Dynatrace/GitLab/Vertex
RUN apt-get update \
    && apt-get install -y --no-install-recommends redis-server curl ca-certificates git \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# uv provides `uvx` for the Fivetran MCP server.
RUN pip install --no-cache-dir uv

# Pre-install the stdio MCP servers the agents spawn. Baking them in means `npx` resolves them
# instantly at runtime instead of downloading on the first incident (slow and flaky in a cold
# Cloud Run container). The agents still launch via `npx -y <pkg>`, which now hits the cache.
RUN npm install -g @zereight/mcp-gitlab @dynatrace-oss/dynatrace-mcp-server@latest

COPY . .
RUN chmod +x /app/deploy/start.sh

ENV PORT=8080 \
    REDIS_URL=redis://localhost:6379

EXPOSE 8080

CMD ["/app/deploy/start.sh"]
