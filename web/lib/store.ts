"use client";

// Client state for the war-room: open channel, per-channel message cache,
// optimistic posts, and live events from the /ws stream.
// WS events are applied in batches via applyEvents (see useEventStream).

import { create } from "zustand";
import * as api from "@/lib/api";
import { isAgentId } from "@/lib/agents";
import type {
  Brief,
  Channel,
  DecisionRequest,
  Message,
  MessageLink,
  WarRoomEvent,
} from "@/lib/types";

/** Where the real HiveMind backend lives for human-in-the-loop POSTs (resume/ask). The REST
 *  channels/messages stay on the mock (NEXT_PUBLIC_API_BASE); only these go to the backend. */
const BACKEND_BASE =
  process.env.NEXT_PUBLIC_BACKEND_BASE ||
  (process.env.NEXT_PUBLIC_WS_BASE
    ? process.env.NEXT_PUBLIC_WS_BASE.replace(/^ws/, "http")
    : "http://localhost:8000");
const WS_USER = process.env.NEXT_PUBLIC_WS_USER || "hivemind";

interface WarRoomState {
  channels: Channel[];
  channelsLoaded: boolean;
  messagesByChannel: Record<string, Message[]>;
  /** Channels created live over WS: their messages come from events, not REST. */
  liveChannels: Record<string, true>;
  /** The pinned Incident Commander brief per channel (what / impact / who). */
  briefByChannel: Record<string, Brief>;
  /** The active approval card per channel (the run paused for a human), or null. */
  decisionByChannel: Record<string, DecisionRequest | null>;

  loadChannels: () => Promise<void>;
  loadMessages: (channelId: string) => Promise<void>;
  sendMessage: (channelId: string, text: string) => Promise<void>;
  markChannelRead: (channelId: string) => void;
  applyEvents: (evs: WarRoomEvent[]) => void;
  /** Human clicked a button on an approval card: resume the paused run on the backend. */
  respondToDecision: (
    incidentId: string,
    channelId: string,
    choice: string,
    label?: string,
  ) => Promise<void>;
}

let tempSeq = 0;

function authorFor(agentId: string): Message["author"] {
  if (agentId !== "system" && isAgentId(agentId)) {
    return { type: "agent", agent: agentId };
  }
  return { type: "system" };
}

/** An agent gets one streaming bubble per run (so its status pills and streamed
 *  summary land together); system messages stay distinct per message_id. */
function liveKey(channelId: string, agentId: string, messageId: string): string {
  return agentId === "system"
    ? `live-${channelId}-sys-${messageId}`
    : `live-${channelId}-${agentId}`;
}

function completeLinks(payload: Record<string, unknown>): MessageLink[] {
  const links: MessageLink[] = [];
  if (payload.mr_url) links.push({ label: "Merge request", href: String(payload.mr_url) });
  if (payload.notebook_url)
    links.push({ label: "Dynatrace notebook", href: String(payload.notebook_url) });
  if (payload.arize_trace_url)
    links.push({ label: "Arize trace", href: String(payload.arize_trace_url) });
  return links;
}

// The slice of state an event can touch; reduceEvent is pure.
type EventSlice = Pick<
  WarRoomState,
  "channels" | "messagesByChannel" | "liveChannels" | "briefByChannel" | "decisionByChannel"
>;

function fmtUsd(n: number): string {
  return n >= 1000 ? `$${Math.round(n).toLocaleString()}` : `$${n}`;
}

function upsertMessage(
  s: EventSlice,
  channelId: string,
  key: string,
  make: () => Message,
  update: (m: Message) => Message,
): EventSlice {
  const list = s.messagesByChannel[channelId] ?? [];
  const next = list.some((m) => m.id === key)
    ? list.map((m) => (m.id === key ? update(m) : m))
    : [...list, make()];
  return { ...s, messagesByChannel: { ...s.messagesByChannel, [channelId]: next } };
}

function reduceEvent(s: EventSlice, ev: WarRoomEvent): EventSlice {
  if (ev.type === "channel_created") {
    const ch = ev.channel;
    if (s.channels.some((c) => c.id === ch.id)) {
      return {
        ...s,
        channels: s.channels.map((c) => (c.id === ch.id ? { ...c, ...ch } : c)),
        liveChannels: { ...s.liveChannels, [ch.id]: true },
      };
    }
    return {
      channels: [...s.channels, ch],
      liveChannels: { ...s.liveChannels, [ch.id]: true },
      messagesByChannel: {
        ...s.messagesByChannel,
        [ch.id]: s.messagesByChannel[ch.id] ?? [],
      },
    };
  }

  if (ev.type === "status") {
    const key = liveKey(ev.channel_id, ev.agent_id, "");
    const pill = { state: ev.state, tool: ev.tool };
    return upsertMessage(
      s,
      ev.channel_id,
      key,
      () => ({
        id: key,
        channelId: ev.channel_id,
        author: authorFor(ev.agent_id),
        text: "",
        ts: new Date().toISOString(),
        pill,
      }),
      (m) => ({ ...m, pill }),
    );
  }

  if (ev.type === "token") {
    const key = liveKey(ev.channel_id, ev.agent_id, ev.message_id);
    return upsertMessage(
      s,
      ev.channel_id,
      key,
      () => ({
        id: key,
        channelId: ev.channel_id,
        author: authorFor(ev.agent_id),
        text: ev.text,
        ts: new Date().toISOString(),
      }),
      (m) => ({ ...m, text: m.text + ev.text }),
    );
  }

  if (ev.type === "complete") {
    const payload = ev.payload ?? {};
    const escalated = Boolean(payload.escalated);
    const verdict = escalated ? "escalated" : String(payload.verdict ?? "resolved");
    const ca = payload.customers_affected;
    const text =
      `Incident ${escalated ? "escalated" : "resolved"}. Verdict: ${verdict}.` +
      (ca != null ? ` ${ca} customers affected.` : "");
    const list = s.messagesByChannel[ev.channel_id] ?? [];
    const cleared = list.map((m) =>
      m.pill && m.pill.state !== "done" ? { ...m, pill: { state: "done" as const } } : m,
    );
    const summary: Message = {
      id: ev.message_id,
      channelId: ev.channel_id,
      author: { type: "system" },
      text,
      ts: new Date().toISOString(),
      links: completeLinks(payload),
    };
    return {
      ...s,
      messagesByChannel: {
        ...s.messagesByChannel,
        [ev.channel_id]: [...cleared, summary],
      },
    };
  }

  if (ev.type === "brief") {
    const brief: Brief = {
      headline: ev.headline,
      what: ev.what,
      severity: ev.severity,
      suspected: ev.suspected,
      team: ev.team,
    };
    return { ...s, briefByChannel: { ...s.briefByChannel, [ev.channel_id]: brief } };
  }

  if (ev.type === "impact") {
    const prev = s.briefByChannel[ev.channel_id];
    if (!prev) return s;
    const parts: string[] = [];
    if (ev.customers_affected != null) parts.push(`${ev.customers_affected} customers`);
    if (ev.revenue_at_risk_usd != null) parts.push(`${fmtUsd(ev.revenue_at_risk_usd)}/mo at risk`);
    if (ev.segments?.length) parts.push(ev.segments.join(" · "));
    const next: Brief = {
      ...prev,
      impact: parts.join(" · ") || prev.impact,
      customersAffected: ev.customers_affected,
      revenueAtRisk: ev.revenue_at_risk_usd,
      segments: ev.segments,
      actionsTaken: ev.actions_taken,
    };
    return { ...s, briefByChannel: { ...s.briefByChannel, [ev.channel_id]: next } };
  }

  if (ev.type === "decision_request") {
    const { type: _t, channel_id, ...req } = ev;
    return {
      ...s,
      decisionByChannel: { ...s.decisionByChannel, [channel_id]: req as DecisionRequest },
    };
  }

  if (ev.type === "decision_made") {
    const audit: Message = {
      id: `decided-${ev.decision_id}`,
      channelId: ev.channel_id,
      author: { type: "system" },
      text: `Human decision: ${ev.choice}${ev.detail ? `. ${ev.detail}` : ""}`,
      ts: new Date().toISOString(),
    };
    const list = s.messagesByChannel[ev.channel_id] ?? [];
    const next = list.some((m) => m.id === audit.id) ? list : [...list, audit];
    return {
      ...s,
      decisionByChannel: { ...s.decisionByChannel, [ev.channel_id]: null },
      messagesByChannel: { ...s.messagesByChannel, [ev.channel_id]: next },
    };
  }

  if (ev.type === "reasoning") {
    // One muted "thinking aloud" line per agent (replaced if it re-narrates on a revise).
    const key = `reason-${ev.channel_id}-${ev.agent_id}`;
    return upsertMessage(
      s,
      ev.channel_id,
      key,
      () => ({
        id: key,
        channelId: ev.channel_id,
        author: authorFor(ev.agent_id),
        text: ev.text,
        ts: new Date().toISOString(),
        reasoning: true,
      }),
      (m) => ({ ...m, text: ev.text }),
    );
  }

  return s;
}

export const useWarRoom = create<WarRoomState>((set, get) => ({
  channels: [],
  channelsLoaded: false,
  messagesByChannel: {},
  liveChannels: {},
  briefByChannel: {},
  decisionByChannel: {},

  async loadChannels() {
    if (get().channelsLoaded) return;
    const channels = await api.listChannels();
    set((s) => ({
      // Keep any channels that already arrived live over WS.
      channels: [...channels, ...s.channels.filter((c) => s.liveChannels[c.id])],
      channelsLoaded: true,
    }));
  },

  async loadMessages(channelId) {
    // Live (WS-created) channels are fed by the event stream; don't overwrite
    // their streamed messages with an empty REST result.
    if (get().liveChannels[channelId]) {
      get().markChannelRead(channelId);
      return;
    }
    const messages = await api.getMessages(channelId);
    set((s) => ({
      messagesByChannel: { ...s.messagesByChannel, [channelId]: messages },
    }));
    get().markChannelRead(channelId);
  },

  async sendMessage(channelId, text) {
    const trimmed = text.trim();
    if (!trimmed) return;

    // A plain reply while a decision is pending is treated as the decision.
    const pending = get().decisionByChannel[channelId];
    if (pending && pending.incident_id) {
      const t = trimmed.toLowerCase();
      const choice =
        /escalat|on.?call|page .*human|human on|get .*human/.test(t)
          ? "escalate"
          : /\b(approve|ship it|ship the|ship\b|merge|go ahead|lgtm|do it|send it|proceed|sounds good|yes\b|yep|yup|👍)/.test(t)
            ? "approve"
            : /\b(request change|need.*change|revis|hold off|not yet|don'?t|do not|reject|rework|wait\b|no\b)/.test(t)
              ? "changes"
              : null;
      if (choice) {
        await get().respondToDecision(pending.incident_id, channelId, choice, trimmed);
        return;
      }
    }

    const tempId = `temp-${++tempSeq}`;
    const optimistic: Message = {
      id: tempId,
      channelId,
      author: { type: "user", name: "you" },
      text: trimmed,
      ts: new Date().toISOString(),
    };
    set((s) => ({
      messagesByChannel: {
        ...s.messagesByChannel,
        [channelId]: [...(s.messagesByChannel[channelId] ?? []), optimistic],
      },
    }));

    // Ask the crew to reply. Routes to the @mentioned agent (else Detective); the reply streams
    // back into this channel over /ws.
    const mention = trimmed.match(/@([a-z_]+)/);
    void fetch(`${BACKEND_BASE}/api/chat?user=${encodeURIComponent(WS_USER)}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ channel_id: channelId, text: trimmed, agent_id: mention?.[1] ?? "" }),
    }).catch(() => {});

    if (get().liveChannels[channelId]) return; // live channels have no REST store

    try {
      const saved = await api.postMessage(channelId, trimmed);
      set((s) => ({
        messagesByChannel: {
          ...s.messagesByChannel,
          [channelId]: (s.messagesByChannel[channelId] ?? []).map((m) =>
            m.id === tempId ? saved : m,
          ),
        },
      }));
    } catch {
      set((s) => ({
        messagesByChannel: {
          ...s.messagesByChannel,
          [channelId]: (s.messagesByChannel[channelId] ?? []).filter(
            (m) => m.id !== tempId,
          ),
        },
      }));
    }
  },

  markChannelRead(channelId) {
    set((s) => ({
      channels: s.channels.map((c: Channel) =>
        c.id === channelId ? { ...c, unread: 0, isNew: false } : c,
      ),
    }));
  },

  applyEvents(evs) {
    if (!evs.length) return;
    set((s) => {
      let slice: EventSlice = {
        channels: s.channels,
        messagesByChannel: s.messagesByChannel,
        liveChannels: s.liveChannels,
        briefByChannel: s.briefByChannel,
        decisionByChannel: s.decisionByChannel,
      };
      for (const ev of evs) slice = reduceEvent(slice, ev);
      return slice;
    });
  },

  async respondToDecision(incidentId, channelId, choice, label) {
    // Optimistically clear the card + post a "you" message; the backend's decision_made/complete
    // events confirm. The run resumes from its Redis checkpoint.
    set((s) => ({
      decisionByChannel: { ...s.decisionByChannel, [channelId]: null },
      messagesByChannel: {
        ...s.messagesByChannel,
        [channelId]: [
          ...(s.messagesByChannel[channelId] ?? []),
          {
            id: `you-${++tempSeq}`,
            channelId,
            author: { type: "user", name: "you" },
            text: `${label ?? choice}`,
            ts: new Date().toISOString(),
          } as Message,
        ],
      },
    }));
    try {
      await fetch(`${BACKEND_BASE}/api/incident/${encodeURIComponent(incidentId)}/resume`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ choice }),
      });
    } catch {
      /* the run stays paused; the card can be retried */
    }
  },
}));
