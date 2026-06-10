"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Menu, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { HiveMark } from "./hive-logo";
import { CtaButton } from "./cta-button";

const LINKS = [
  { label: "How it works", href: "#how" },
  { label: "The crew", href: "#crew" },
  { label: "Proof", href: "#proof" },
];

function useScrolled(threshold = 15) {
  const [scrolled, setScrolled] = useState(false);
  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > threshold);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, [threshold]);
  return scrolled;
}

export function NavBar() {
  const [open, setOpen] = useState(false);
  const scrolled = useScrolled(15);

  return (
    <header
      className={cn(
        "fixed inset-x-3 top-3 z-50 mx-auto flex max-w-6xl flex-col rounded-xl border border-transparent px-4 py-2.5 transition duration-300 sm:inset-x-4 sm:top-4 sm:px-3",
        open
          ? "border-gray-200/60 bg-white/95 shadow-2xl shadow-black/5 backdrop-blur-md"
          : scrolled
            ? "border-gray-200/60 bg-white/80 shadow-2xl shadow-black/5 backdrop-blur-md"
            : "bg-white/0",
      )}
    >
      <div className="flex w-full items-center justify-between">
        <Link href="/" aria-label="HiveMind home" className="flex items-center gap-2">
          <HiveMark className="h-7 w-7" />
          <span className="text-base font-semibold tracking-tight text-gray-900">HiveMind</span>
        </Link>

        <nav className="absolute left-1/2 hidden -translate-x-1/2 sm:block">
          <div className="flex items-center gap-8 text-sm font-medium">
            {LINKS.map((l) => (
              <Link key={l.href} href={l.href} className="text-gray-700 transition-colors hover:text-gray-900">
                {l.label}
              </Link>
            ))}
          </div>
        </nav>

        <div className="hidden items-center gap-2 sm:flex">
          <Link
            href="/sign-in"
            className="rounded-md px-3 py-2 text-sm font-medium text-gray-700 transition-colors hover:text-gray-900"
          >
            Sign in
          </Link>
          <CtaButton href="/onboarding" className="h-10 py-0">
            Connect your stack
          </CtaButton>
        </div>

        <button
          onClick={() => setOpen((v) => !v)}
          className="flex min-h-11 min-w-11 items-center justify-center rounded-md border border-gray-300 bg-white p-2.5 text-gray-900 sm:hidden"
          aria-label={open ? "Close menu" : "Open menu"}
          aria-expanded={open}
          aria-controls="mobile-nav"
        >
          {open ? <X className="size-5" /> : <Menu className="size-5" />}
        </button>
      </div>

      <nav id="mobile-nav" className={cn("mt-4 flex-col gap-1 text-base sm:hidden", open ? "flex" : "hidden")}>
        {LINKS.map((l) => (
          <Link
            key={l.href}
            href={l.href}
            onClick={() => setOpen(false)}
            className="rounded-md px-2 py-2 font-medium text-gray-800 hover:bg-gray-100"
          >
            {l.label}
          </Link>
        ))}
        <div className="mt-2 flex flex-col gap-2">
          <Link
            href="/sign-in"
            onClick={() => setOpen(false)}
            className="rounded-md border border-gray-300 px-3 py-2.5 text-center text-sm font-medium text-gray-900"
          >
            Sign in
          </Link>
          <CtaButton href="/onboarding" className="w-full">
            Connect your stack
          </CtaButton>
        </div>
      </nav>
    </header>
  );
}
