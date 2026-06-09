import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

export const metadata: Metadata = {
  metadataBase: new URL(process.env.NEXT_PUBLIC_SITE_URL || "https://hivemind.app"),
  title: "HiveMind · AI that fixes your incidents end to end",
  description:
    "The moment Dynatrace flags a real problem, six AI specialists find the cause in your live data, open the fix in GitLab, and prove your service recovered. You approve every change.",
  openGraph: {
    title: "HiveMind · AI that fixes your incidents end to end",
    description:
      "Dynatrace flags the problem. Six specialists find the fix. You approve. Your service recovers.",
    siteName: "HiveMind",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "HiveMind · AI that fixes your incidents end to end",
    description: "Dynatrace flags the problem. Six specialists find the fix. You approve. Your service recovers.",
  },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} dark`}
      suppressHydrationWarning
    >
      <body className="antialiased">{children}</body>
    </html>
  );
}
