import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

// The Solar section header: a small amber eyebrow with a left tick, then a large headline.
// `inline-block` keeps the tick glued to the text in both left-aligned and centered sections.
// The headline carries the real heading semantics (h2/h3); the eyebrow is a styled label.

export function Eyebrow({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <p className={cn("relative inline-block text-lg font-semibold tracking-tight text-amber-600", className)}>
      {children}
      <span className="absolute top-1 -left-[8px] h-5 w-[3px] rounded-r-sm bg-amber-500" />
    </p>
  );
}

export function Headline({
  children,
  as: As = "h2",
  className,
}: {
  children: ReactNode;
  as?: "h2" | "h3";
  className?: string;
}) {
  return (
    <As className={cn("mt-2 text-3xl font-semibold tracking-tighter text-balance text-gray-900 md:text-4xl", className)}>
      {children}
    </As>
  );
}
