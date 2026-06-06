/** "2:32 PM" — Slack-style short time. Rendered client-side so locale matches. */
export function formatTime(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
}

/** Whether two timestamps are within `mins` of each other (for message grouping). */
export function within(aIso: string, bIso: string, mins = 5): boolean {
  return Math.abs(new Date(aIso).getTime() - new Date(bIso).getTime()) < mins * 60_000;
}
