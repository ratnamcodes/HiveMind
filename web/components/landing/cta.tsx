import { ArrowRight, CheckCircle2, GitMerge, ShieldCheck } from "lucide-react";
import { Reveal } from "./fade";
import { CtaButton } from "./cta-button";

export function CallToAction() {
  return (
    <section className="px-4 xl:px-0">
      <Reveal className="mx-auto grid max-w-6xl items-center gap-10 sm:grid-cols-6">
        <div className="sm:col-span-3">
          <h2 className="text-3xl font-semibold tracking-tighter text-balance text-gray-900 md:text-4xl">
            Turn your next 2am page into a merge request.
          </h2>
          <p className="mt-4 mb-8 max-w-md text-lg text-gray-600">
            Connect Dynatrace and GitLab in about two minutes, then watch your first real incident get fixed
            from start to finish.
          </p>
          <div className="flex flex-wrap gap-3">
            <CtaButton href="/onboarding">
              Connect your stack <ArrowRight className="size-4" />
            </CtaButton>
            <CtaButton href="/sign-in" variant="secondary">
              Sign in
            </CtaButton>
          </div>
        </div>

        <div className="relative isolate sm:col-span-3 sm:h-full">
          <div className="relative overflow-hidden rounded-2xl border border-amber-200 bg-linear-to-br from-amber-50 to-orange-50 p-6 shadow-xl shadow-amber-500/10">
            <div className="flex items-center justify-between">
              <span className="inline-flex items-center gap-1.5 rounded-full border border-red-500/30 bg-red-50 px-2 py-0.5 text-[11px] font-semibold text-red-600">
                SEV1 · checkout
              </span>
              <span className="font-mono text-[11px] text-gray-500">resolved in 4m</span>
            </div>
            <div className="mt-4 space-y-2.5">
              <Row Icon={GitMerge} tone="amber">CodeArch opened MR #52 — one-line fix</Row>
              <Row Icon={CheckCircle2} tone="gray">You approved: &ldquo;Ship it.&rdquo;</Row>
              <Row Icon={ShieldCheck} tone="emerald">SRG recovery check: PASS · p95 back to 3ms</Row>
            </div>
            <div className="mt-5 rounded-lg border border-emerald-500/30 bg-emerald-50 px-3 py-2 text-sm font-medium text-emerald-700">
              Incident resolved — fix merged, recovery verified.
            </div>
          </div>
        </div>
      </Reveal>
    </section>
  );
}

function Row({
  Icon,
  tone,
  children,
}: {
  Icon: typeof GitMerge;
  tone: "amber" | "gray" | "emerald";
  children: React.ReactNode;
}) {
  const tones = {
    amber: "border-amber-300/60 bg-white text-amber-600",
    gray: "border-gray-200 bg-white text-gray-500",
    emerald: "border-emerald-300/60 bg-white text-emerald-600",
  } as const;
  return (
    <div className="flex items-center gap-2.5 text-sm text-gray-700">
      <span className={`flex size-7 shrink-0 items-center justify-center rounded-md border ${tones[tone]}`}>
        <Icon className="size-4" strokeWidth={2} />
      </span>
      {children}
    </div>
  );
}
