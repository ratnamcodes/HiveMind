"use client";

import { useState } from "react";
import Link from "next/link";
import { Activity, GitPullRequest, Hexagon, Check, Loader2, ArrowRight, Lock } from "lucide-react";
import { cn } from "@/lib/utils";

type Status = { state: "idle" | "testing" | "ok" | "error"; msg?: string };

function ConnectCard({
  provider,
  title,
  partner,
  Icon,
  urlPlaceholder,
  tokenLabel,
  onConnected,
}: {
  provider: "dynatrace" | "gitlab";
  title: string;
  partner: string;
  Icon: typeof Activity;
  urlPlaceholder: string;
  tokenLabel: string;
  onConnected: (ok: boolean) => void;
}) {
  const [url, setUrl] = useState("");
  const [token, setToken] = useState("");
  const [status, setStatus] = useState<Status>({ state: "idle" });

  async function test() {
    setStatus({ state: "testing" });
    try {
      const r = await fetch("/api/onboarding/test", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ provider, url, token }),
      });
      const d = await r.json();
      if (d.ok) {
        setStatus({ state: "ok", msg: `Connected as ${d.identity}${d.detail ? ` · ${d.detail}` : ""}` });
        onConnected(true);
      } else {
        setStatus({ state: "error", msg: d.error || "Connection failed" });
        onConnected(false);
      }
    } catch (e) {
      setStatus({ state: "error", msg: String(e) });
      onConnected(false);
    }
  }

  return (
    <div className="rounded-lg border border-border bg-card p-5">
      <div className="flex items-center gap-2.5">
        <span className="flex h-8 w-8 items-center justify-center rounded-md border border-border bg-background text-foreground">
          <Icon className="h-4 w-4" strokeWidth={2} />
        </span>
        <div>
          <div className="text-sm font-semibold">{title}</div>
          <div className="font-mono text-[11px] uppercase tracking-wide text-muted-foreground">{partner}</div>
        </div>
        {status.state === "ok" && (
          <span className="ml-auto inline-flex items-center gap-1 rounded-full border border-emerald-400/30 bg-emerald-400/10 px-2 py-0.5 text-[11px] font-medium text-emerald-300">
            <Check className="h-3 w-3" /> Connected
          </span>
        )}
      </div>

      <div className="mt-4 space-y-2.5">
        <input
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder={urlPlaceholder}
          className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm outline-none placeholder:text-muted-foreground/60 focus:border-ring"
        />
        <input
          value={token}
          onChange={(e) => setToken(e.target.value)}
          type="password"
          placeholder={tokenLabel}
          className="w-full rounded-md border border-border bg-background px-3 py-2 font-mono text-sm outline-none placeholder:font-sans placeholder:text-muted-foreground/60 focus:border-ring"
        />
      </div>

      <div className="mt-3 flex items-center gap-3">
        <button
          type="button"
          onClick={test}
          disabled={status.state === "testing"}
          className="inline-flex items-center gap-2 rounded-md border border-border bg-background px-3 py-1.5 text-sm font-medium transition-colors hover:bg-accent disabled:opacity-50"
        >
          {status.state === "testing" ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : null}
          Test connection
        </button>
        {status.msg && (
          <span className={cn("text-xs", status.state === "ok" ? "text-emerald-300" : "text-destructive")}>
            {status.msg}
          </span>
        )}
      </div>
    </div>
  );
}

export default function Onboarding() {
  const [dt, setDt] = useState(false);
  const [gl, setGl] = useState(false);
  // Connect at least one to continue — the war room works on either, and you can add the other
  // any time. (Hard-gating on both blocks the demo whenever one tenant/token is unavailable.)
  const ready = dt || gl;

  return (
    <div className="min-h-screen bg-background text-foreground">
      <header className="border-b border-border">
        <div className="mx-auto flex h-14 max-w-3xl items-center gap-2 px-6">
          <span className="flex h-7 w-7 items-center justify-center rounded-md border border-border bg-foreground text-background">
            <Hexagon className="h-4 w-4" strokeWidth={2.5} fill="currentColor" />
          </span>
          <span className="text-sm font-semibold tracking-tight">HiveMind</span>
          <span className="ml-auto text-xs text-muted-foreground">Connect your stack</span>
        </div>
      </header>

      <main className="mx-auto max-w-3xl px-6 py-12">
        <h1 className="text-2xl font-semibold tracking-tight">Connect your stack</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          HiveMind reads incidents from Dynatrace and ships fixes to GitLab. Connect at least one to
          continue, then run your first real incident. Tokens are stored encrypted and never shown again.
        </p>

        <div className="mt-8 space-y-4">
          <ConnectCard
            provider="dynatrace"
            title="Dynatrace"
            partner="Observability"
            Icon={Activity}
            urlPlaceholder="Tenant URL (e.g. https://abc12345.apps.dynatrace.com)"
            tokenLabel="API token (dt0c01…)"
            onConnected={setDt}
          />
          <ConnectCard
            provider="gitlab"
            title="GitLab"
            partner="Source + merge requests"
            Icon={GitPullRequest}
            urlPlaceholder="GitLab URL (default https://gitlab.com)"
            tokenLabel="Personal access token (api, write_repository)"
            onConnected={setGl}
          />
        </div>

        <div className="mt-6 flex items-center gap-2 text-xs text-muted-foreground">
          <Lock className="h-3.5 w-3.5" /> Tokens are encrypted at rest and never used to train models.
        </div>

        <div className="mt-8 flex items-center justify-between border-t border-border pt-6">
          <Link href="/" className="text-sm text-muted-foreground hover:text-foreground">
            Back
          </Link>
          <Link
            href="/c/ops"
            aria-disabled={!ready}
            className={cn(
              "inline-flex items-center gap-2 rounded-lg px-5 py-2.5 text-sm font-semibold transition-opacity",
              ready ? "bg-foreground text-background hover:opacity-90" : "pointer-events-none bg-muted text-muted-foreground",
            )}
          >
            Enter the war room <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      </main>
    </div>
  );
}
