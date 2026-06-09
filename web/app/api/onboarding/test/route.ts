import { readFileSync } from "node:fs";
import { join } from "node:path";

// Real "Test connection" — validates the credentials the user pastes by calling the live
// Dynatrace + GitLab APIs server-side. If a field is blank, it falls back to the repo .env
// (so the demo works without re-pasting tokens). Returns the real identity it connected as.

function envFallback(key: string): string {
  try {
    const txt = readFileSync(join(process.cwd(), "..", ".env"), "utf8");
    // .env may have duplicate keys (e.g. two DT_API_TOKEN); take the last non-empty.
    let val = "";
    for (const line of txt.split("\n")) {
      const m = line.match(new RegExp(`^${key}=(.*)$`));
      if (m && m[1].trim()) val = m[1].trim();
    }
    return val;
  } catch {
    return "";
  }
}

async function testDynatrace(tenant: string, token: string) {
  const base = (tenant || envFallback("DT_ENVIRONMENT")).replace(/\/$/, "").replace(".apps.", ".live.");
  const tok = token || envFallback("DT_API_TOKEN");
  if (!base || !tok) return { ok: false, error: "Missing tenant URL or token" };
  const r = await fetch(`${base}/api/v2/problems?pageSize=1`, { headers: { Authorization: `Api-Token ${tok}` } });
  if (!r.ok) return { ok: false, error: `HTTP ${r.status}` };
  const host = base.replace(/^https?:\/\//, "").split(".")[0];
  return { ok: true, identity: `tenant ${host}`, detail: "problems API reachable" };
}

async function testGitlab(url: string, pat: string) {
  const base = (url || envFallback("GITLAB_URL") || "https://gitlab.com").replace(/\/$/, "");
  const tok = pat || envFallback("GITLAB_TOKEN");
  if (!tok) return { ok: false, error: "Missing personal access token" };
  const r = await fetch(`${base}/api/v4/user`, { headers: { "PRIVATE-TOKEN": tok } });
  if (!r.ok) return { ok: false, error: `HTTP ${r.status}` };
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
