import type { AgentId } from "./types";

export interface AgentMeta {
  id: AgentId;
  /** Short display name shown next to messages. */
  name: string;
  /** The partner platform this agent drives. */
  partner: string;
  emoji: string;
  /** Two-letter fallback initials. */
  initials: string;
  /**
   * Tailwind classes for the avatar (background + ring). Written as full literal
   * strings so the Tailwind v4 scanner includes them — never build these
   * dynamically or they'll be purged.
   */
  avatar: string;
  /** Tailwind text color for the agent's name. */
  nameColor: string;
}

// 6 agents → 6 partner colors, exactly as the spec maps them:
// emerald=mongo, teal=elastic, indigo=dynatrace, orange=gitlab, blue=fivetran, purple=arize.
export const AGENTS: Record<AgentId, AgentMeta> = {
  detective: {
    id: "detective",
    name: "Detective",
    partner: "Dynatrace",
    emoji: "🕵️",
    initials: "DT",
    avatar: "bg-indigo-500 ring-indigo-400/40",
    nameColor: "text-indigo-300",
  },
  log_diver: {
    id: "log_diver",
    name: "LogDiver",
    partner: "Elastic",
    emoji: "🌊",
    initials: "LD",
    avatar: "bg-teal-500 ring-teal-400/40",
    nameColor: "text-teal-300",
  },
  code_arch: {
    id: "code_arch",
    name: "CodeArch",
    partner: "GitLab",
    emoji: "🔧",
    initials: "CA",
    avatar: "bg-orange-500 ring-orange-400/40",
    nameColor: "text-orange-300",
  },
  customer_liaison: {
    id: "customer_liaison",
    name: "Liaison",
    partner: "Fivetran",
    emoji: "📣",
    initials: "CL",
    avatar: "bg-blue-500 ring-blue-400/40",
    nameColor: "text-blue-300",
  },
  scribe: {
    id: "scribe",
    name: "Scribe",
    partner: "MongoDB Atlas",
    emoji: "📝",
    initials: "SC",
    avatar: "bg-emerald-500 ring-emerald-400/40",
    nameColor: "text-emerald-300",
  },
  reviewer: {
    id: "reviewer",
    name: "Reviewer",
    partner: "Arize",
    emoji: "⚖️",
    initials: "RV",
    avatar: "bg-purple-500 ring-purple-400/40",
    nameColor: "text-purple-300",
  },
};

export const AGENT_IDS = Object.keys(AGENTS) as AgentId[];

export function isAgentId(value: string): value is AgentId {
  return value in AGENTS;
}
