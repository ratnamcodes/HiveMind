import type { ReactNode } from "react";
import { ChannelView } from "@/components/channel-view";

// The channel view lives in the layout (not the page) so it stays mounted while
// a thread occupies the slot ({children}). At /c/[id] the page renders nothing;
// at /c/[id]/t/[tid] the thread panel slides into the slot beside the channel.
export default function ChannelLayout({ children }: { children: ReactNode }) {
  return (
    <div className="flex h-full w-full min-w-0">
      <ChannelView />
      {children}
    </div>
  );
}
