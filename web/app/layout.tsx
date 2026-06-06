import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { ChannelSidebar } from "@/components/channel-sidebar";
import { EventStream } from "@/components/event-stream";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "HiveMind · War Room",
  description: "Multi-agent incident response — war room",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} dark`}
      suppressHydrationWarning
    >
      <body className="h-screen overflow-hidden antialiased">
        <EventStream />
        <div className="flex h-full">
          <ChannelSidebar />
          <main className="flex min-w-0 flex-1">{children}</main>
        </div>
      </body>
    </html>
  );
}
