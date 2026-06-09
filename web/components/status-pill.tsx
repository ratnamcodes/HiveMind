import { Check, Hand, Loader2 } from "lucide-react";
import type { StatusPill as Pill } from "@/lib/types";
import { cn } from "@/lib/utils";

const VARIANTS = {
  thinking: {
    icon: Loader2,
    spin: true,
    cls: "border-amber-400/30 bg-amber-400/10 text-amber-300",
  },
  tool_call: {
    icon: Loader2,
    spin: true,
    cls: "animate-pulse border-sky-400/30 bg-sky-400/10 text-sky-300",
  },
  done: {
    icon: Check,
    spin: false,
    cls: "border-emerald-400/30 bg-emerald-400/10 text-emerald-300",
  },
  awaiting_human: {
    icon: Hand,
    spin: false,
    cls: "animate-pulse border-blue-400/40 bg-blue-400/15 text-blue-200",
  },
} as const;

/** Small pill showing an agent's work state: thinking · tool_call(tool) · done. */
export function StatusPill({ pill }: { pill: Pill }) {
  const v = VARIANTS[pill.state];
  const Icon = v.icon;
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-medium",
        v.cls,
      )}
    >
      <Icon className={cn("h-3 w-3", v.spin && "animate-spin")} />
      {pill.state === "tool_call" ? (
        <code className="font-mono">{pill.tool ?? "tool"}</code>
      ) : pill.state === "awaiting_human" ? (
        "paused for you"
      ) : (
        pill.state
      )}
    </span>
  );
}
