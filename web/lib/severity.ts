import type { Severity } from "@/lib/types";

// Severity → color tokens for the sidebar stripe, header badge, and dot.
// Literal class strings so Tailwind v4's scanner keeps them.
export const SEVERITY: Record<
  Severity,
  { label: string; stripe: string; badge: string; dot: string }
> = {
  sev1: {
    label: "SEV1",
    stripe: "bg-red-500",
    badge: "border-red-500/40 bg-red-500/10 text-red-300",
    dot: "bg-red-500",
  },
  sev2: {
    label: "SEV2",
    stripe: "bg-orange-500",
    badge: "border-orange-500/40 bg-orange-500/10 text-orange-300",
    dot: "bg-orange-500",
  },
  sev3: {
    label: "SEV3",
    stripe: "bg-amber-400",
    badge: "border-amber-400/40 bg-amber-400/10 text-amber-200",
    dot: "bg-amber-400",
  },
};
