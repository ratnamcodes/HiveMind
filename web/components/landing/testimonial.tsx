import { HiveMark } from "./hive-logo";

// A honeycomb-tinted pull quote — the Solar testimonial slot, reframed around the on-call reality.
export function Testimonial() {
  return (
    <section className="px-4 xl:px-0">
      <div className="relative mx-auto w-full max-w-6xl overflow-hidden rounded-2xl bg-linear-to-br from-amber-500 via-orange-500 to-orange-600 shadow-2xl shadow-amber-500/20 ring-1 ring-black/5">
        {/* honeycomb motif */}
        <svg aria-hidden className="absolute inset-0 size-full opacity-[0.15] [mask-image:radial-gradient(white,transparent_85%)]">
          <defs>
            <pattern id="honeycomb" width="56" height="48" patternUnits="userSpaceOnUse" patternTransform="scale(1.4)">
              <path
                d="M28 0 L42 8 V24 L28 32 L14 24 V8 Z M0 24 L14 32 V48 L0 56 M56 24 L42 32 V48 L56 56"
                fill="none"
                stroke="white"
                strokeWidth="1.4"
              />
            </pattern>
          </defs>
          <rect width="100%" height="100%" fill="url(#honeycomb)" />
        </svg>

        <div className="relative z-10 p-8 sm:p-14 lg:p-20">
          <HiveMark className="size-10 drop-shadow-sm" />
          <blockquote className="mt-8 max-w-3xl text-2xl leading-snug font-medium tracking-tight text-balance text-white md:text-3xl lg:text-4xl">
            <p className="relative before:absolute before:right-full before:text-white/55 before:content-['“'] after:text-white/55 after:content-['”']">
              On-call used to start with a blank terminal at 2am.{" "}
              <span className="text-white/75">
                Now it starts with a root cause, a merge request, and a recovery check already waiting — and a
                human still says yes before anything ships.
              </span>
            </p>
          </blockquote>
          <div className="mt-10 flex items-center gap-3">
            <span className="h-px w-8 bg-white/40" />
            <span className="text-sm font-medium text-white/80">The on-call reality, before and after HiveMind</span>
          </div>
        </div>
      </div>
    </section>
  );
}
