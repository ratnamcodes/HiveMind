"use client";

import { useEffect, useRef } from "react";
import { useWarRoom } from "@/lib/store";
import { within } from "@/lib/format";
import type { Message } from "@/lib/types";
import { MessageItem } from "./message-item";

function sameAuthor(a: Message, b: Message): boolean {
  if (a.author.type !== b.author.type) return false;
  if (a.author.type === "agent" && b.author.type === "agent") {
    return a.author.agent === b.author.agent;
  }
  if (a.author.type === "user" && b.author.type === "user") {
    return a.author.name === b.author.name;
  }
  return false;
}

export function MessageList({ channelId }: { channelId: string }) {
  const messages = useWarRoom((s) => s.messagesByChannel[channelId]);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = containerRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages?.length]);

  if (!messages) {
    return (
      <div className="flex flex-1 items-center justify-center text-sm text-muted-foreground">
        Loading messages…
      </div>
    );
  }

  return (
    <div ref={containerRef} className="flex-1 overflow-y-auto pb-4">
      {messages.map((m, i) => {
        const prev = messages[i - 1];
        const grouped =
          !!prev &&
          m.author.type !== "system" &&
          sameAuthor(prev, m) &&
          within(prev.ts, m.ts) &&
          !m.pill;
        return <MessageItem key={m.id} message={m} grouped={grouped} />;
      })}
      <div className="h-2" />
    </div>
  );
}
