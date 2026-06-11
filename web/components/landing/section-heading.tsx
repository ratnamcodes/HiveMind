import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

// `inline-block` keeps the eyebrow's tick glued to the text in both left-aligned and centered sections.

export function Eyebrow({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <p className={cn("relative inline-block text-lg font-semibold tracking-tight text-orange-600", className)}>
      {children}
      <span className="absolute top-1 -left-[8px] h-5 w-[3px] rounded-r-sm bg-orange-500" />
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
