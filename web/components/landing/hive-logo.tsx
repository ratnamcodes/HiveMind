import { Hexagon } from "lucide-react";
import { cn } from "@/lib/utils";

// The original HiveMind mark: a filled hexagon inside a rounded square badge (the War Room logo).
// Sized by the wrapper's className; the hexagon scales to half the badge.
export function HiveMark({ className }: { className?: string }) {
  return (
    <span className={cn("inline-flex items-center justify-center rounded-md bg-[#0b0d10] text-white", className)}>
      <Hexagon className="h-1/2 w-1/2" strokeWidth={2.5} fill="currentColor" />
    </span>
  );
}
