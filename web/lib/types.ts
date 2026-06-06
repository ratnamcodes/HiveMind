// Core domain types for the HiveMind war-room UI.
// The shapes here mirror what the real backend will eventually return (see the
// orchestrator's incident output: incident_id, mr_url, notebook_url,
// customers_affected, verdict, arize_trace_url) so swapping mocks for the live
// REST API is a base-URL change, not a refactor.

export type AgentId =
  | "detective"
  | "log_diver"
  | "code_arch"
  | "customer_liaison"
  | "scribe"
  | "reviewer";

export type Severity = "sev1" | "sev2" | "sev3";

export type ChannelKind = "ops" | "incident";

/** State of an agent's work, shown as a small pill to the right of its message. */
export type PillState = "thinking" | "tool_call" | "done";

export interface StatusPill {
  state: PillState;
  /** Tool the agent is invoking, when state === "tool_call" (e.g. "execute_dql"). */
  tool?: string;
}

export interface Channel {
  id: string;
  /** Display name without the leading "#", e.g. "ops" or "inc-checkout-latency". */
  name: string;
  kind: ChannelKind;
  /** Incident channels carry a severity that drives the sidebar color stripe. */
  severity?: Severity;
  /** Unread message count → sidebar unread dot. */
  unread: number;
  /** Freshly-opened incident channel → triggers the sidebar pulse animation. */
  isNew?: boolean;
  /** Short channel topic shown in the header. */
  topic?: string;
  /** Resolved incidents render dimmed with a check. */
  resolved?: boolean;
}

export type Author =
  | { type: "agent"; agent: AgentId }
  | { type: "user"; name: string }
  | { type: "system" };

export interface MessageLink {
  label: string;
  href: string;
}

export interface Message {
  id: string;
  channelId: string;
  author: Author;
  text: string;
  /** ISO-8601 timestamp. */
  ts: string;
  /** Present on agent messages to show thinking / tool_call / done. */
  pill?: StatusPill;
  /** Agents @-mentioned in the body, for highlight. */
  mentions?: AgentId[];
  /** If this message anchors a thread. */
  threadId?: string;
  replyCount?: number;
  /** Cross-partner observability links (Arize trace, Dynatrace notebook, MR, …). */
  links?: MessageLink[];
}

export interface Thread {
  id: string;
  channelId: string;
  rootMessageId: string;
  messages: Message[];
}

/** Live events pushed over the /ws WebSocket (must match hivemind/events.py). */
export type WarRoomEvent =
  | { type: "channel_created"; channel: Channel }
  | {
      type: "status";
      channel_id: string;
      agent_id: string;
      state: PillState;
      tool?: string;
    }
  | {
      type: "token";
      channel_id: string;
      agent_id: string;
      message_id: string;
      text: string;
    }
  | {
      type: "complete";
      channel_id: string;
      message_id: string;
      payload: Record<string, unknown>;
    };
