import { NavBar } from "@/components/landing/navbar";
import { Hero } from "@/components/landing/hero";
import { LandingWarRoom } from "@/components/landing/war-room";
import { HowItWorks } from "@/components/landing/how-it-works";
import { Crew } from "@/components/landing/crew";
import { Proof } from "@/components/landing/proof";
import { Testimonial } from "@/components/landing/testimonial";
import { CallToAction } from "@/components/landing/cta";
import { Footer } from "@/components/landing/footer";
import { FeatureDivider } from "@/components/landing/divider";
import { Reveal } from "@/components/landing/fade";
import { Eyebrow, Headline } from "@/components/landing/section-heading";
import { GuideLines } from "@/components/landing/guides";

export default function Landing() {
  return (
    <div className="min-h-screen w-full overflow-x-hidden bg-gray-50 font-sans text-gray-900 antialiased selection:bg-orange-100 selection:text-orange-700">
      <NavBar />
      <main className="relative mx-auto flex flex-col">
        <div className="pt-48 sm:pt-60">
          <Hero />
        </div>

        {/* The product, playing for real: the dark war room framed against the light page. */}
        <section id="demo" className="relative mx-auto mt-52 w-full max-w-6xl scroll-my-24 px-4 xl:px-0">
          <GuideLines />
          <Reveal className="mx-auto mb-12 max-w-2xl text-center">
            <Eyebrow>See it work</Eyebrow>
            <Headline>One real incident, start to finish</Headline>
            <p className="mt-5 text-balance text-gray-700">
              This is the actual war room. It plays through once on its own. Replay it any time.
            </p>
          </Reveal>
          <Reveal delay={0.05}>
            <LandingWarRoom />
          </Reveal>
        </section>

        <FeatureDivider className="my-24 max-w-6xl" />

        <HowItWorks />

        <FeatureDivider className="my-24 max-w-6xl" />

        <Crew />

        <div className="mt-40">
          <Proof />
        </div>

        <div className="mt-40">
          <Testimonial />
        </div>

        <FeatureDivider className="my-24 max-w-6xl" />

        <div className="mb-40">
          <CallToAction />
        </div>

        <Footer />
        <div className="h-12" />
      </main>
    </div>
  );
}
