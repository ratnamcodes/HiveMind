import Link from "next/link";
import {
  Hexagon,
  Search,
  Waves,
  GitPullRequest,
  Megaphone,
  ClipboardList,
  ShieldCheck,
  ArrowRight,
  Activity,
  Wrench,
  CheckCircle2,
  Lock,
  Terminal,
} from "lucide-react";
import { LandingWarRoom } from "@/components/landing-war-room";

const AGENTS = [
  { icon: Search, name: "Detective", partner: "Dynatrace", does: "Finds the root cause in your live Grail data" },
  { icon: Waves, name: "LogDiver", partner: "Elastic", does: "Pins the slowdown to the exact deploy" },
  { icon: GitPullRequest, name: "CodeArch", partner: "GitLab", does: "Opens the fix as a merge request you can read" },
  { icon: Megaphone, name: "Liaison", partner: "BigQuery", does: "Names the customers and revenue at risk" },
  { icon: ClipboardList, name: "Scribe", partner: "MongoDB Atlas", does: "Writes the incident record" },
  { icon: ShieldCheck, name: "Reviewer", partner: "Dynatrace SRG", does: "Checks the service really recovered" },
];

function Nav() {
  return (
    <header className="sticky top-0 z-20 border-b border-border/80 bg-background/80 backdrop-blur">
      <div className="mx-auto flex h-14 max-w-6xl items-center justify-between px-6">
        <div className="flex items-center gap-2">
          <span className="flex h-7 w-7 items-center justify-center rounded-md border border-border bg-foreground text-background">
            <Hexagon className="h-4 w-4" strokeWidth={2.5} fill="currentColor" />
          </span>
          <span className="text-sm font-semibold tracking-tight">HiveMind</span>
        </div>
        <nav className="flex items-center gap-2 text-sm">
          <Link href="/sign-in" className="rounded-md px-3 py-1.5 text-muted-foreground transition-colors hover:text-foreground">
            Sign in
          </Link>
          <Link href="/onboarding" className="rounded-md border border-border px-3 py-1.5 font-medium transition-colors hover:bg-accent">
            Get started
          </Link>
        </nav>
      </div>
    </header>
  );
}

function Hero() {
  return (
    <section className="relative overflow-hidden border-b border-border">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 opacity-[0.55]"
        style={{ background: "radial-gradient(55% 45% at 50% 0%, oklch(0.7 0.12 250 / 0.10), transparent 70%)" }}
      />
      <div className="relative mx-auto max-w-6xl px-6 pb-16 pt-20 text-center">
        <div className="mx-auto mb-5 inline-flex items-center gap-2 rounded-full border border-border bg-card px-3 py-1 text-xs text-muted-foreground">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
          Runs on your Dynatrace data
        </div>
        <h1 className="mx-auto max-w-3xl text-balance text-4xl font-semibold tracking-tight sm:text-5xl">
          An AI crew that fixes your incidents, end to end.
        </h1>
        <p className="mx-auto mt-5 max-w-2xl text-pretty text-lg leading-relaxed text-muted-foreground">
          The moment Dynatrace flags a real problem, six AI specialists find the cause in your live
          data, open the fix in GitLab, and prove your service recovered. You approve every change.
          They handle the rest.
        </p>
        <div className="mt-8 flex items-center justify-center">
          <Link
            href="/onboarding"
            className="inline-flex items-center gap-2 rounded-lg bg-foreground px-5 py-2.5 text-sm font-semibold text-background transition-opacity hover:opacity-90"
          >
            Connect your stack <ArrowRight className="h-4 w-4" />
          </Link>
        </div>

        {/* The interactive, read-only war room: a real incident playing out, start to finish. */}
        <div className="mx-auto mt-12 w-full text-left">
          <LandingWarRoom />
          <p className="mt-3 text-center text-xs text-muted-foreground">
            A real incident, start to finish. It plays on its own. Hover to pause.
          </p>
        </div>
      </div>
    </section>
  );
}

function ValueProps() {
  const props = [
    { icon: Activity, title: "It catches the problem", body: "When Dynatrace flags a real issue on your service, HiveMind wakes up on its own. No polling, no setup. It pulls the cause and the evidence straight from your data." },
    { icon: Wrench, title: "It writes the fix", body: "It reads your live logs and traces, finds the one thing that broke, and opens the fix as a GitLab merge request. It even tells you which customers and how much revenue are at risk." },
    { icon: CheckCircle2, title: "It proves the recovery", body: "Once you approve, it merges and redeploys. Then a Dynatrace Site Reliability Guardian confirms the service is healthy again. The proof comes from Dynatrace, not from us." },
  ];
  return (
    <section className="border-b border-border">
      <div className="mx-auto grid max-w-6xl gap-px bg-border sm:grid-cols-3">
        {props.map((p) => (
          <div key={p.title} className="bg-background p-8">
            <p.icon className="h-5 w-5 text-muted-foreground" strokeWidth={2} />
            <h3 className="mt-4 text-lg font-semibold">{p.title}</h3>
            <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{p.body}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

function Crew() {
  return (
    <section className="border-b border-border">
      <div className="mx-auto max-w-6xl px-6 py-20">
        <div className="max-w-2xl">
          <h2 className="text-2xl font-semibold tracking-tight">A real team, not a chatbot</h2>
          <p className="mt-3 text-muted-foreground">
            Six specialists, each plugged into a real system. One alert and they all jump in. A single
            coding agent cannot see your production, your customers, or your revenue. This team can.
          </p>
        </div>
        <div className="mt-10 grid gap-px overflow-hidden rounded-lg border border-border bg-border sm:grid-cols-2 lg:grid-cols-3">
          {AGENTS.map((a) => (
            <div key={a.name} className="flex items-start gap-3 bg-card p-5">
              <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md border border-border bg-background text-foreground">
                <a.icon className="h-4 w-4" strokeWidth={2} />
              </span>
              <div>
                <div className="text-sm font-semibold">{a.name}</div>
                <div className="font-mono text-[11px] uppercase tracking-wide text-muted-foreground">{a.partner}</div>
                <div className="mt-1 text-sm text-muted-foreground">{a.does}</div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function ShowsWork() {
  return (
    <section className="border-b border-border bg-card/40">
      <div className="mx-auto grid max-w-6xl items-center gap-10 px-6 py-20 lg:grid-cols-2">
        <div>
          <h2 className="text-2xl font-semibold tracking-tight">Every claim comes with proof</h2>
          <p className="mt-3 text-muted-foreground">
            You do not have to take its word for anything. Each step links to the real thing behind it.
            The Dynatrace problem, the exact query it ran, the merge request, and the recovery check. A
            script cannot fake any of it.
          </p>
          <ul className="mt-5 space-y-2 text-sm text-muted-foreground">
            <li className="flex items-center gap-2"><Terminal className="h-4 w-4 text-muted-foreground" /> The real query, run on your Grail data</li>
            <li className="flex items-center gap-2"><Activity className="h-4 w-4 text-muted-foreground" /> The real Davis problem, linked to your tenant</li>
            <li className="flex items-center gap-2"><GitPullRequest className="h-4 w-4 text-muted-foreground" /> The real GitLab merge request</li>
            <li className="flex items-center gap-2"><ShieldCheck className="h-4 w-4 text-muted-foreground" /> A Dynatrace recovery check that goes from fail to pass</li>
          </ul>
        </div>
        <div className="rounded-lg border border-border bg-background p-4 font-mono text-[12.5px] leading-relaxed text-foreground/85">
          <div className="text-muted-foreground"># Detective, real query on your Grail data</div>
          <div className="mt-1">fetch spans, from:now()-30m</div>
          <div>| filter dt.entity.service == &quot;checkout&quot;</div>
          <div>| summarize p95 = percentile(duration, 95), by:&#123;bin(timestamp, 1m)&#125;</div>
          <div className="mt-3 text-emerald-400">p95 went from 80ms to 1,320ms after the payment-service deploy</div>
          <div className="mt-1 text-sky-300">problem P-2506-4471, root cause: payment-service</div>
        </div>
      </div>
    </section>
  );
}

function Trust() {
  const items = [
    { icon: Lock, title: "It never ships without you", body: "Every change stops at an approval step. HiveMind writes the fix. You decide if it goes out." },
    { icon: ShieldCheck, title: "Proof, not promises", body: "A Dynatrace Site Reliability Guardian checks the service recovered. We do not say it worked. Dynatrace does." },
    { icon: Activity, title: "Your data stays yours", body: "It runs on Vertex AI in your own cloud. Your telemetry is never used to train models." },
  ];
  return (
    <section className="border-b border-border">
      <div className="mx-auto grid max-w-6xl gap-px bg-border sm:grid-cols-3">
        {items.map((i) => (
          <div key={i.title} className="bg-background p-8">
            <i.icon className="h-5 w-5 text-muted-foreground" strokeWidth={2} />
            <h3 className="mt-4 text-base font-semibold">{i.title}</h3>
            <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{i.body}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

function CTA() {
  return (
    <section className="border-b border-border">
      <div className="mx-auto max-w-3xl px-6 py-24 text-center">
        <h2 className="text-3xl font-semibold tracking-tight">Turn your next 2am page into a merge request.</h2>
        <p className="mx-auto mt-4 max-w-xl text-muted-foreground">
          Connect your Dynatrace and GitLab in two minutes, then watch your first real incident get
          fixed from start to finish.
        </p>
        <div className="mt-8 flex items-center justify-center">
          <Link href="/onboarding" className="inline-flex items-center gap-2 rounded-lg bg-foreground px-5 py-2.5 text-sm font-semibold text-background transition-opacity hover:opacity-90">
            Connect your stack <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      </div>
    </section>
  );
}

export default function Landing() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <Nav />
      <Hero />
      <ValueProps />
      <Crew />
      <ShowsWork />
      <Trust />
      <CTA />
      <footer className="mx-auto flex max-w-6xl items-center justify-between px-6 py-8 text-xs text-muted-foreground">
        <span>HiveMind. AI incident response on Vertex AI and Google Cloud.</span>
        <span className="font-mono">Dynatrace · GitLab · Gemini</span>
      </footer>
    </div>
  );
}
