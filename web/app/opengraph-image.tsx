import { ImageResponse } from "next/og";

export const alt = "HiveMind · AI that fixes your incidents end to end";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

// The hexagon badge as a data-URI SVG so it renders reliably in the OG image renderer.
const HEX = `data:image/svg+xml;utf8,${encodeURIComponent(
  `<svg xmlns="http://www.w3.org/2000/svg" width="120" height="120" viewBox="0 0 32 32">
    <defs><linearGradient id="g" x1="16" y1="0" x2="16" y2="32" gradientUnits="userSpaceOnUse">
      <stop stop-color="#FB923C"/><stop offset="1" stop-color="#F97316"/></linearGradient></defs>
    <rect width="32" height="32" rx="7" fill="url(#g)"/>
    <g transform="translate(4 4)" fill="#FFFFFF">
      <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/>
    </g>
  </svg>`,
)}`;

export default function OpengraphImage() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          background: "#0B0D10",
          backgroundImage: "radial-gradient(60% 50% at 30% 0%, rgba(245,158,11,0.18), transparent 70%)",
          padding: "72px",
          fontFamily: "sans-serif",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 20 }}>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={HEX} width={72} height={72} alt="" />
          <div style={{ color: "#fff", fontSize: 40, fontWeight: 600, letterSpacing: -1 }}>HiveMind</div>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
          <div style={{ color: "#fff", fontSize: 76, fontWeight: 700, letterSpacing: -3, lineHeight: 1.05 }}>
            Incidents, fixed end to end.
          </div>
          <div style={{ color: "#A1A1AA", fontSize: 30, maxWidth: 900, lineHeight: 1.35 }}>
            Dynatrace flags the problem. Six AI specialists find the fix, open the merge request, and prove the
            recovery. You approve every change.
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 14, color: "#71717A", fontSize: 24 }}>
          <span style={{ color: "#F97316" }}>●</span>
          Dynatrace · GitLab · Elastic · MongoDB · BigQuery · Vertex AI
        </div>
      </div>
    ),
    { ...size },
  );
}
