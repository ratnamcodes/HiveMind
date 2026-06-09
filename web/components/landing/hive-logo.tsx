// The HiveMind mark: a honey-amber hexagon (the hive) holding three linked nodes (the mind —
// a small swarm of agents acting as one). Renders crisp at favicon size and hero size alike.
export function HiveMark({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      aria-hidden="true"
    >
      <defs>
        <linearGradient id="hive-grad" x1="4" y1="1" x2="20" y2="23" gradientUnits="userSpaceOnUse">
          <stop stopColor="#FBBF24" />
          <stop offset="0.55" stopColor="#F59E0B" />
          <stop offset="1" stopColor="#D97706" />
        </linearGradient>
      </defs>
      {/* hive cell */}
      <path
        d="M12 1.2 21.36 6.6V17.4L12 22.8 2.64 17.4V6.6L12 1.2Z"
        fill="url(#hive-grad)"
      />
      {/* the swarm: three nodes, linked */}
      <g stroke="#FFFFFF" strokeWidth="1.1" strokeLinecap="round" opacity="0.95">
        <path d="M9 9.2 15 9.2" />
        <path d="M9 9.2 12 15" />
        <path d="M15 9.2 12 15" />
      </g>
      <g fill="#FFFFFF">
        <circle cx="9" cy="9.2" r="1.7" />
        <circle cx="15" cy="9.2" r="1.7" />
        <circle cx="12" cy="15" r="1.7" />
      </g>
    </svg>
  );
}
