import { ImageResponse } from "next/og";

export const size = { width: 180, height: 180 };
export const contentType = "image/png";

export default function AppleIcon() {
  return new ImageResponse(
    (
      <div style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", background: "#fafafa" }}>
        <svg width="108" height="108" viewBox="0 0 24 24">
          <path d="M12 2 L20.66 7 L20.66 17 L12 22 L3.34 17 L3.34 7 Z" fill="#0b0d10" />
        </svg>
      </div>
    ),
    { ...size },
  );
}
