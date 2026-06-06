import { AGENTS } from "@/lib/agents";
import type { AgentId } from "@/lib/types";
import { cn } from "@/lib/utils";

const SIZES = {
  sm: "h-6 w-6 text-[13px] rounded",
  md: "h-9 w-9 text-lg rounded-md",
  lg: "h-10 w-10 text-xl rounded-md",
} as const;

/** A bot-style rounded-square avatar in the agent's partner color. */
export function AgentAvatar({
  agent,
  size = "md",
}: {
  agent: AgentId;
  size?: keyof typeof SIZES;
}) {
  const meta = AGENTS[agent];
  return (
    <div
      title={`${meta.name} · ${meta.partner}`}
      className={cn(
        "flex shrink-0 select-none items-center justify-center text-white shadow-sm ring-2 ring-inset",
        meta.avatar,
        SIZES[size],
      )}
    >
      <span aria-hidden>{meta.emoji}</span>
    </div>
  );
}
