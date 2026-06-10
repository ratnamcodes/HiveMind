"use client";

// Singleton WebSocket to the backend's /ws, with exponential reconnect. Incoming
// events are BUFFERED and flushed to the store once per animation frame, so a burst
// of tokens/status collapses into a single re-render (keeps the UI + navigation
// responsive under load). One connection per tab.

import { useEffect } from "react";
import { useWarRoom } from "@/lib/store";
import type { WarRoomEvent } from "@/lib/types";

let socket: WebSocket | null = null;
let started = false;
let reconnectDelay = 500;

const buffer: WarRoomEvent[] = [];
let flushScheduled = false;

function scheduleFlush(applyEvents: (evs: WarRoomEvent[]) => void): void {
  if (flushScheduled) return;
  flushScheduled = true;
  // setTimeout (not requestAnimationFrame): a ~50ms window still collapses a burst into one
  // render, but it keeps firing when the tab is backgrounded — rAF pauses there, which would
  // freeze the war room until you switched back to it.
  setTimeout(() => {
    flushScheduled = false;
    const batch = buffer.splice(0, buffer.length);
    if (batch.length) applyEvents(batch);
  }, 50);
}

function wsUrl(): string {
  const base = process.env.NEXT_PUBLIC_WS_BASE || "ws://localhost:8000";
  const user = process.env.NEXT_PUBLIC_WS_USER || "hivemind";
  return `${base}/ws?user=${encodeURIComponent(user)}`;
}

function scheduleReconnect(applyEvents: (evs: WarRoomEvent[]) => void): void {
  const delay = reconnectDelay;
  reconnectDelay = Math.min(reconnectDelay * 2, 10_000);
  setTimeout(() => connect(applyEvents), delay);
}

function connect(applyEvents: (evs: WarRoomEvent[]) => void): void {
  try {
    socket = new WebSocket(wsUrl());
  } catch {
    scheduleReconnect(applyEvents);
    return;
  }
  socket.onopen = () => {
    reconnectDelay = 500;
  };
  socket.onmessage = (e) => {
    try {
      buffer.push(JSON.parse(e.data) as WarRoomEvent);
      scheduleFlush(applyEvents);
    } catch {
      /* ignore malformed frames */
    }
  };
  socket.onclose = () => {
    socket = null;
    scheduleReconnect(applyEvents);
  };
  socket.onerror = () => {
    try {
      socket?.close();
    } catch {
      /* noop */
    }
  };
}

/** Open the singleton stream. Mount once via <EventStream/>. */
export function useEventStream(): void {
  const applyEvents = useWarRoom((s) => s.applyEvents);
  useEffect(() => {
    if (started) return;
    started = true;
    connect(applyEvents);
    // Intentionally not closed on unmount — one connection lives for the tab session.
  }, [applyEvents]);
}
