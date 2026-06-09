import Link from "next/link";
import type { SVGProps } from "react";
import { HiveMark } from "./hive-logo";
import { DiagonalPattern } from "./guides";
import { GoogleCloudLogo, GeminiLogo, BRAND_COLOR } from "./brand-logos";

const REPO_URL = "https://github.com/ratnamcodes/HiveMind";

// lucide-react dropped brand glyphs, so the GitHub mark is inline.
function Github(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden {...props}>
      <path d="M12 .5C5.73.5.5 5.73.5 12c0 5.08 3.29 9.39 7.86 10.91.58.11.79-.25.79-.56v-2c-3.2.7-3.88-1.37-3.88-1.37-.53-1.34-1.29-1.7-1.29-1.7-1.05-.72.08-.71.08-.71 1.16.08 1.77 1.19 1.77 1.19 1.03 1.77 2.7 1.26 3.36.96.1-.75.4-1.26.73-1.55-2.56-.29-5.25-1.28-5.25-5.7 0-1.26.45-2.29 1.19-3.1-.12-.29-.52-1.46.11-3.05 0 0 .97-.31 3.18 1.18a11 11 0 0 1 5.8 0c2.2-1.49 3.17-1.18 3.17-1.18.63 1.59.23 2.76.11 3.05.74.81 1.19 1.84 1.19 3.1 0 4.43-2.7 5.4-5.27 5.69.41.36.78 1.06.78 2.14v3.17c0 .31.21.68.8.56A11.51 11.51 0 0 0 23.5 12C23.5 5.73 18.27.5 12 .5Z" />
    </svg>
  );
}

const SECTIONS = {
  product: {
    title: "Product",
    items: [
      { label: "How it works", href: "#how" },
      { label: "The crew", href: "#crew" },
      { label: "Proof", href: "#proof" },
      { label: "Connect your stack", href: "/onboarding" },
      { label: "Sign in", href: "/sign-in" },
    ],
  },
  builtOn: {
    title: "Built on",
    items: [
      { label: "Dynatrace", href: "#" },
      { label: "GitLab", href: "#" },
      { label: "Elastic", href: "#" },
      { label: "MongoDB Atlas", href: "#" },
      { label: "BigQuery", href: "#" },
      { label: "Vertex AI", href: "#" },
    ],
  },
  company: {
    title: "Company",
    items: [
      { label: "About", href: "#" },
      { label: "Privacy", href: "#" },
      { label: "Terms", href: "#" },
      { label: "Contact", href: "#" },
    ],
  },
};

export function Footer() {
  return (
    <div className="px-4 xl:px-0">
      <footer className="relative mx-auto flex max-w-6xl flex-wrap pt-4">
        {/* dashed diagonal banner */}
        <div className="relative mb-10 h-20 w-full overflow-hidden border-y border-dashed border-gray-300">
          <DiagonalPattern />
        </div>

        <div className="mr-auto flex w-full justify-between lg:w-fit lg:flex-col">
          <Link href="/" className="flex items-center gap-2 text-gray-700 select-none" aria-label="HiveMind home">
            <HiveMark className="size-7" />
            <span className="text-base font-semibold tracking-tight text-gray-900">HiveMind</span>
          </Link>
          <div>
            <div className="mt-4 flex items-center">
              <Link href={REPO_URL} target="_blank" rel="noopener noreferrer" aria-label="HiveMind on GitHub" className="rounded-sm p-2 text-gray-600 transition-colors hover:bg-gray-200 hover:text-gray-900">
                <Github className="size-5" />
              </Link>
            </div>
            <div className="mt-2 flex items-center gap-2 pl-2 text-xs text-gray-400">
              <span>Built on</span>
              <GoogleCloudLogo className="size-4" style={{ color: BRAND_COLOR.googlecloud }} />
              <span className="text-gray-500">Google Cloud</span>
              <span aria-hidden>·</span>
              <GeminiLogo className="size-4" />
              <span className="text-gray-500">Gemini on Vertex AI</span>
            </div>
          </div>
        </div>

        {Object.entries(SECTIONS).map(([key, section]) => (
          <div key={key} className="mt-10 min-w-44 pl-2 lg:mt-0 lg:pl-0">
            <h3 className="mb-4 text-sm font-medium text-gray-900">{section.title}</h3>
            <ul className="space-y-4">
              {section.items.map((item) => (
                <li key={item.label} className="text-sm">
                  <Link href={item.href} className="text-gray-600 transition-colors hover:text-gray-900">
                    {item.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        ))}

        <div className="mt-12 w-full border-t border-gray-200 pt-6 text-xs text-gray-400">
          © {new Date().getFullYear()} HiveMind · An autonomous incident-response crew. Dynatrace · GitLab · Gemini on Vertex AI.
        </div>
      </footer>
    </div>
  );
}
