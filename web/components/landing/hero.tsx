import { ArrowRight, ArrowUpRight } from "lucide-react";
import { FadeContainer, FadeDiv, FadeSpan } from "./fade";
import { CtaButton } from "./cta-button";
import { GameOfLife } from "./game-of-life";
import {
  DynatraceLogo,
  ElasticLogo,
  GitLabLogo,
  MongoDBLogo,
  BigQueryLogo,
} from "./brand-logos";

const TRUST = [
  { name: "Dynatrace", Logo: DynatraceLogo },
  { name: "GitLab", Logo: GitLabLogo },
  { name: "Elastic", Logo: ElasticLogo },
  { name: "MongoDB", Logo: MongoDBLogo },
  { name: "BigQuery", Logo: BigQueryLogo },
];

export function Hero() {
  return (
    <section aria-label="hero" className="relative isolate">
      <div className="absolute inset-0 z-0 flex items-center justify-center overflow-hidden">
        <GameOfLife />
      </div>
      <FadeContainer className="relative z-10 flex flex-col items-center justify-center px-4">
        <FadeDiv className="mx-auto">
          <a href="#demo" className="group mx-auto w-full">
            <div className="inline-flex max-w-full items-center gap-3 rounded-full bg-white/60 px-2.5 py-0.5 pr-3 pl-0.5 font-medium text-gray-900 ring-1 shadow-lg shadow-amber-400/20 ring-black/10 backdrop-blur-[1px] transition-colors hover:bg-amber-500/5 sm:text-sm">
              <span className="shrink-0 truncate rounded-full border border-gray-200 bg-gray-50 px-2.5 py-1 text-xs text-gray-600">
                Live
              </span>
              <span className="flex items-center gap-1 truncate">
                <span className="size-1.5 rounded-full bg-emerald-500" />
                <span className="w-full truncate">Watch a real incident get fixed</span>
                <ArrowUpRight className="size-4 shrink-0 text-gray-700 transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
              </span>
            </div>
          </a>
        </FadeDiv>

        <h1 className="mt-8 text-center text-5xl font-semibold tracking-tighter text-balance text-gray-900 sm:text-7xl sm:leading-[1.05] lg:text-8xl lg:leading-[1.02]">
          <FadeSpan>Incidents,</FadeSpan> <FadeSpan>fixed</FadeSpan>
          <br />
          <FadeSpan>end</FadeSpan> <FadeSpan>to</FadeSpan> <FadeSpan>end.</FadeSpan>
        </h1>

        <p className="mt-6 max-w-xl text-center text-base text-balance text-gray-700 sm:mt-7 sm:text-xl">
          <FadeSpan>The moment Dynatrace flags a real problem, six AI specialists</FadeSpan>{" "}
          <FadeSpan>find the cause in your live data, open the fix in GitLab,</FadeSpan>{" "}
          <FadeSpan>and prove your service recovered. You approve every change.</FadeSpan>
        </p>

        <FadeDiv className="mt-7 flex flex-col items-center gap-3 sm:flex-row">
          <CtaButton href="/onboarding">
            Connect your stack <ArrowRight className="size-4" />
          </CtaButton>
          <CtaButton href="#demo" variant="secondary">
            Watch the demo
          </CtaButton>
        </FadeDiv>

        <FadeDiv className="mt-12 w-full max-w-3xl">
          <p className="text-center text-xs font-medium tracking-wide text-gray-500 uppercase">
            Runs on the stack you already have
          </p>
          <div className="mt-5 flex flex-wrap items-center justify-center gap-x-9 gap-y-5">
            {TRUST.map(({ name, Logo }) => (
              <div key={name} className="flex items-center gap-2 text-gray-400 transition-colors hover:text-gray-600">
                <Logo className="h-6 w-6" />
                <span className="text-sm font-medium">{name}</span>
              </div>
            ))}
          </div>
        </FadeDiv>
      </FadeContainer>
    </section>
  );
}
