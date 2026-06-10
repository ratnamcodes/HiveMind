"use client";

import { useEffect, useRef, useState } from "react";
import { useInView } from "motion/react";
import {
  AlertTriangle,
  CheckCircle2,
  GitMerge,
  Hash,
  Hexagon,
  ShieldCheck,
  UserRound,
} from "lucide-react";
import { AGENTS, AGENT_IDS } from "@/lib/agents";
import { cn } from "@/lib/utils";

// A read-only recreation of the real war room playing one incident from start to finish. It begins
// when it scrolls into view, plays through exactly ONCE, and then rests on the resolved state — no
// looping. A Replay control lets you watch it again. Nothing calls the backend.

type AgentKey = keyof typeof AGENTS;

type Beat =
  | { t: "agent"; agent: AgentKey; text: string; chip?: string }
  | { t: "approve" }
  | { t: "recovery" }
  | { t: "resolved" };

const SCRIPT: Beat[] = [
  { t: "agent", agent: "detective", text: "Davis opened problem P-2506-4471 on checkout. Grail shows 1,271 error events and a peak latency of 1,320ms. The payment-service deploy added a 1,200ms delay." },
  { t: "agent", agent: "log_diver", text: "Confirmed in the logs: the slowdown starts right at the 14:09 payment-service release. Nothing else changed." },
  { t: "agent", agent: "code_arch", text: "Opened a one-line fix: set downstream_delay_ms back to 0 in payment-service.", chip: "MR #52" },
  { t: "agent", agent: "customer_liaison", text: "7 paying customers are hit. About $18,397 a month is at risk across Enterprise, Pro and Free." },
  { t: "agent", agent: "reviewer", text: "I reviewed the whole investigation. The fix is safe and it is one line. My verdict: approve." },
  { t: "approve" },
  { t: "recovery" },
  { t: "resolved" },
];

// Dwell time AFTER a beat appears, before the next one is revealed.
const DUR: Record<Beat["t"], number> = { agent: 1350, approve: 1300, recovery: 1900, resolved: 2200 };
const START_DELAY = 650;

export function LandingWarRoom() {
  const rootRef = useRef<HTMLDivElement>(null);
  const feedRef = useRef<HTMLDivElement>(null);
  const inView = useInView(rootRef, { once: true, margin: "-120px 0px -120px 0px" });

  // `n` = number of beats revealed (0 = only the incident brief).
  const [n, setN] = useState(0);
  const done = n >= SCRIPT.length;

  // Advance one beat at a time, once in view, then stop at the end.
  useEffect(() => {
    if (!inView || done) return;
    const justShown = n === 0 ? null : SCRIPT[n - 1];
    const wait = justShown ? DUR[justShown.t] : START_DELAY;
    const id = setTimeout(() => setN((x) => Math.min(x + 1, SCRIPT.length)), wait);
    return () => clearTimeout(id);
  }, [inView, n, done]);

  // Keep the newest line in view as the feed fills.
  useEffect(() => {
    const el = feedRef.current;
    if (el) el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
  }, [n]);

  const shown = SCRIPT.slice(0, n);
  const next = SCRIPT[n];
  const mrShown = shown.some((b) => b.t === "agent" && b.chip);
  const recovered = shown.some((b) => b.t === "recovery" || b.t === "resolved");

  return (
    <div
      ref={rootRef}
      className="overflow-hidden rounded-xl border border-white/10 bg-[#0b0d10] text-zinc-100 shadow-2xl shadow-black/30 ring-1 ring-black/5"
    >
      {/* window chrome */}
      <div className="flex items-center gap-2 border-b border-white/10 bg-white/[0.03] px-4 py-2.5">
        <div className="flex gap-1.5">
          <span className="h-2.5 w-2.5 rounded-full bg-red-400/70" />
          <span className="h-2.5 w-2.5 rounded-full bg-amber-400/70" />
          <span className="h-2.5 w-2.5 rounded-full bg-emerald-400/70" />
        </div>
        <span className="ml-2 flex items-center gap-1.5 whitespace-nowrap text-xs font-medium text-zinc-200">
          <Hexagon className="h-3.5 w-3.5 text-amber-400" strokeWidth={2.5} fill="currentColor" /> HiveMind War Room
        </span>
        {done ? (
          <button
            onClick={() => setN(0)}
            className="ml-auto inline-flex items-center gap-1.5 rounded-full border border-white/10 bg-white/[0.04] px-2.5 py-0.5 text-[11px] font-medium text-zinc-300 transition-colors hover:bg-white/[0.08] hover:text-white"
          >
            <ReplayIcon /> Replay
          </button>
        ) : (
          <span className="ml-auto inline-flex items-center gap-1.5 rounded-full border border-white/10 bg-white/[0.03] px-2 py-0.5 text-[11px] text-zinc-400">
            <Live /> Replaying a real incident
          </span>
        )}
      </div>

      <div className="flex h-[520px] sm:h-[600px]">
        {/* sidebar */}
        <aside className="hidden w-48 shrink-0 flex-col border-r border-white/10 bg-white/[0.02] p-3 md:flex">
          <SideGroup title="Pinned">
            {["ops", "deploys", "general"].map((c) => (
              <SideChannel key={c} name={c} />
            ))}
          </SideGroup>
          <SideGroup title="Incidents">
            <SideChannel name="inc-checkout" active sev />
          </SideGroup>
          <div className="mt-auto flex items-center gap-2 pt-3 text-[11px] text-zinc-500">
            <span className="flex h-6 w-6 items-center justify-center rounded-full border border-white/10 bg-white/[0.03] text-[10px]">RS</span>
            6 agents online
          </div>
        </aside>

        {/* center: channel */}
        <div className="flex min-w-0 flex-1 flex-col">
          <div className="flex h-11 shrink-0 items-center gap-2 border-b border-white/10 px-4">
            <Hash className="h-3.5 w-3.5 shrink-0 text-zinc-500" />
            <span className="shrink-0 text-sm font-semibold whitespace-nowrap">inc-checkout</span>
            <span className="shrink-0 rounded-full border border-red-500/40 bg-red-500/10 px-1.5 py-0.5 text-[10px] font-semibold text-red-300">SEV1</span>
            <span className="hidden truncate text-xs text-zinc-500 sm:inline">checkout latency past the 300ms goal</span>
          </div>

          <div ref={feedRef} className="flex flex-1 flex-col gap-3 overflow-y-auto px-4 py-3">
            {/* brief */}
            <div className="shrink-0 rounded-lg border border-white/10 bg-white/[0.03] px-3.5 py-2.5">
              <div className="flex items-center gap-2">
                <AlertTriangle className="h-3.5 w-3.5 text-red-300" strokeWidth={2} />
                <span className="text-[11px] font-semibold uppercase tracking-wide text-zinc-400">Incident brief</span>
              </div>
              <p className="mt-1.5 text-[13px] leading-relaxed text-zinc-200">
                Checkout latency jumped to ~1,320ms, past the 300ms goal, because payment-service got slow.
              </p>
            </div>
            {shown.map((b, i) => (
              <Line key={i} beat={b} />
            ))}
            {!done && <LiveBar next={next} />}
          </div>
        </div>

        {/* right rail: context that fills in as the run proceeds */}
        <aside className="hidden w-64 shrink-0 flex-col gap-px overflow-hidden border-l border-white/10 bg-white/[0.015] lg:flex">
          <RailBlock title="Impact">
            <div className="text-lg font-semibold text-zinc-100">$18,397<span className="text-sm font-normal text-zinc-500">/mo at risk</span></div>
            <div className="mt-0.5 text-xs text-zinc-500">7 customers · Enterprise, Pro, Free</div>
          </RailBlock>
          <RailBlock title="On the case">
            <div className="flex flex-wrap gap-1.5">
              {AGENT_IDS.map((id) => {
                const a = AGENTS[id];
                const I = a.icon;
                return (
                  <span key={id} title={a.name} className={cn("flex h-7 w-7 items-center justify-center rounded-md", a.avatar)}>
                    <I className="h-3.5 w-3.5" strokeWidth={2} />
                  </span>
                );
              })}
            </div>
          </RailBlock>
          <RailBlock title="The fix">
            {mrShown ? (
              <span className="inline-flex items-center gap-1.5 rounded-md border border-amber-400/30 bg-amber-400/10 px-2 py-1 font-mono text-[11px] text-amber-300">
                <GitMerge className="h-3 w-3" /> MR #52 · {recovered ? "merged" : "open"}
              </span>
            ) : (
              <span className="text-xs text-zinc-500">drafting…</span>
            )}
          </RailBlock>
          <RailBlock title="Recovery">
            {recovered ? (
              <span className="inline-flex items-center gap-1.5 text-xs font-medium text-emerald-300">
                <ShieldCheck className="h-3.5 w-3.5" /> SRG check: PASS
              </span>
            ) : (
              <span className="text-xs text-zinc-500">waiting for the fix…</span>
            )}
          </RailBlock>
        </aside>
      </div>
    </div>
  );
}

function Live() {
  return (
    <span className="relative flex h-1.5 w-1.5">
      <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400/70" />
      <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-emerald-400" />
    </span>
  );
}

function ReplayIcon() {
  return (
    <svg viewBox="0 0 24 24" className="size-3" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <path d="M3 12a9 9 0 1 0 3-6.7L3 8" />
      <path d="M3 3v5h5" />
    </svg>
  );
}

function SideGroup({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="mb-3">
      <div className="px-1 pb-1 text-[10px] font-semibold uppercase tracking-wide text-zinc-500">{title}</div>
      <div className="space-y-0.5">{children}</div>
    </div>
  );
}

function SideChannel({ name, active, sev }: { name: string; active?: boolean; sev?: boolean }) {
  return (
    <div className={cn("flex cursor-default items-center gap-1.5 rounded-md px-2 py-1 text-[13px]", active ? "bg-white/[0.06] text-zinc-100" : "text-zinc-500")}>
      {sev && <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-red-400" />}
      <Hash className="h-3 w-3 shrink-0 opacity-60" />
      <span className="truncate">{name}</span>
    </div>
  );
}

function RailBlock({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="bg-white/[0.02] px-4 py-3">
      <div className="text-[10px] font-semibold uppercase tracking-wide text-zinc-500">{title}</div>
      <div className="mt-1.5">{children}</div>
    </div>
  );
}

function Line({ beat }: { beat: Beat }) {
  if (beat.t === "agent") {
    const a = AGENTS[beat.agent];
    const Icon = a.icon;
    return (
      <div className="hm-reveal flex shrink-0 gap-2.5">
        <span className={cn("flex h-7 w-7 shrink-0 items-center justify-center rounded-md", a.avatar)}>
          <Icon className="h-3.5 w-3.5" strokeWidth={2} />
        </span>
        <div className="min-w-0">
          <span className={cn("text-[13px] font-semibold", a.nameColor)}>{a.name}</span>
          <p className="text-[13px] leading-snug text-zinc-300">
            {beat.text}
            {beat.chip && (
              <span className="ml-1.5 inline-flex items-center gap-1 rounded-md border border-amber-400/30 bg-amber-400/10 px-1.5 py-0.5 align-middle font-mono text-[11px] text-amber-300">
                <GitMerge className="h-3 w-3" /> {beat.chip}
              </span>
            )}
          </p>
        </div>
      </div>
    );
  }
  if (beat.t === "approve") {
    return (
      <div className="hm-reveal flex shrink-0 items-center gap-2.5">
        <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md border border-white/10 bg-white/[0.06] text-zinc-200">
          <UserRound className="h-3.5 w-3.5" strokeWidth={2} />
        </span>
        <p className="text-[13px] text-zinc-300">
          <span className="font-semibold text-zinc-100">You</span> approved the fix:{" "}
          <span className="italic text-zinc-500">&ldquo;Ship it.&rdquo;</span>
        </p>
      </div>
    );
  }
  if (beat.t === "recovery") {
    return (
      <div className="hm-reveal shrink-0 rounded-lg border border-emerald-500/25 bg-emerald-500/[0.07] px-3 py-2 text-[13px] leading-snug text-emerald-100/90">
        <span className="inline-flex items-center gap-1.5 font-medium text-emerald-300">
          <ShieldCheck className="h-3.5 w-3.5" /> Recovery verified in Dynatrace.
        </span>{" "}
        Checkout latency is back to ~3ms, under the 300ms goal. Site Reliability Guardian: PASS.
      </div>
    );
  }
  return (
    <div className="hm-reveal flex shrink-0 items-center gap-2.5 rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-3 py-2">
      <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-300" strokeWidth={2} />
      <span className="text-[13px] font-medium text-emerald-200">Incident resolved in 4 minutes. Fix merged.</span>
    </div>
  );
}

function LiveBar({ next }: { next?: Beat }) {
  let label = "HiveMind is on it";
  let color: string | undefined;
  if (next?.t === "agent") {
    label = `${AGENTS[next.agent].name} is digging in`;
    color = AGENTS[next.agent].nameColor;
  } else if (next?.t === "approve") {
    label = "Waiting for your approval";
  } else if (next?.t === "recovery") {
    label = "Shipping the fix and checking recovery";
  }
  return (
    <div className="flex shrink-0 items-center gap-2.5 rounded-md border border-amber-400/20 bg-amber-400/[0.05] px-3 py-2">
      <span className="relative flex h-2 w-2 shrink-0">
        <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-amber-400/70" />
        <span className="relative inline-flex h-2 w-2 rounded-full bg-amber-400" />
      </span>
      <span className={cn("text-xs", color ?? "text-zinc-400")}>{label}</span>
      <span className="ml-auto inline-flex items-end gap-0.5 pb-0.5 text-amber-300/90">
        {[0, 150, 300].map((d) => (
          <span key={d} className="h-1 w-1 animate-bounce rounded-full bg-current" style={{ animationDelay: `${d}ms`, animationDuration: "900ms" }} />
        ))}
      </span>
    </div>
  );
}
