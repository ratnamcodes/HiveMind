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

const AGENTS = [
  { icon: Search, name: "Detective", partner: "Dynatrace", does: "Finds root cause in real Grail data" },
  { icon: Waves, name: "LogDiver", partner: "Elastic", does: "Blames the exact deploy from the logs" },
  { icon: GitPullRequest, name: "CodeArch", partner: "GitLab", does: "Opens the fix as a reviewable MR" },
  { icon: Megaphone, name: "Liaison", partner: "BigQuery", does: "Names affected customers + revenue" },
  { icon: ClipboardList, name: "Scribe", partner: "MongoDB Atlas", does: "Writes the postmortem" },
  { icon: ShieldCheck, name: "Reviewer", partner: "Dynatrace SRG", does: "Proves the SLO recovered" },
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
          <Link href="/c/ops" className="rounded-md px-3 py-1.5 text-muted-foreground transition-colors hover:text-foreground">
            Live war room
          </Link>
          <Link href="/sign-in" className="rounded-md border border-border px-3 py-1.5 font-medium transition-colors hover:bg-accent">
            Sign in
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
        className="pointer-events-none absolute inset-0 opacity-[0.6]"
        style={{ background: "radial-gradient(60% 50% at 50% 0%, oklch(0.7 0.12 250 / 0.10), transparent 70%)" }}
      />
      <div className="relative mx-auto max-w-4xl px-6 py-24 text-center">
        <div className="mx-auto mb-5 inline-flex items-center gap-2 rounded-full border border-border bg-card px-3 py-1 text-xs text-muted-foreground">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
          Runs on your real Dynatrace telemetry — no synthetic data
        </div>
        <h1 className="text-balance text-4xl font-semibold tracking-tight sm:text-5xl">
          From a Dynatrace alert to a merged fix — automatically.
        </h1>
        <p className="mx-auto mt-5 max-w-2xl text-pretty text-lg leading-relaxed text-muted-foreground">
          HiveMind is a crew of six AI specialists that wakes the moment Davis raises a real problem,
          finds the root cause in your real production data, opens the GitLab fix, and proves your
          service recovered against an SLO — with a human approving every change.
        </p>
        <div className="mt-8 flex items-center justify-center gap-3">
          <Link
            href="/onboarding"
            className="inline-flex items-center gap-2 rounded-lg bg-foreground px-5 py-2.5 text-sm font-semibold text-background transition-opacity hover:opacity-90"
          >
            Connect your stack <ArrowRight className="h-4 w-4" />
          </Link>
          <Link
            href="/c/ops"
            className="inline-flex items-center gap-2 rounded-lg border border-border px-5 py-2.5 text-sm font-medium transition-colors hover:bg-accent"
          >
            Watch a live incident
          </Link>
        </div>
        <div className="mt-10 flex flex-wrap items-center justify-center gap-x-6 gap-y-2 font-mono text-xs text-muted-foreground">
          <span>6 specialist agents</span>
          <span className="text-border">·</span>
          <span>Real Dynatrace Grail data</span>
          <span className="text-border">·</span>
          <span>Human-approved fixes</span>
        </div>
      </div>
    </section>
  );
}

function ValueProps() {
  const props = [
    { icon: Activity, title: "Detect", body: "A real Davis problem on your service triggers HiveMind — no polling, no seed. It pulls the real root-cause entity and evidence straight from Dynatrace." },
    { icon: Wrench, title: "Fix", body: "It diagnoses from real Grail logs and spans, then opens the exact one-file fix as a GitLab merge request — and names the customers and revenue at risk." },
    { icon: CheckCircle2, title: "Recover", body: "After you approve, it merges, redeploys, and a Site Reliability Guardian flips Fail to Pass — Dynatrace itself proves the SLO recovered." },
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
            Six separately-credentialed specialists, each wired to a real system. One alert fans out;
            a human commands. A solo coding agent can&apos;t see your production, your warehouse, or your
            revenue — HiveMind can.
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
          <h2 className="text-2xl font-semibold tracking-tight">AI that shows its work</h2>
          <p className="mt-3 text-muted-foreground">
            Every claim is backed by an artifact you can click — a real Dynatrace problem ID, the exact
            DQL it ran, the merge request URL, and the Guardian verdict. None of it can be faked by a script.
          </p>
          <ul className="mt-5 space-y-2 text-sm text-muted-foreground">
            <li className="flex items-center gap-2"><Terminal className="h-4 w-4 text-muted-foreground" /> Real DQL, run on your Grail</li>
            <li className="flex items-center gap-2"><Activity className="h-4 w-4 text-muted-foreground" /> A real Davis problem ID, deep-linked to your tenant</li>
            <li className="flex items-center gap-2"><GitPullRequest className="h-4 w-4 text-muted-foreground" /> A real GitLab MR, authored by the bot</li>
            <li className="flex items-center gap-2"><ShieldCheck className="h-4 w-4 text-muted-foreground" /> A Dynatrace SRG verdict: Fail to Pass</li>
          </ul>
        </div>
        <div className="rounded-lg border border-border bg-background p-4 font-mono text-[12.5px] leading-relaxed text-foreground/85">
          <div className="text-muted-foreground"># Detective · real DQL on Grail</div>
          <div className="mt-1">fetch spans, from:now()-30m</div>
          <div>| filter dt.entity.service == &quot;checkout&quot;</div>
          <div>| summarize p95 = percentile(duration, 95), by:&#123;bin(timestamp, 1m)&#125;</div>
          <div className="mt-3 text-emerald-400">→ p95 80ms → 1,320ms after payment-service deploy</div>
          <div className="mt-1 text-sky-300">→ problem P-2506-4471 · root cause: payment-service</div>
        </div>
      </div>
    </section>
  );
}

function Trust() {
  const items = [
    { icon: Lock, title: "Never ships without you", body: "Every change pauses at a human approval gate. HiveMind drafts the fix — you decide if it ships." },
    { icon: ShieldCheck, title: "Proven recovery, not claims", body: "A Dynatrace Site Reliability Guardian validates the SLO recovered. We don't say it worked — Dynatrace does." },
    { icon: Activity, title: "Your data stays yours", body: "Runs on Vertex AI on your own cloud. Your telemetry is never used to train models." },
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
          Connect your Dynatrace and GitLab in two minutes and watch your first real incident resolve end to end.
        </p>
        <div className="mt-8 flex items-center justify-center gap-3">
          <Link href="/onboarding" className="inline-flex items-center gap-2 rounded-lg bg-foreground px-5 py-2.5 text-sm font-semibold text-background transition-opacity hover:opacity-90">
            Connect your stack <ArrowRight className="h-4 w-4" />
          </Link>
          <Link href="/c/ops" className="inline-flex items-center gap-2 rounded-lg border border-border px-5 py-2.5 text-sm font-medium transition-colors hover:bg-accent">
            Watch a live incident
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
        <span>HiveMind · AI incident response on Vertex AI &amp; Google Cloud</span>
        <span className="font-mono">Dynatrace · GitLab · Gemini</span>
      </footer>
    </div>
  );
}
