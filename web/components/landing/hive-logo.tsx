import { Hexagon } from "lucide-react";
import { cn } from "@/lib/utils";

// The HiveMind mark: a filled hexagon in a rounded square badge. On the landing the badge is the
// honey-orange of the CTAs. `tone="white"` is the inverse (white badge, orange hexagon) for use on
// an orange background like the testimonial, where a solid orange badge would disappear.
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
