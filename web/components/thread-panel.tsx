"use client";

import { useEffect, useRef, useState, type KeyboardEvent } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { SendHorizontal, X } from "lucide-react";
import * as api from "@/lib/api";
import { useWarRoom } from "@/lib/store";
import type { Message } from "@/lib/types";
import { MessageItem } from "./message-item";

export function ThreadPanel() {
  const params = useParams<{ channel_id: string; thread_id: string }>();
  const channelMessages = useWarRoom(
    (s) => s.messagesByChannel[params.channel_id],
  );
  const [replies, setReplies] = useState<Message[]>([]);
  const [rootId, setRootId] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const seq = useRef(0);

  useEffect(() => {
    let active = true;
    api
      .getThread(params.thread_id)
      .then((t) => {
        if (active) {
          setReplies(t.messages);
          setRootId(t.rootMessageId);
        }
      })
      .catch(() => {});
    return () => {
      active = false;
    };
  }, [params.thread_id]);

  const root = channelMessages?.find((m) => m.id === rootId);

  function submit() {
    const text = draft.trim();
    if (!text) return;
    setReplies((r) => [
      ...r,
      {
        id: `tr-${++seq.current}`,
        channelId: params.channel_id,
        author: { type: "user", name: "you" },
        text,
        ts: new Date().toISOString(),
      },
    ]);
    setDraft("");
  }

  function onKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  }

  return (
    <aside className="flex w-[380px] shrink-0 animate-in flex-col border-l bg-background duration-200 slide-in-from-right-8 fade-in">
      <header className="flex h-14 shrink-0 items-center justify-between border-b px-4">
        <div className="leading-tight">
          <div className="text-sm font-semibold">Thread</div>
          <div className="text-[11px] text-muted-foreground">
            #{params.channel_id}
          </div>
        </div>
        <Link
          href={`/c/${params.channel_id}`}
          aria-label="Close thread"
          className="rounded-md p-1.5 text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
        >
          <X className="h-4 w-4" />
        </Link>
      </header>

      <div className="flex-1 overflow-y-auto py-3">
        {root && (
          <>
            <MessageItem message={root} />
            <div className="flex items-center gap-3 px-4 py-2">
              <span className="text-[11px] font-medium text-muted-foreground">
                {replies.length} {replies.length === 1 ? "reply" : "replies"}
              </span>
              <span className="h-px flex-1 bg-border" />
            </div>
          </>
        )}
        {replies.map((m) => (
          <MessageItem key={m.id} message={m} />
        ))}
      </div>

      <div className="px-4 pb-5 pt-1">
        <div className="flex items-end gap-2 rounded-xl border bg-card px-3 py-2.5 transition-colors focus-within:border-ring">
          <textarea
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={onKeyDown}
            rows={1}
            placeholder="Reply…"
            className="max-h-32 flex-1 resize-none bg-transparent text-sm outline-none placeholder:text-muted-foreground"
          />
          <button
            type="button"
            onClick={submit}
            disabled={!draft.trim()}
            aria-label="Send reply"
            className="rounded-md p-1.5 text-primary transition-colors hover:bg-accent disabled:opacity-30"
          >
            <SendHorizontal className="h-4 w-4" />
          </button>
        </div>
      </div>
    </aside>
  );
}
