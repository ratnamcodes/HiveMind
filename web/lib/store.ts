"use client";

// Client state for the war-room: which channel is open, a per-channel message
// cache, optimistic posts, AND live events from the /ws stream (T17): streaming
// tokens, agent status pills, and channels that materialize from a Dynatrace alert.
//
// WS events are applied in BATCHES (applyEvents) — the hook coalesces a burst into
// one set() per animation frame, so a flood of tokens/status is one re-render, not
// hundreds. That keeps the UI (and client-side navigation) responsive under load.

import { create } from "zustand";
import * as api from "@/lib/api";
import { isAgentId } from "@/lib/agents";
import type { Channel, Message, MessageLink, WarRoomEvent } from "@/lib/types";

interface WarRoomState {
  channels: Channel[];
  channelsLoaded: boolean;
  messagesByChannel: Record<string, Message[]>;
  loadingMessages: Record<string, boolean>;
  /** Channels created live over WS — their messages come from events, not REST. */
  liveChannels: Record<string, true>;

  loadChannels: () => Promise<void>;
  loadMessages: (channelId: string) => Promise<void>;
  sendMessage: (channelId: string, text: string) => Promise<void>;
  markChannelRead: (channelId: string) => void;
  applyEvents: (evs: WarRoomEvent[]) => void;
  applyEvent: (ev: WarRoomEvent) => void;
}

let tempSeq = 0;

function authorFor(agentId: string): Message["author"] {
  if (agentId !== "system" && isAgentId(agentId)) {
    return { type: "agent", agent: agentId };
  }
  return { type: "system" };
}

/** An agent gets ONE streaming bubble per run (so its status pills and streamed
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

// The slice of state an event can touch. reduceEvent is pure so a batch folds into
// one new state object → one re-render.
type EventSlice = Pick<
  WarRoomState,
  "channels" | "messagesByChannel" | "liveChannels"
>;

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
      `✅ Incident ${escalated ? "escalated" : "resolved"} — verdict: ${verdict}.` +
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

  return s;
}

export const useWarRoom = create<WarRoomState>((set, get) => ({
  channels: [],
  channelsLoaded: false,
  messagesByChannel: {},
  loadingMessages: {},
  liveChannels: {},

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
    // Live (WS-created) channels are fed by the event stream — never overwrite their
    // streamed messages with an empty REST result.
    if (get().liveChannels[channelId]) {
      get().markChannelRead(channelId);
      return;
    }
    set((s) => ({ loadingMessages: { ...s.loadingMessages, [channelId]: true } }));
    try {
      const messages = await api.getMessages(channelId);
      set((s) => ({
        messagesByChannel: { ...s.messagesByChannel, [channelId]: messages },
      }));
      get().markChannelRead(channelId);
    } finally {
      set((s) => ({
        loadingMessages: { ...s.loadingMessages, [channelId]: false },
      }));
    }
  },

  async sendMessage(channelId, text) {
    const trimmed = text.trim();
    if (!trimmed) return;

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
      };
      for (const ev of evs) slice = reduceEvent(slice, ev);
      return slice;
    });
  },

  applyEvent(ev) {
    get().applyEvents([ev]);
  },
}));
