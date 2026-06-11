// "Test connection" validates the credentials the user pastes by calling the
// Dynatrace + GitLab APIs server-side. If a field is blank, it falls back to server-side env
// vars (set these in the deploy: DT_ENVIRONMENT/DT_API_TOKEN/GITLAB_URL/GITLAB_TOKEN). Returns
// the identity it connected as, and a human-readable reason on failure.

const envFallback = (key: string): string => (process.env[key] || "").trim();

async function testDynatrace(tenant: string, token: string) {
  const base = (tenant || envFallback("DT_ENVIRONMENT")).replace(/\/$/, "").replace(".apps.", ".live.");
  const tok = token || envFallback("DT_API_TOKEN");
  if (!base || !tok) return { ok: false, error: "Paste your tenant URL and an API token (no default is configured)." };
  const r = await fetch(`${base}/api/v2/problems?pageSize=1`, { headers: { Authorization: `Api-Token ${tok}` } });
  if (!r.ok) {
    let detail = `HTTP ${r.status}`;
    try {
      const b = await r.json();
      if (b?.error?.message) detail = b.error.message;
    } catch {}
    if (r.status === 401 || r.status === 403) detail = "Token rejected — check the token and its scopes.";
    else if (r.status === 404) detail = "Tenant not found — check the URL (it may be expired).";
    return { ok: false, error: detail };
  }
  const host = base.replace(/^https?:\/\//, "").split(".")[0];
  return { ok: true, identity: `tenant ${host}`, detail: "problems API reachable" };
}

async function testGitlab(url: string, pat: string) {
  const base = (url || envFallback("GITLAB_URL") || "https://gitlab.com").replace(/\/$/, "");
  const tok = pat || envFallback("GITLAB_TOKEN");
  if (!tok) return { ok: false, error: "Paste a personal access token (no default is configured)." };
  const r = await fetch(`${base}/api/v4/user`, { headers: { "PRIVATE-TOKEN": tok } });
  if (!r.ok) {
    const detail = r.status === 401 ? "Token rejected — check the token and its scopes." : `HTTP ${r.status}`;
    return { ok: false, error: detail };
  }
  const u = await r.json();
  return { ok: true, identity: `@${u.username}`, detail: u.name || "" };
}

export async function POST(req: Request) {
  try {
    const body = await req.json().catch(() => ({}));
    const { provider, url, token } = body as { provider?: string; url?: string; token?: string };
    const res =
      provider === "gitlab" ? await testGitlab(url || "", token || "") : await testDynatrace(url || "", token || "");
    return Response.json(res);
  } catch (e) {
    return Response.json({ ok: false, error: String(e) }, { status: 500 });
  }
}
