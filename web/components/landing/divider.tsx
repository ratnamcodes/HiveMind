import { cn } from "@/lib/utils";
import type { ReactNode } from "react";

export function Divider({ className, children }: { className?: string; children?: ReactNode }) {
  return (
    <div className={cn("mx-auto my-6 flex w-full items-center justify-between gap-3 text-sm text-gray-500", className)}>
      {children ? (
        <>
          <div className="h-px w-full bg-linear-to-r from-transparent to-gray-200" />
          <div className="whitespace-nowrap text-inherit">{children}</div>
          <div className="h-px w-full bg-linear-to-l from-transparent to-gray-200" />
        </>
      ) : (
        <div className="h-px w-full bg-linear-to-l from-transparent via-gray-200 to-transparent" />
      )}
    </div>
  );
}

// The little animated wave of dots that marks a section break in the Solar template.
export function FeatureDivider({ className }: { className?: string }) {
  const dots = [
    { top: 0, left: 0, delay: 0 },
    { top: 0, left: 16, delay: 0 },
    { top: 4, left: 8, delay: 0.4 },
    { top: 8, left: 0, delay: 0.6 },
    { top: 8, left: 16, delay: 0.6 },
    { top: 12, left: 8, delay: 1 },
  ];
  return (
    <Divider className={className}>
      <div className="relative h-4 w-5">
        {dots.map((d, i) => (
          <div
            key={i}
            className="absolute size-1 rounded-full bg-amber-400/70"
            style={{ top: d.top, left: d.left, animation: `wave 2s infinite ease-in-out`, animationDelay: `${d.delay}s` }}
          />
        ))}
      </div>
    </Divider>
  );
}
