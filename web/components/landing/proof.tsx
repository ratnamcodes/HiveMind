import { Activity, GitPullRequest, ShieldCheck, Terminal } from "lucide-react";
import { Reveal } from "./fade";
import { Eyebrow, Headline } from "./section-heading";

const PROOFS = [
  { Icon: Terminal, text: "The real DQL query, run on your Grail data" },
  { Icon: Activity, text: "The real Davis problem, linked to your tenant" },
  { Icon: GitPullRequest, text: "The real GitLab merge request" },
  { Icon: ShieldCheck, text: "A Dynatrace recovery check that goes fail → pass" },
];

export function Proof() {
  return (
    <section id="proof" className="relative scroll-my-24 border-y border-gray-200 bg-white">
      <div className="mx-auto grid max-w-6xl items-center gap-10 px-4 py-20 lg:grid-cols-2 xl:px-0">
        <Reveal>
          <Eyebrow>Every claim comes with proof</Eyebrow>
          <Headline>You never have to take its word for it</Headline>
          <p className="mt-4 text-balance text-gray-600">
            Every step links to the real artifact behind it. A script can&apos;t fake a live Grail query, a
            Davis problem on your tenant, a merge request in your repo, or a Site Reliability Guardian flipping
            green.
          </p>
          <ul className="mt-6 space-y-3">
            {PROOFS.map(({ Icon, text }) => (
              <li key={text} className="flex items-center gap-3 text-sm text-gray-700">
                <span className="flex size-7 shrink-0 items-center justify-center rounded-md border border-gray-200 bg-gray-50 text-amber-600">
                  <Icon className="size-4" strokeWidth={2} />
                </span>
                {text}
              </li>
            ))}
          </ul>
        </Reveal>

        <Reveal delay={0.05}>
          <div className="overflow-hidden rounded-xl border border-white/10 bg-[#0b0d10] shadow-2xl shadow-black/20">
            <div className="flex items-center gap-2 border-b border-white/10 bg-white/[0.03] px-4 py-2.5">
              <div className="flex gap-1.5">
                <span className="h-2.5 w-2.5 rounded-full bg-red-400/70" />
                <span className="h-2.5 w-2.5 rounded-full bg-amber-400/70" />
                <span className="h-2.5 w-2.5 rounded-full bg-emerald-400/70" />
              </div>
              <span className="ml-2 font-mono text-[11px] text-zinc-400">detective · execute_dql</span>
            </div>
            <div className="space-y-1 p-5 font-mono text-[12.5px] leading-relaxed text-zinc-300">
              <div className="text-zinc-500"># real query, on your Grail data</div>
              <div>fetch spans, from:now()-30m</div>
              <div>| filter dt.entity.service == <span className="text-amber-300">&quot;checkout&quot;</span></div>
              <div>| summarize p95 = percentile(duration, 95),</div>
              <div className="pl-10">by:&#123;bin(timestamp, 1m)&#125;</div>
              <div className="mt-3 text-emerald-300">→ p95 climbed 80ms → 1,320ms after the payment-service deploy</div>
              <div className="text-sky-300">→ problem P-2506-4471 · root cause: payment-service</div>
            </div>
          </div>
        </Reveal>
      </div>
    </section>
  );
}
