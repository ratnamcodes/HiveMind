// In-memory mock backend for the war-room. Lives server-side (imported only by
// the route handlers under app/api), so the client always talks REST and never
// imports this directly. Swapping in the real backend = point lib/api.ts at it.
//
// The incident below is the SAME story the real HiveMind orchestrator produces:
// payment-service retry timeout too low after a deploy → CodeArch opens an MR →
// 7 customers impacted → Reviewer approves. Keeps the demo honest end to end.

import type { Channel, Message, Thread } from "@/lib/types";

const NOW = Date.now();
/** Build an ISO timestamp `mins` minutes before server start. */
const ago = (mins: number): string => new Date(NOW - mins * 60_000).toISOString();

let _seq = 1000;
const nextId = (prefix: string): string => `${prefix}-${++_seq}`;

// --- channels --------------------------------------------------------------
// A clean team workspace: a control-plane channel + ordinary team channels. There are NO
// pre-seeded incidents — the only incident channel that ever appears is a REAL one, materialized
// live over /ws when HiveMind is paged. (Keeps the demo honest: nothing is staged in the sidebar.)
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

// --- messages, keyed by channel -------------------------------------------
const THREAD_ID = "thr-rootcause";

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
  "inc-checkout-latency": [
    {
      id: "m-inc-1",
      channelId: "inc-checkout-latency",
      author: { type: "system" },
      text: "Incident opened — Checkout p99 latency doubled to 1.8s starting 14:32; error rate normal. Suspected trigger: the 14:05 payment-service deploy.",
      ts: ago(32),
    },
    {
      id: "m-inc-2",
      channelId: "inc-checkout-latency",
      author: { type: "user", name: "you" },
      text: "@detective can you take this one?",
      ts: ago(31),
      mentions: ["detective"],
    },
    {
      id: "m-inc-3",
      channelId: "inc-checkout-latency",
      author: { type: "agent", agent: "detective" },
      text: "On it. Pulling Dynatrace logs for payment-service around the 14:05 deploy window.",
      ts: ago(31),
      pill: { state: "tool_call", tool: "execute_dql" },
    },
    {
      id: "m-inc-4",
      channelId: "inc-checkout-latency",
      author: { type: "agent", agent: "detective" },
      text: "Root cause: the 14:05 deploy set retry.timeout_seconds=1 in payment-service — too aggressive, so valid calls abort under load. p99 went 240ms → 520ms right after rollout. Confidence 0.82.",
      ts: ago(29),
      pill: { state: "done" },
      threadId: THREAD_ID,
      replyCount: 2,
      links: [
        {
          label: "Dynatrace notebook",
          href: "https://jyl55158.apps.dynatrace.com/ui/notebooks/demo",
        },
      ],
    },
    {
      id: "m-inc-5",
      channelId: "inc-checkout-latency",
      author: { type: "agent", agent: "log_diver" },
      text: "Elastic corroborates: 1,204 ERROR logs post-deploy — \"payment call aborted: deadline exceeded\". Spike begins 14:06, one minute after rollout.",
      ts: ago(28),
      pill: { state: "done" },
    },
    {
      id: "m-inc-6",
      channelId: "inc-checkout-latency",
      author: { type: "agent", agent: "code_arch" },
      text: "Drafted the minimal fix: payment-service/config.yaml retry.timeout_seconds 1 → 5. Opened MR !1 under @hivemind-bot off main.",
      ts: ago(26),
      pill: { state: "tool_call", tool: "create_merge_request" },
      links: [
        {
          label: "MR !1 · fix(payment-service): INC-a104854b",
          href: "https://gitlab.com/ratnamsingh1201-group/hivemind-target/-/merge_requests/1",
        },
      ],
    },
    {
      id: "m-inc-7",
      channelId: "inc-checkout-latency",
      author: { type: "agent", agent: "customer_liaison" },
      text: "Customer impact (Fivetran → BigQuery): 7 customers hit checkout failures in the window. Top by volume: Acme, Globex, Initech.",
      ts: ago(25),
      pill: { state: "done" },
    },
    {
      id: "m-inc-8",
      channelId: "inc-checkout-latency",
      author: { type: "agent", agent: "scribe" },
      text: "Recorded incident INC-a104854b to Atlas with the full timeline, participants, and the MR link.",
      ts: ago(24),
      pill: { state: "done" },
      links: [{ label: "incidents/INC-a104854b", href: "#" }],
    },
    {
      id: "m-inc-9",
      channelId: "inc-checkout-latency",
      author: { type: "agent", agent: "reviewer" },
      text: "Verdict: approve — the hypothesis is grounded in Dynatrace logs and the MR addresses the root cause directly. Full trace attached.",
      ts: ago(23),
      pill: { state: "done" },
      links: [
        {
          label: "Arize trace",
          href: "http://localhost:6006/projects/hivemind/traces/de4c0a4f",
        },
      ],
    },
  ],
  "inc-cache-stampede": [
    {
      id: "m-cs-1",
      channelId: "inc-cache-stampede",
      author: { type: "system" },
      text: "Incident resolved — cache stampede on product-service mitigated.",
      ts: ago(320),
    },
    {
      id: "m-cs-2",
      channelId: "inc-cache-stampede",
      author: { type: "agent", agent: "code_arch" },
      text: "MR !4 merged: added request coalescing around the hot product lookup. p99 back to baseline.",
      ts: ago(315),
      pill: { state: "done" },
    },
  ],
};

// --- threads ---------------------------------------------------------------
const threads: Record<string, Thread> = {
  [THREAD_ID]: {
    id: THREAD_ID,
    channelId: "inc-checkout-latency",
    rootMessageId: "m-inc-4",
    messages: [
      {
        id: "m-thr-1",
        channelId: "inc-checkout-latency",
        author: { type: "user", name: "you" },
        text: "Nice. Is the timeout the only change in that deploy?",
        ts: ago(28),
      },
      {
        id: "m-thr-2",
        channelId: "inc-checkout-latency",
        author: { type: "agent", agent: "detective" },
        text: "Yes — the deploy diff is a single-line config change, nothing else touched. Reverting the timeout (or merging CodeArch's MR) fully addresses it.",
        ts: ago(27),
        pill: { state: "done" },
      },
    ],
  },
};

// --- accessors (the "backend" surface) -------------------------------------
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
