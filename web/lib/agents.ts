import type { LucideIcon } from "lucide-react";
import {
  Search,
  Waves,
  GitPullRequest,
  Megaphone,
  ClipboardList,
  ShieldCheck,
} from "lucide-react";
import type { AgentId } from "./types";

export interface AgentMeta {
  id: AgentId;
  /** Short display name shown next to messages. */
  name: string;
  /** The partner platform this agent drives. */
  partner: string;
  /** Lucide icon for the agent (no emojis — reads as a real tool). */
  icon: LucideIcon;
  /** Two-letter fallback initials. */
  initials: string;
  /**
   * Tailwind classes for the avatar square (tinted bg + hairline border + icon color).
   * Full literal strings so the Tailwind v4 scanner keeps them — never build dynamically.
   */
  avatar: string;
  /** Tailwind text color for the agent's name (muted, restrained — no indigo/purple). */
  nameColor: string;
}

// 6 specialists, each a Lucide icon on a restrained tinted square. Tones are muted and
// functional, not decorative — a calm dev-tool palette, not a rainbow.
export const AGENTS: Record<AgentId, AgentMeta> = {
  detective: {
    id: "detective",
    name: "Detective",
    partner: "Dynatrace",
    icon: Search,
    initials: "DT",
    avatar: "border border-sky-400/25 bg-sky-400/10 text-sky-300",
    nameColor: "text-sky-300",
  },
  log_diver: {
    id: "log_diver",
    name: "LogDiver",
    partner: "Elastic",
    icon: Waves,
    initials: "LD",
    avatar: "border border-teal-400/25 bg-teal-400/10 text-teal-300",
    nameColor: "text-teal-300",
  },
  code_arch: {
    id: "code_arch",
    name: "CodeArch",
    partner: "GitLab",
    icon: GitPullRequest,
    initials: "CA",
    avatar: "border border-amber-400/25 bg-amber-400/10 text-amber-300",
    nameColor: "text-amber-300",
  },
  customer_liaison: {
    id: "customer_liaison",
    name: "Liaison",
    partner: "Fivetran",
    icon: Megaphone,
    initials: "CL",
    avatar: "border border-blue-400/25 bg-blue-400/10 text-blue-300",
    nameColor: "text-blue-300",
  },
  scribe: {
    id: "scribe",
    name: "Scribe",
    partner: "MongoDB Atlas",
    icon: ClipboardList,
    initials: "SC",
    avatar: "border border-emerald-400/25 bg-emerald-400/10 text-emerald-300",
    nameColor: "text-emerald-300",
  },
  reviewer: {
    id: "reviewer",
    name: "Reviewer",
    partner: "Dynatrace SRG",
    icon: ShieldCheck,
    initials: "RV",
    avatar: "border border-zinc-400/25 bg-zinc-400/10 text-zinc-300",
    nameColor: "text-zinc-300",
  },
};

export const AGENT_IDS = Object.keys(AGENTS) as AgentId[];

export function isAgentId(value: string): value is AgentId {
  return value in AGENTS;
}
