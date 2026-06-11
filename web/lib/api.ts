// Typed REST client for the war-room. Hits the local mock backend (Next route
// handlers under /api); set NEXT_PUBLIC_API_BASE to point at the real backend.

import type { Channel, Message, Thread } from "@/lib/types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "";

async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    cache: "no-store",
    ...init,
  });
  if (!res.ok) {
    throw new Error(`${init?.method ?? "GET"} ${path} → ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export function listChannels(): Promise<Channel[]> {
  return fetchJson<Channel[]>("/api/channels");
}

export function getMessages(channelId: string): Promise<Message[]> {
  return fetchJson<Message[]>(
    `/api/channels/${encodeURIComponent(channelId)}/messages`,
  );
}

export function postMessage(channelId: string, text: string): Promise<Message> {
  return fetchJson<Message>(
    `/api/channels/${encodeURIComponent(channelId)}/messages`,
    { method: "POST", body: JSON.stringify({ text }) },
  );
}

export function getThread(threadId: string): Promise<Thread> {
  return fetchJson<Thread>(`/api/threads/${encodeURIComponent(threadId)}`);
}
