"use client";

import { useWarRoom } from "@/lib/store";
import { AGENTS, isAgentId } from "@/lib/agents";
import { cn } from "@/lib/utils";

function Dots() {
  return (
    <span className="inline-flex items-end gap-0.5 pb-0.5">
      {[0, 150, 300].map((d) => (
        <span
          key={d}
          className="h-1 w-1 animate-bounce rounded-full bg-current"
          style={{ animationDelay: `${d}ms`, animationDuration: "900ms" }}
        />
      ))}
    </span>
  );
}

/**
 * Liveness bar pinned above the composer while the crew works an incident: shows which agent
 * is active and what it's doing. Hidden once resolved or while paused for a human decision.
 */
export function LiveActivity({ channelId }: { channelId: string }) {
  const messages = useWarRoom((s) => s.messagesByChannel[channelId]);
  const decision = useWarRoom((s) => s.decisionByChannel[channelId]);
  const brief = useWarRoom((s) => s.briefByChannel[channelId]);

  // Only live on an in-flight incident (a brief is emitted when one opens).
  if (!brief) return null;
  if (!messages || messages.length === 0) return null;
  const resolved = messages.some(
    (m) => m.author.type === "system" && /incident (resolved|escalated)/i.test(m.text),
  );
  // The approval card owns the screen when a human decision is pending.
  if (resolved || decision) return null;

  // The most recent agent still working (its pill hasn't reached "done").
  let active: { agent: string; state: string; tool?: string } | null = null;
  for (let i = messages.length - 1; i >= 0; i--) {
    const m = messages[i];
    if (m.author.type === "agent" && m.pill && m.pill.state !== "done") {
      active = {
        agent: m.author.type === "agent" ? m.author.agent : "",
        state: m.pill.state,
        tool: m.pill.tool,
      };
      break;
    }
  }

  const meta = active && isAgentId(active.agent) ? AGENTS[active.agent] : null;
  const Icon = meta?.icon;
  const verb =
    active?.state === "tool_call" && active.tool
      ? "is running"
      : active
        ? "is investigating"
        : "is working the incident";

  return (
    <div className="flex shrink-0 items-center gap-2.5 border-t border-amber-400/25 bg-amber-400/[0.05] px-4 py-2">
      <span className="relative flex h-2 w-2 shrink-0">
        <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-amber-400/70" />
        <span className="relative inline-flex h-2 w-2 rounded-full bg-amber-400" />
      </span>
      {Icon && <Icon className={cn("h-3.5 w-3.5 shrink-0", meta?.nameColor)} strokeWidth={2} />}
      <span className="min-w-0 truncate text-xs text-muted-foreground">
        <span className={cn("font-semibold", meta?.nameColor ?? "text-foreground")}>
          {meta ? meta.name : "HiveMind crew"}
        </span>{" "}
        {verb}
        {active?.state === "tool_call" && active.tool ? (
          <code className="ml-1 rounded bg-muted px-1 font-mono text-[11px] text-foreground/80">
            {active.tool}
          </code>
        ) : null}
      </span>
      <span className="ml-auto text-amber-300/90">
        <Dots />
      </span>
    </div>
  );
}
