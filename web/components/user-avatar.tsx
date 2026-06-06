import { cn } from "@/lib/utils";

const SIZES = {
  sm: "h-6 w-6 text-[10px] rounded",
  md: "h-9 w-9 text-xs rounded-md",
} as const;

/** Neutral rounded-square avatar with initials, for human authors. */
export function UserAvatar({
  name,
  size = "md",
}: {
  name: string;
  size?: keyof typeof SIZES;
}) {
  const initials = name.replace(/[^a-z]/gi, "").slice(0, 2).toUpperCase() || "?";
  return (
    <div
      className={cn(
        "flex shrink-0 select-none items-center justify-center bg-zinc-600 font-semibold text-zinc-100 shadow-sm",
        SIZES[size],
      )}
    >
      {initials}
    </div>
  );
}
