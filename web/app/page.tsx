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
    <div className="min-h-screen w-full overflow-x-hidden bg-gray-50 font-sans text-gray-900 antialiased selection:bg-amber-100 selection:text-amber-700">
      <NavBar />
      <main className="relative mx-auto flex flex-col">
        <div className="pt-44 sm:pt-56">
          <Hero />
        </div>

        {/* The product, playing for real — the dark war room framed against the light page. */}
        <section id="demo" className="relative mx-auto mt-24 w-full max-w-6xl scroll-my-24 px-4 xl:px-0">
          <GuideLines />
          <Reveal className="mx-auto mb-8 max-w-2xl text-center">
            <Eyebrow>See it work</Eyebrow>
            <Headline>One real incident, start to finish</Headline>
            <p className="mt-4 text-balance text-gray-600">
              This is the actual war room. It plays on its own — hover to pause and read along.
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

        <div className="mt-24">
          <Proof />
        </div>

        <div className="mt-24">
          <Testimonial />
        </div>

        <FeatureDivider className="my-24 max-w-6xl" />

        <div className="mb-32">
          <CallToAction />
        </div>

        <Footer />
        <div className="h-10" />
      </main>
    </div>
  );
}
