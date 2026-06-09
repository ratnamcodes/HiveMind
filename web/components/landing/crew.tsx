import {
  Search,
  Waves,
  GitPullRequest,
  Megaphone,
  ClipboardList,
  ShieldCheck,
  type LucideIcon,
} from "lucide-react";
import { Reveal } from "./fade";
import { Eyebrow, Headline } from "./section-heading";
import {
  DynatraceLogo,
  ElasticLogo,
  GitLabLogo,
  MongoDBLogo,
  BigQueryLogo,
  BRAND_COLOR,
} from "./brand-logos";

type Member = {
  icon: LucideIcon;
  name: string;
  partner: string;
  Logo: (p: { className?: string; style?: React.CSSProperties }) => React.ReactNode;
  color: string;
  does: string;
};

const CREW: Member[] = [
  { icon: Search, name: "Detective", partner: "Dynatrace", Logo: DynatraceLogo, color: BRAND_COLOR.dynatrace, does: "Finds the root cause in your live Grail data." },
  { icon: Waves, name: "LogDiver", partner: "Elastic", Logo: ElasticLogo, color: BRAND_COLOR.elastic, does: "Pins the slowdown to the exact deploy." },
  { icon: GitPullRequest, name: "CodeArch", partner: "GitLab", Logo: GitLabLogo, color: BRAND_COLOR.gitlab, does: "Opens the fix as a merge request you can read." },
  { icon: Megaphone, name: "Liaison", partner: "BigQuery", Logo: BigQueryLogo, color: BRAND_COLOR.bigquery, does: "Names the customers and the revenue at risk." },
  { icon: ClipboardList, name: "Scribe", partner: "MongoDB Atlas", Logo: MongoDBLogo, color: BRAND_COLOR.mongodb, does: "Writes the incident record as it happens." },
  { icon: ShieldCheck, name: "Reviewer", partner: "Dynatrace SRG", Logo: DynatraceLogo, color: BRAND_COLOR.dynatrace, does: "Signs off on the fix, then confirms the service recovered." },
];

export function Crew() {
  return (
    <section id="crew" className="relative mx-auto max-w-6xl scroll-my-24 px-4 xl:px-0">
      <Reveal className="max-w-2xl px-2">
        <Eyebrow>A real team, not a chatbot</Eyebrow>
        <Headline>Six specialists, each wired into a real system</Headline>
        <p className="mt-4 text-balance text-gray-600">
          One alert and they all jump in — each one fluent in the platform it drives. Together they see your
          production, your code, your customers, and your revenue at once.
        </p>
      </Reveal>

      <Reveal className="mt-10 grid grid-cols-1 gap-px overflow-hidden rounded-xl bg-gray-200 shadow-sm ring-1 ring-gray-200 sm:grid-cols-2 lg:grid-cols-3">
        {CREW.map((m) => {
          const Icon = m.icon;
          const Logo = m.Logo;
          return (
            <div key={m.name} className="group flex flex-col gap-3 bg-white p-6 transition-colors hover:bg-gray-50">
              <div className="flex items-center justify-between">
                <span className="flex size-10 items-center justify-center rounded-lg bg-gray-900 text-white shadow-sm">
                  <Icon className="size-5" strokeWidth={2} />
                </span>
                <Logo className="size-6 opacity-90" style={{ color: m.color }} />
              </div>
              <div>
                <div className="text-base font-semibold text-gray-900">{m.name}</div>
                <div className="font-mono text-[11px] tracking-wide text-gray-400 uppercase">{m.partner}</div>
              </div>
              <p className="text-sm leading-relaxed text-gray-600">{m.does}</p>
            </div>
          );
        })}
      </Reveal>
    </section>
  );
}
