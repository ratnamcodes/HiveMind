import type { ReactNode } from "react";
import { redirect } from "next/navigation";
import { ChannelSidebar } from "@/components/channel-sidebar";
import { EventStream } from "@/components/event-stream";
import { currentUserEmail } from "@/lib/session";

// The war-room shell: the singleton /ws stream and the channel sidebar wrap every /c/* route.
// Reaching any /c/* route requires a signed-in session.
export default async function WarRoomLayout({ children }: { children: ReactNode }) {
  if (!(await currentUserEmail())) redirect("/sign-in");
  return (
    <div className="flex h-screen overflow-hidden">
      <EventStream />
      <ChannelSidebar />
      <main className="flex min-w-0 flex-1">{children}</main>
    </div>
  );
}
