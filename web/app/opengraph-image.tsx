import { ImageResponse } from "next/og";

export const alt = "HiveMind · AI that fixes your incidents end to end";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

// A hive hexagon as a data-URI SVG so it renders reliably in the OG image renderer.
const HEX = `data:image/svg+xml;utf8,${encodeURIComponent(
  `<svg xmlns="http://www.w3.org/2000/svg" width="120" height="120" viewBox="0 0 24 24">
    <defs><linearGradient id="g" x1="4" y1="1" x2="20" y2="23" gradientUnits="userSpaceOnUse">
      <stop stop-color="#FB923C"/><stop offset="0.55" stop-color="#F97316"/><stop offset="1" stop-color="#EA580C"/>
    </linearGradient></defs>
    <path d="M12 1.2 21.36 6.6V17.4L12 22.8 2.64 17.4V6.6L12 1.2Z" fill="url(#g)"/>
    <g stroke="#fff" stroke-width="1.1" stroke-linecap="round" opacity="0.95">
      <path d="M9 9.2 15 9.2"/><path d="M9 9.2 12 15"/><path d="M15 9.2 12 15"/></g>
    <g fill="#fff"><circle cx="9" cy="9.2" r="1.7"/><circle cx="15" cy="9.2" r="1.7"/><circle cx="12" cy="15" r="1.7"/></g>
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
