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

// Solar's folded-corner "sticker" card — amber icon + tick, with the agent's real partner mark.
const STICKER =
  "relative z-10 block h-full w-full overflow-hidden rounded-lg rounded-tr-[26px] bg-white px-6 pt-6 pb-5 shadow-[inset_0_0_0_1px] shadow-gray-200 transition-all duration-200 ease-in-out " +
  "before:absolute before:top-0 before:right-0 before:z-3 before:h-[30px] before:w-[30px] before:-translate-y-1/2 before:translate-x-1/2 before:rotate-45 before:bg-gray-50 before:shadow-[0_1px_0_0] before:shadow-gray-200 before:transition-all before:duration-200 before:content-[''] " +
  "after:absolute after:top-0 after:right-0 after:z-2 after:size-7 after:-translate-y-2 after:translate-x-2 after:rounded-bl-lg after:border after:border-gray-200 after:bg-gray-50 after:shadow-xs after:transition-all after:duration-200 after:content-[''] " +
  "hover:rounded-tr-[45px] hover:before:h-[50px] hover:before:w-[50px] hover:after:h-[42px] hover:after:w-[42px] hover:after:shadow-lg hover:after:shadow-black/5";

export function Crew() {
  return (
    <section id="crew" className="relative mx-auto max-w-6xl scroll-my-24 px-4 xl:px-0">
      <Reveal className="max-w-2xl px-2">
        <Eyebrow>A real team, not a chatbot</Eyebrow>
        <Headline>Six specialists, each wired into a real system</Headline>
        <p className="mt-4 text-balance text-gray-700">
          One alert and they all jump in. Each is fluent in the platform it drives, so together they see your
          production, your code, your customers, and your revenue at once.
        </p>
      </Reveal>

      <Reveal className="mt-14 grid grid-cols-1 gap-7 sm:grid-cols-2 lg:grid-cols-3">
        {CREW.map((m) => {
          const Icon = m.icon;
          const Logo = m.Logo;
          return (
            <div key={m.name} className="group relative">
              <div className={STICKER}>
                <div className="relative flex items-center gap-2.5">
                  <span className="absolute -left-5 h-5 w-[3px] rounded-r-sm bg-orange-500" />
                  <Icon className="size-5 shrink-0 text-orange-500" strokeWidth={2} />
                  <h3 className="font-semibold text-gray-900">{m.name}</h3>
                </div>
                <div className="mt-2.5 flex items-center gap-1.5">
                  <Logo className="size-4 shrink-0" style={{ color: m.color }} />
                  <span className="font-mono text-[11px] tracking-wide text-gray-600 uppercase">{m.partner}</span>
                </div>
                <p className="mt-2.5 text-sm leading-relaxed text-gray-700">{m.does}</p>
              </div>
            </div>
          );
        })}
      </Reveal>
    </section>
  );
}
