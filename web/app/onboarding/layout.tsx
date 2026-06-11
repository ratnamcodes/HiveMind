import type { ReactNode } from "react";
import { redirect } from "next/navigation";
import { currentUserEmail } from "@/lib/session";

// Onboarding requires a session; unauthenticated visitors are sent to sign-in.
export default async function OnboardingLayout({ children }: { children: ReactNode }) {
  if (!(await currentUserEmail())) redirect("/sign-in");
  return children;
}
