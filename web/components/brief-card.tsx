"use client";

import { AlertTriangle } from "lucide-react";
import { isAgentId } from "@/lib/agents";
import { SEVERITY } from "@/lib/severity";
import { useWarRoom } from "@/lib/store";
import { cn } from "@/lib/utils";
import { AgentAvatar } from "./agent-avatar";

/** The pinned Incident Commander brief — the first thing a third person reads when a channel
 *  opens: what happened, how bad, who's on it, and (once Liaison reports) the business impact. */
export function BriefCard({ channelId }: { channelId: string }) {
  const brief = useWarRoom((s) => s.briefByChannel[channelId]);
  if (!brief) return null;
  const sev = SEVERITY[brief.severity];

  return (
    <div className="mx-4 mt-3 overflow-hidden rounded-lg border border-border bg-card">
      <div className="flex items-center gap-2 border-b border-border px-4 py-2">
        <AlertTriangle className="h-4 w-4 shrink-0 text-muted-foreground" strokeWidth={2} />
        <span className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
          Incident brief
        </span>
        {sev && (
          <span
            className={cn(
              "ml-auto shrink-0 rounded-full border px-2 py-0.5 text-[11px] font-semibold",
              sev.badge,
            )}
          >
            {sev.label}
          </span>
        )}
      </div>

      <div className="space-y-2.5 px-4 py-3">
        <p className="text-sm font-medium leading-relaxed text-foreground/95">{brief.what}</p>

        <div className="grid grid-cols-[88px_1fr] gap-x-3 gap-y-1.5 text-sm">
          <span className="pt-0.5 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Impact
          </span>
          <span
            className={cn(
              "font-semibold tabular-nums",
              brief.impact && brief.revenueAtRisk ? "text-emerald-400" : "text-muted-foreground",
            )}
          >
            {brief.impact ?? "Assessing customers + revenue at risk…"}
          </span>

          {brief.suspected && (
            <>
              <span className="pt-0.5 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Status
              </span>
              <span className="text-foreground/80">{brief.suspected}</span>
            </>
          )}
        </div>

        {brief.actionsTaken && brief.actionsTaken.length > 0 && (
          <div className="flex flex-wrap gap-1.5 pt-0.5">
            {brief.actionsTaken.map((a) => (
              <span
                key={a}
                className="rounded-md border border-blue-400/30 bg-blue-400/10 px-2 py-0.5 text-[11px] font-medium text-blue-200"
              >
                {a}
              </span>
            ))}
          </div>
        )}

        {brief.team && brief.team.length > 0 && (
          <div className="flex items-center gap-1.5 pt-1 text-xs text-muted-foreground">
            <span>On the case:</span>
            <div className="flex items-center gap-1">
              {brief.team.map((id) => (isAgentId(id) ? <AgentAvatar key={id} agent={id} size="sm" /> : null))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
