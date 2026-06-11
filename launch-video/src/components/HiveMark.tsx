import React from "react";

// Current brand mark (origin/main web/app/icon.svg): a white filled hexagon inside an
// orange rounded-square badge. Simple, no swarm nodes. `nodeProgress` (0..1) gently
// scales/fades the hexagon in for the title reveal.
export const HiveMark: React.FC<{ size: number; nodeProgress?: number }> = ({
  size,
  nodeProgress = 1,
}) => {
  const p = Math.max(0, Math.min(1, nodeProgress));
  const hexScale = 0.6 + 0.4 * p;
  const hexOpacity = Math.min(1, p / 0.5);
  return (
    <svg viewBox="0 0 32 32" width={size} height={size} fill="none">
      <defs>
        <linearGradient id="hive-badge" x1="16" y1="0" x2="16" y2="32" gradientUnits="userSpaceOnUse">
          <stop stopColor="#FB923C" />
          <stop offset="1" stopColor="#F97316" />
        </linearGradient>
      </defs>
      <rect width="32" height="32" rx="7" fill="url(#hive-badge)" />
      <g transform={`translate(16 16) scale(${hexScale}) translate(-12 -12)`} fill="#FFFFFF" opacity={hexOpacity}>
        <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" />
      </g>
    </svg>
  );
};
