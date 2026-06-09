import type { ReactNode } from "react";
import { ChannelSidebar } from "@/components/channel-sidebar";
import { EventStream } from "@/components/event-stream";

// The war-room shell: the singleton /ws stream + the channel sidebar wrap every /c/* route.
// (The landing page at / has no sidebar — this is why the shell lives here, not in the root layout.)
export default function WarRoomLayout({ children }: { children: ReactNode }) {
  return (
    <div className="flex h-screen overflow-hidden">
      <EventStream />
      <ChannelSidebar />
      <main className="flex min-w-0 flex-1">{children}</main>
    </div>
  );
}
