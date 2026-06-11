// In-memory mock backend for the war-room, imported only by the route handlers under app/api.

import type { Channel, Message, Thread } from "@/lib/types";

const NOW = Date.now();
/** Build an ISO timestamp `mins` minutes before server start. */
const ago = (mins: number): string => new Date(NOW - mins * 60_000).toISOString();

let _seq = 1000;
const nextId = (prefix: string): string => `${prefix}-${++_seq}`;

// No pre-seeded incident channels; incident channels are created live over /ws.
const channels: Channel[] = [
  {
    id: "ops",
    name: "ops",
    kind: "ops",
    unread: 0,
    topic: "HiveMind control plane — 6 agents standing by",
  },
  {
    id: "deploys",
    name: "deploys",
    kind: "ops",
    unread: 0,
    topic: "Release + deploy notifications",
  },
  {
    id: "general",
    name: "general",
    kind: "ops",
    unread: 0,
    topic: "Engineering team",
  },
];

const messages: Record<string, Message[]> = {
  ops: [
    {
      id: "m-ops-1",
      channelId: "ops",
      author: { type: "system" },
      text: "HiveMind online. 6 specialists connected: Detective, LogDiver, CodeArch, Liaison, Scribe, Reviewer.",
      ts: ago(180),
    },
    {
      id: "m-ops-2",
      channelId: "ops",
      author: { type: "agent", agent: "scribe" },
      text: "Nightly incident digest written to Atlas — 3 incidents in the last 24h, all resolved.",
      ts: ago(140),
      pill: { state: "done" },
    },
    {
      id: "m-ops-3",
      channelId: "ops",
      author: { type: "system" },
      text: "New incident channel created: #inc-checkout-latency (sev2)",
      ts: ago(32),
    },
  ],
};

const threads: Record<string, Thread> = {};

export function getChannels(): Channel[] {
  return channels;
}

export function getMessages(channelId: string): Message[] {
  return messages[channelId] ?? [];
}

export function addMessage(channelId: string, text: string, authorName = "you"): Message {
  const msg: Message = {
    id: nextId("m-user"),
    channelId,
    author: { type: "user", name: authorName },
    text,
    ts: new Date().toISOString(),
    mentions: extractMentions(text),
  };
  (messages[channelId] ??= []).push(msg);
  // Reading a channel clears its unread badge.
  const ch = channels.find((c) => c.id === channelId);
  if (ch) {
    ch.unread = 0;
    ch.isNew = false;
  }
  return msg;
}

export function getThread(threadId: string): Thread | undefined {
  return threads[threadId];
}

export function markRead(channelId: string): void {
  const ch = channels.find((c) => c.id === channelId);
  if (ch) {
    ch.unread = 0;
    ch.isNew = false;
  }
}

const AGENT_HANDLES = [
  "detective",
  "log_diver",
  "code_arch",
  "customer_liaison",
  "scribe",
  "reviewer",
] as const;

function extractMentions(text: string): Message["mentions"] {
  const found = AGENT_HANDLES.filter((h) =>
    new RegExp(`@${h}\\b`, "i").test(text),
  );
  return found.length ? (found as Message["mentions"]) : undefined;
}
