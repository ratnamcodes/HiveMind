"use client";

import { useEventStream } from "@/lib/useEventStream";

/** Mounts the singleton /ws connection. Renders nothing. */
export function EventStream() {
  useEventStream();
  return null;
}
