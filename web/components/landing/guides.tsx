import { cn } from "@/lib/utils";

// The Solar signature: dashed vertical "guide lines" flanking a section, and a faint diagonal
// hatch fill behind illustration panels. Both are decorative and pointer-events-none.

function VLine({ className }: { className?: string }) {
  return (
    <div
      className={cn("absolute inset-y-0 -my-20 w-px", className)}
      style={{ maskImage: "linear-gradient(transparent, white 5rem, white calc(100% - 5rem), transparent)" }}
    >
      <svg className="h-full w-full" preserveAspectRatio="none">
        <line x1="0" y1="0" x2="0" y2="100%" className="stroke-gray-300" strokeWidth="2" strokeDasharray="3 3" />
      </svg>
    </div>
  );
}

export function GuideLines({ quarters = false }: { quarters?: boolean }) {
  return (
    <div aria-hidden className="pointer-events-none absolute inset-0 select-none">
      <VLine className="left-0" />
      <VLine className="right-0" />
      <VLine className="left-1/2 -z-10" />
      {quarters && (
        <>
          <VLine className="left-1/4 -z-10 hidden sm:block" />
          <VLine className="left-3/4 -z-10 hidden sm:block" />
        </>
      )}
    </div>
  );
}

export function DiagonalPattern({ className }: { className?: string }) {
  return (
    <svg aria-hidden className={cn("absolute size-full", className)}>
      <defs>
        <pattern id="hm-diagonal" patternUnits="userSpaceOnUse" width="64" height="64">
          {Array.from({ length: 17 }, (_, i) => {
            const offset = i * 8;
            return (
              <path key={i} d={`M${-106 + offset} 110L${22 + offset} -18`} className="stroke-gray-200/70" strokeWidth="1" />
            );
          })}
        </pattern>
      </defs>
      <rect width="100%" height="100%" fill="url(#hm-diagonal)" />
    </svg>
  );
}
