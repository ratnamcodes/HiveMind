import { ImageResponse } from "next/og";

// Social share card. Generated at build from the same hexagon mark as the favicon.
export const alt = "HiveMind, an AI crew that fixes your incidents end to end";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default function OpengraphImage() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          background: "#0b0d10",
          color: "#fafafa",
          padding: 84,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 22 }}>
          <div
            style={{
              width: 76,
              height: 76,
              borderRadius: 18,
              background: "#fafafa",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <svg width="46" height="46" viewBox="0 0 24 24">
              <path d="M12 2 L20.66 7 L20.66 17 L12 22 L3.34 17 L3.34 7 Z" fill="#0b0d10" />
            </svg>
          </div>
          <div style={{ fontSize: 46, fontWeight: 600, letterSpacing: -1 }}>HiveMind</div>
        </div>
        <div style={{ fontSize: 66, fontWeight: 600, lineHeight: 1.08, marginTop: 52, maxWidth: 960, letterSpacing: -1.5 }}>
          An AI crew that fixes your incidents, end to end.
        </div>
        <div style={{ fontSize: 30, color: "#9aa4b2", marginTop: 30, maxWidth: 900, lineHeight: 1.35 }}>
          Dynatrace flags the problem. Six specialists find the fix. You approve. Your service recovers.
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 14, marginTop: 44, fontSize: 24, color: "#6b7280" }}>
          <span style={{ width: 8, height: 8, borderRadius: 8, background: "#34d399" }} />
          Runs on your real Dynatrace data
        </div>
      </div>
    ),
    { ...size },
  );
}
