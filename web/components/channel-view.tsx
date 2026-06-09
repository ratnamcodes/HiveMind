"use client";

import { useEffect } from "react";
import { useParams } from "next/navigation";
import { CheckCircle2, Hash } from "lucide-react";
import { useWarRoom } from "@/lib/store";
import { SEVERITY } from "@/lib/severity";
import { cn } from "@/lib/utils";
import { MessageList } from "./message-list";
import { Composer } from "./composer";
import { BriefCard } from "./brief-card";
import { ApprovalCard } from "./approval-card";
import { LiveActivity } from "./live-activity";

export function ChannelView() {
  const params = useParams<{ channel_id: string }>();
  const channelId = params.channel_id;
  const channels = useWarRoom((s) => s.channels);
  const loadChannels = useWarRoom((s) => s.loadChannels);
  const loadMessages = useWarRoom((s) => s.loadMessages);
  const channel = channels.find((c) => c.id === channelId);

  useEffect(() => {
    loadChannels();
  }, [loadChannels]);

  useEffect(() => {
    if (channelId) loadMessages(channelId);
  }, [channelId, loadMessages]);

  const sev = channel?.severity ? SEVERITY[channel.severity] : null;

  return (
    <div className="flex h-full min-w-0 flex-1 flex-col bg-background">
      <header className="flex h-14 min-w-0 shrink-0 items-center gap-2 border-b px-4">
        {channel?.resolved ? (
          <CheckCircle2 className="h-4 w-4 shrink-0 text-muted-foreground" />
        ) : (
          <Hash className="h-4 w-4 shrink-0 text-muted-foreground" />
        )}
        <h1 className="shrink-0 whitespace-nowrap font-semibold text-foreground">
          {channel?.name ?? channelId}
        </h1>
        {sev && (
          <span
            className={cn(
              "shrink-0 rounded-full border px-2 py-0.5 text-[11px] font-semibold",
              sev.badge,
            )}
          >
            {channel?.resolved ? "RESOLVED" : sev.label}
          </span>
        )}
        {channel?.topic && (
          <>
            <span className="shrink-0 text-border">|</span>
            <p className="min-w-0 truncate text-sm text-muted-foreground">
              {channel.topic}
            </p>
          </>
        )}
      </header>

      <BriefCard channelId={channelId} />
      <MessageList channelId={channelId} />
      <LiveActivity channelId={channelId} />
      <ApprovalCard channelId={channelId} />
      <Composer channelId={channelId} channelName={channel?.name ?? channelId} />
    </div>
  );
}
