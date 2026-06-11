import { Hexagon } from "lucide-react";
import { cn } from "@/lib/utils";

// HiveMind mark; tone="white" inverts for orange backgrounds.
export function HiveMark({
  className,
  tone = "orange",
}: {
  className?: string;
  tone?: "orange" | "white";
}) {
  const badge =
    tone === "white"
      ? "bg-white text-orange-500 shadow-sm"
      : "bg-linear-to-b from-orange-400 to-orange-500 text-white";
  return (
    <span className={cn("inline-flex items-center justify-center rounded-md", badge, className)}>
      <Hexagon className="h-1/2 w-1/2" strokeWidth={2.5} fill="currentColor" />
    </span>
  );
}
