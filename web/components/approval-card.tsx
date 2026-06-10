"use client";

import { useState } from "react";
import { ExternalLink, ShieldCheck } from "lucide-react";
import { useWarRoom } from "@/lib/store";
import { cn } from "@/lib/utils";

/** The run PAUSED and is waiting on a human. Rendered above the composer with the drafted
 *  fix + who's affected + $ at risk, and buttons that resume the paused run on the backend. */
export function ApprovalCard({ channelId }: { channelId: string }) {
  const decision = useWarRoom((s) => s.decisionByChannel[channelId]);
  const respond = useWarRoom((s) => s.respondToDecision);
  const [busy, setBusy] = useState(false);
  if (!decision) return null;

  async function choose(id: string, label: string) {
    if (busy) return;
    setBusy(true);
    await respond(decision!.incident_id, channelId, id, label);
  }

  return (
    <div className="mx-4 mb-2 overflow-hidden rounded-lg border border-border border-l-2 border-l-blue-400/70 bg-card">
      <div className="flex items-center gap-2 border-b border-border px-4 py-2">
        <ShieldCheck className="h-4 w-4 shrink-0 text-blue-300" strokeWidth={2} />
        <span className="text-[11px] font-semibold uppercase tracking-wide text-blue-200">
          Paused for you
        </span>
        <span className="ml-auto animate-pulse text-[11px] text-blue-300/80">
          nothing has shipped yet
        </span>
      </div>

      <div className="space-y-2.5 px-4 py-3">
        <p className="text-sm font-semibold text-foreground">{decision.title}</p>
        {decision.prompt && (
          <p className="text-sm leading-relaxed text-foreground/85">{decision.prompt}</p>
        )}

        <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5 text-xs">
          {decision.impact && (
            <span className="font-semibold text-emerald-300">{decision.impact}</span>
          )}
          {decision.suspect_files?.map((f) => (
            <code key={f} className="rounded bg-muted px-1.5 py-0.5 font-mono text-foreground/80">
              {f}
            </code>
          ))}
          {decision.mr_url && (
            <a
              href={decision.mr_url}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1 text-blue-300 hover:text-blue-200"
            >
              <ExternalLink className="h-3 w-3" /> Review the merge request
            </a>
          )}
        </div>

        {decision.actions_taken && decision.actions_taken.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {decision.actions_taken.map((a) => (
              <span
                key={a}
                className="rounded-md border border-blue-400/30 bg-blue-400/10 px-2 py-0.5 text-[11px] font-medium text-blue-200"
              >
                {a}
              </span>
            ))}
          </div>
        )}

        <div className="flex flex-wrap gap-2 pt-1">
          {decision.options.map((o) => (
            <button
              key={o.id}
              type="button"
              disabled={busy}
              onClick={() => choose(o.id, o.label)}
              className={cn(
                "rounded-lg px-3.5 py-1.5 text-sm font-semibold transition-colors disabled:opacity-50",
                o.style === "primary"
                  ? "bg-emerald-500 text-white hover:bg-emerald-400"
                  : o.style === "danger"
                    ? "border border-red-400/40 bg-red-500/10 text-red-200 hover:bg-red-500/20"
                    : "border border-border bg-card text-foreground/90 hover:bg-accent",
              )}
            >
              {o.label}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
