"""Environment for stdio MCP subprocesses.

ADK launches stdio MCP servers (npx / uvx) as child processes without inheriting our
environment, so we hand them PATH (to locate the npx/uvx binaries) and HOME (npm and uv
write their caches there) explicitly; otherwise the spawn fails in minimal container envs
with "[Errno 2] No such file or directory". Cache dirs default under /tmp, which is
writable on Cloud Run.
"""

from __future__ import annotations

import os


def mcp_env(**service_vars: str | None) -> dict[str, str]:
    """Base env (PATH/HOME/cache dirs) for a stdio MCP server, merged with service-specific vars.
    None-valued service vars are dropped so a missing optional credential doesn't blank the env."""
    env = {
        "PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"),
        "HOME": os.environ.get("HOME") or "/tmp",
        "NPM_CONFIG_CACHE": os.environ.get("NPM_CONFIG_CACHE") or "/tmp/.npm",
        "XDG_CACHE_HOME": os.environ.get("XDG_CACHE_HOME") or "/tmp/.cache",
        "UV_CACHE_DIR": os.environ.get("UV_CACHE_DIR") or "/tmp/.uv",
    }
    env.update({k: v for k, v in service_vars.items() if v is not None})
    return env
