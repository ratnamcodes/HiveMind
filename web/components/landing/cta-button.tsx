import Link from "next/link";
import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

// The Solar-style honey-gradient primary, plus a clean secondary. Renders as a Next <Link>.

const variants = {
  primary:
    "border-b-[1.5px] border-amber-700 bg-linear-to-b from-amber-400 to-amber-500 text-white shadow-[0_0_0_2px_rgba(0,0,0,0.04),0_0_14px_0_rgba(255,255,255,0.19)] hover:shadow-amber-300/70 hover:to-amber-500",
  secondary:
    "border border-gray-300 bg-white text-gray-900 shadow-xs hover:bg-gray-50",
  ghost: "border border-transparent text-gray-700 hover:bg-gray-100",
} as const;

export function CtaButton({
  href,
  children,
  variant = "primary",
  className,
}: {
  href: string;
  children: ReactNode;
  variant?: keyof typeof variants;
  className?: string;
}) {
  return (
    <Link
      href={href}
      className={cn(
        "inline-flex cursor-pointer items-center justify-center gap-1.5 rounded-md px-5 py-3 text-sm leading-4 font-medium tracking-wide whitespace-nowrap transition-all duration-200 ease-in-out focus:outline-none focus-visible:ring-2 focus-visible:ring-amber-500/50",
        variants[variant],
        className,
      )}
    >
      {children}
    </Link>
  );
}
