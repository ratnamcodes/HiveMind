import { AGENTS } from "@/lib/agents";
import type { AgentId } from "@/lib/types";
import { cn } from "@/lib/utils";

const SIZES = {
  sm: { box: "h-6 w-6 rounded", icon: "h-3.5 w-3.5" },
  md: { box: "h-9 w-9 rounded-md", icon: "h-4 w-4" },
  lg: { box: "h-10 w-10 rounded-md", icon: "h-5 w-5" },
} as const;

export function AgentAvatar({
  agent,
  size = "md",
}: {
  agent: AgentId;
  size?: keyof typeof SIZES;
}) {
  const meta = AGENTS[agent];
  const Icon = meta.icon;
  const s = SIZES[size];
  return (
    <div
      title={`${meta.name} · ${meta.partner}`}
      className={cn(
        "flex shrink-0 select-none items-center justify-center",
        meta.avatar,
        s.box,
      )}
    >
      <Icon className={s.icon} strokeWidth={2} />
    </div>
  );
}
