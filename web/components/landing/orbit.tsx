import type { ReactNode } from "react";

// Objects orbiting a center mark (ported from the Solar template). Used for the "it catches the
// problem" illustration — partner systems circling the hive.
interface OrbitProps {
  radiusPx?: number;
  children: ReactNode;
  orbitingObjects: ReactNode[];
  defaultObjectSize?: number;
  durationSeconds?: number;
  keepUpright?: boolean;
}

export function Orbit({
  radiusPx = 144,
  children,
  orbitingObjects = [],
  defaultObjectSize = 32,
  durationSeconds = 8,
  keepUpright = false,
}: OrbitProps) {
  const orbitDiameter = radiusPx * 2;
  const containerSize = orbitDiameter + defaultObjectSize;
  const initialOffset = radiusPx + defaultObjectSize / 2;

  const positioned = orbitingObjects.map((object, index) => {
    const delaySeconds = -(index * (durationSeconds / orbitingObjects.length));
    return (
      <div
        key={index}
        className="absolute flex items-center justify-center"
        style={{
          animationName: "spin",
          animationDuration: `${durationSeconds}s`,
          animationTimingFunction: "linear",
          animationIterationCount: "infinite",
          animationDelay: `${delaySeconds}s`,
          transformOrigin: `calc(50% + ${radiusPx}px) 50%`,
          left: `calc(50% - ${initialOffset}px)`,
          top: `calc(50% - ${defaultObjectSize / 2}px)`,
          width: `${defaultObjectSize}px`,
          height: `${defaultObjectSize}px`,
        }}
      >
        <div
          className="flex h-full w-full items-center justify-center"
          style={
            keepUpright
              ? {
                  animationName: "spin",
                  animationDuration: `${durationSeconds}s`,
                  animationTimingFunction: "linear",
                  animationIterationCount: "infinite",
                  animationDelay: `${delaySeconds}s`,
                  animationDirection: "reverse",
                }
              : undefined
          }
        >
          {object}
        </div>
      </div>
    );
  });

  return (
    <div
      className="relative flex items-center justify-center"
      style={{ width: `${containerSize}px`, height: `${containerSize}px` }}
    >
      <div
        className="absolute animate-pulse rounded-full border border-gray-300 bg-gray-500/5"
        style={{ width: `${orbitDiameter}px`, height: `${orbitDiameter}px` }}
      />
      {positioned}
      {children}
    </div>
  );
}
