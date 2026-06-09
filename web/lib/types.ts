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
export type PillState = "thinking" | "tool_call" | "done" | "awaiting_human";

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
  /** A one-line "why I'm doing this" the agent narrates before its work (rendered muted/italic). */
  reasoning?: boolean;
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

/** The pinned Incident Commander brief — the 5-second "what / impact / who" a newcomer reads. */
export interface Brief {
  headline: string;
  what: string;
  severity: Severity;
  suspected?: string;
  team?: string[];
  /** Updated once Liaison reports: a formatted business-impact line. */
  impact?: string;
  customersAffected?: number;
  revenueAtRisk?: number;
  segments?: string[];
  actionsTaken?: string[];
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
    }
  | {
      type: "brief";
      channel_id: string;
      headline: string;
      what: string;
      severity: Severity;
      suspected?: string;
      team?: string[];
    }
  | {
      type: "reasoning";
      channel_id: string;
      agent_id: string;
      text: string;
    }
  | {
      type: "impact";
      channel_id: string;
      customers_affected?: number;
      revenue_at_risk_usd?: number;
      segments?: string[];
      actions_taken?: string[];
      summary?: string;
    }
  | ({ type: "decision_request"; channel_id: string } & DecisionRequest)
  | {
      type: "decision_made";
      channel_id: string;
      decision_id: string;
      choice: string;
      detail?: string;
    };

/** An approval card: the run paused and needs a human to choose. */
export interface DecisionRequest {
  decision_id: string;
  incident_id: string;
  kind: string;
  title: string;
  prompt?: string;
  mr_url?: string;
  suspect_files?: string[];
  impact?: string;
  actions_taken?: string[];
  options: { id: string; label: string; style?: string }[];
}
