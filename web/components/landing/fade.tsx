"use client";

import { motion } from "motion/react";
import type { ReactNode } from "react";

// Solar-style staggered blur-up entrance. `FadeContainer` orchestrates, `FadeDiv`/`FadeSpan`
// are the children. `Reveal` is the on-scroll variant for sections below the fold.

const container = {
  hidden: {},
  show: {
    transition: { staggerChildren: 0.05, delayChildren: 0.15 },
  },
} as const;

const item = {
  hidden: { opacity: 0, y: 16, filter: "blur(4px)" },
  show: {
    opacity: 1,
    y: 0,
    filter: "blur(0px)",
    transition: { type: "spring", stiffness: 150, damping: 19, mass: 1.2 },
  },
} as const;

export function FadeContainer({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <motion.div variants={container} initial="hidden" animate="show" className={className}>
      {children}
    </motion.div>
  );
}

export function FadeDiv({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <motion.div variants={item} className={className}>
      {children}
    </motion.div>
  );
}

export function FadeSpan({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <motion.span variants={item} className={className}>
      {children}
    </motion.span>
  );
}

export function Reveal({
  children,
  className,
  delay = 0,
}: {
  children: ReactNode;
  className?: string;
  delay?: number;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 24, filter: "blur(4px)" }}
      whileInView={{ opacity: 1, y: 0, filter: "blur(0px)" }}
      viewport={{ once: true, margin: "-80px" }}
      transition={{ type: "spring", stiffness: 140, damping: 20, mass: 1, delay }}
      className={className}
    >
      {children}
    </motion.div>
  );
}
