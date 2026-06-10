import type { ReactNode } from "react";
import { redirect } from "next/navigation";
import { ChannelSidebar } from "@/components/channel-sidebar";
import { EventStream } from "@/components/event-stream";
import { currentUserEmail } from "@/lib/session";

// The war-room shell: the singleton /ws stream + the channel sidebar wrap every /c/* route.
// (The landing page at / has no sidebar — this is why the shell lives here, not in the root layout.)
// The product is gated: you must be signed in to reach any /c/* route.
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
