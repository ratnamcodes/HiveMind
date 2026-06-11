import { Activity, GitMerge, ShieldCheck } from "lucide-react";
import { Reveal } from "./fade";
import { Eyebrow, Headline } from "./section-heading";
import { GuideLines, DiagonalPattern } from "./guides";
import { Orbit } from "./orbit";
import { HiveMark } from "./hive-logo";
import {
  DynatraceLogo,
  ElasticLogo,
  GitLabLogo,
  MongoDBLogo,
  BigQueryLogo,
  BRAND_COLOR,
} from "./brand-logos";

// Illustration 1: partner systems orbiting the hive, Dynatrace raising a problem.
const ORBIT_MARKS = [
  { Logo: DynatraceLogo, color: BRAND_COLOR.dynatrace, alert: true },
  { Logo: ElasticLogo, color: BRAND_COLOR.elastic },
  { Logo: GitLabLogo, color: BRAND_COLOR.gitlab },
  { Logo: BigQueryLogo, color: BRAND_COLOR.bigquery },
  { Logo: MongoDBLogo, color: BRAND_COLOR.mongodb },
];

function DetectOrbit() {
  return (
    <div className="pointer-events-none flex h-[26rem] origin-center scale-[0.8] items-center justify-center p-10 select-none sm:scale-100">
      <Orbit
        durationSeconds={44}
        radiusPx={140}
        keepUpright
        orbitingObjects={ORBIT_MARKS.map(({ Logo, color, alert }, i) => (
          <div key={i} className="relative flex items-center justify-center">
            <div className="absolute size-11 rounded-full bg-white/70 ring-1 shadow-lg ring-black/5" />
            <Logo className="z-10 size-5" style={{ color }} />
            {alert && (
              <>
                <div className="absolute -top-6 left-4">
                  <div className="flex gap-1">
                    <div className="flex items-center justify-center rounded-l-full bg-red-500 p-1 ring-1 ring-gray-200">
                      <Activity className="size-3 shrink-0 text-white" />
                    </div>
                    <div className="rounded-r-full bg-white/80 py-0.5 pr-1.5 pl-1 text-xs whitespace-nowrap ring-1 ring-gray-200">
                      Davis problem
                    </div>
                  </div>
                </div>
                <div className="absolute size-11 animate-[ping_5s_ease_infinite] rounded-full ring-1 ring-red-500/50" />
              </>
            )}
          </div>
        ))}
      >
        <div className="relative flex h-48 w-48 items-center justify-center">
          <div className="rounded-full p-1 ring-1 ring-black/10">
            <div className="relative z-10 flex size-20 items-center justify-center rounded-full bg-white ring-1 shadow-[inset_0px_-15px_20px_rgba(0,0,0,0.1),0_7px_10px_0_rgba(0,0,0,0.15)] ring-black/20">
              <HiveMark className="size-10" />
            </div>
            <div className="absolute inset-12 animate-[spin_8s_linear_infinite] rounded-full bg-linear-to-t from-transparent via-orange-400 to-transparent blur-lg" />
          </div>
        </div>
      </Orbit>
    </div>
  );
}

// Illustration 2: live telemetry converging into a single merge request.
const SIGNALS = [
  { label: "p95", value: "1,320ms", top: 24, left: 8 },
  { label: "errors", value: "1,271", top: 120, left: 196 },
  { label: "deploy", value: "14:09", top: 232, left: 40 },
  { label: "trace", value: "checkout", top: 96, left: 264 },
];

function FixConverge() {
  return (
    <div className="pointer-events-none relative flex h-[26rem] origin-center scale-[0.8] items-center justify-center p-8 select-none sm:scale-100">
      <div className="relative h-80 w-80">
        {SIGNALS.map((s) => (
          <div key={s.label} className="absolute" style={{ top: s.top, left: s.left }}>
            <div className="relative">
              <div className="absolute inset-0 size-full animate-pulse rounded-md bg-orange-200/70 blur-[4px]" />
              <div className="relative flex items-center gap-1.5 rounded-md bg-white px-2 py-1 ring-1 shadow-sm ring-black/10">
                <span className="text-[10px] font-medium text-gray-500 uppercase">{s.label}</span>
                <span className="font-mono text-xs font-medium text-gray-700">{s.value}</span>
              </div>
            </div>
          </div>
        ))}
        {/* converging rays + center MR card */}
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2">
          <div className="relative">
            {[0, 60, 120, 180, 240, 300].map((rotation, index) => (
              <div key={rotation} className="absolute origin-left overflow-hidden" style={{ transform: `rotate(${rotation}deg)` }}>
                <div className="relative">
                  <div className="h-0.5 w-40 bg-linear-to-r from-gray-300 to-transparent" />
                  <div
                    className="absolute top-0 left-0 h-0.5 w-20 bg-linear-to-r from-transparent via-orange-400 to-transparent"
                    style={{ animation: `gridMovingLine 4s linear infinite ${index * 0.6}s`, animationFillMode: "backwards" }}
                  />
                </div>
              </div>
            ))}
            <div className="absolute -translate-x-1/2 -translate-y-1/2 rounded-lg border border-orange-300/60 bg-white px-3 py-2 shadow-xl shadow-orange-500/10">
              <div className="flex items-center gap-1.5">
                <GitMerge className="size-4 text-orange-600" />
                <span className="font-mono text-xs font-semibold text-gray-900">MR #52</span>
              </div>
              <div className="mt-0.5 font-mono text-[10px] text-gray-600">downstream_delay_ms → 0</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// Illustration 3: latency recovering past the SLO, SRG flipping fail to pass.
function RecoveryChart() {
  // x: 0..300, y: 0..140. A spike, then a sharp drop after the fix at x≈150.
  const pts = [
    [0, 118], [30, 112], [55, 96], [70, 40], [90, 28], [110, 30], [130, 26],
    [148, 24], [150, 118], [168, 124], [190, 126], [220, 127], [260, 128], [300, 128],
  ];
  const line = pts.map((p, i) => `${i === 0 ? "M" : "L"}${p[0]} ${p[1]}`).join(" ");
  const area = `${line} L300 140 L0 140 Z`;
  return (
    <div className="pointer-events-none flex h-[26rem] w-full items-center justify-center p-8 select-none">
      <div className="w-full max-w-md">
        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm text-gray-600">checkout p95 latency</div>
            <div className="mt-0.5 text-3xl font-semibold tracking-tight text-gray-900">3<span className="text-lg font-normal text-gray-500">ms</span></div>
          </div>
          <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-500/30 bg-emerald-50 px-2.5 py-1 text-xs font-semibold text-emerald-700">
            <ShieldCheck className="size-3.5" /> SRG: PASS
          </span>
        </div>
        <svg viewBox="0 0 300 150" className="mt-4 w-full" fill="none">
          <defs>
            <linearGradient id="rec-fill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0" stopColor="#f97316" stopOpacity="0.22" />
              <stop offset="1" stopColor="#f97316" stopOpacity="0" />
            </linearGradient>
          </defs>
          {/* SLO goal line */}
          <line x1="0" y1="92" x2="300" y2="92" className="stroke-gray-400" strokeWidth="1" strokeDasharray="4 4" />
          <text x="2" y="88" className="fill-gray-500" fontSize="9">300ms goal</text>
          <path d={area} fill="url(#rec-fill)" />
          <path d={line} className="stroke-orange-500" strokeWidth="2.5" strokeLinejoin="round" strokeLinecap="round" />
          {/* fix marker */}
          <line x1="150" y1="0" x2="150" y2="140" className="stroke-orange-400/50" strokeWidth="1" strokeDasharray="3 3" />
          <circle cx="150" cy="118" r="3.5" className="fill-white stroke-orange-500" strokeWidth="2" />
        </svg>
        <div className="mt-1 flex items-center justify-between font-mono text-[10px] text-gray-500">
          <span>before fix</span>
          <span className="text-orange-600">MR #52 merged</span>
          <span>after fix</span>
        </div>
      </div>
    </div>
  );
}

const STEPS = [
  {
    eyebrow: "1. It catches the problem",
    title: "The page wakes HiveMind, not you",
    body: "When Dynatrace Davis flags a real problem, HiveMind wakes up on its own. No polling, no rules to wire up. It pulls the cause and the evidence from your live Grail data.",
    bullets: ["Triggered by a real Davis problem", "Reads your own telemetry", "Opens an incident room in seconds"],
    Illustration: DetectOrbit,
  },
  {
    eyebrow: "2. It finds and writes the fix",
    title: "Six specialists, one merge request",
    body: "The crew reads your live logs and traces, pins the slowdown to the exact deploy, and opens the fix as a GitLab merge request. It even names the customers and revenue at risk.",
    bullets: ["Root cause from logs and traces", "A real, reviewable GitLab MR", "Customer and revenue impact, quantified"],
    Illustration: FixConverge,
  },
  {
    eyebrow: "3. It proves the recovery",
    title: "The proof comes from Dynatrace",
    body: "Once you approve, the fix ships. A Dynatrace Site Reliability Guardian confirms the service is healthy again. The verdict comes from Dynatrace, not us.",
    bullets: ["You approve before anything ships", "The fix ships only when you say yes", "SRG recovery check goes from fail to pass"],
    Illustration: RecoveryChart,
  },
];

export function HowItWorks() {
  return (
    <section id="how" className="relative mx-auto max-w-6xl scroll-my-24 px-4 xl:px-0">
      <GuideLines quarters />
      <Reveal className="mx-auto max-w-2xl px-2 text-center">
        <Eyebrow>How it works</Eyebrow>
        <Headline>From a 2am page to a verified fix, on its own</Headline>
        <p className="mt-4 text-balance text-gray-700">
          A single coding agent can&apos;t see your production, your customers, or your revenue. HiveMind is a
          team of specialists that can. It shows its work at every step.
        </p>
      </Reveal>

      <div className="mt-20 flex flex-col gap-y-24 md:gap-y-12">
        {STEPS.map((step, i) => {
          const Illustration = step.Illustration;
          const flip = i % 2 === 1;
          return (
            <Reveal key={step.eyebrow} className="grid grid-cols-1 items-center gap-8 md:grid-cols-2 md:gap-0">
              <div className={flip ? "px-2 md:order-2 md:pl-12" : "px-2 md:pr-12"}>
                <Eyebrow>{step.eyebrow}</Eyebrow>
                <Headline as="h3">{step.title}</Headline>
                <p className="mt-4 text-balance text-gray-700">{step.body}</p>
                <ul className="mt-5 space-y-2.5">
                  {step.bullets.map((b) => (
                    <li key={b} className="flex items-center gap-2.5 text-sm text-gray-700">
                      <span className="flex size-5 shrink-0 items-center justify-center rounded-full bg-orange-100 text-orange-600">
                        <CheckTiny />
                      </span>
                      {b}
                    </li>
                  ))}
                </ul>
              </div>
              <div className={`relative flex items-center justify-center overflow-hidden ${flip ? "md:order-1" : ""}`}>
                <DiagonalPattern className="[mask-image:linear-gradient(transparent,white_8rem,white_calc(100%-8rem),transparent)]" />
                <Illustration />
              </div>
            </Reveal>
          );
        })}
      </div>
    </section>
  );
}

function CheckTiny() {
  return (
    <svg viewBox="0 0 12 12" className="size-3" fill="none">
      <path d="M2.5 6.2 5 8.5 9.5 3.5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
