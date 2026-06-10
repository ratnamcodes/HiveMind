import type { ReactNode } from "react";
import { redirect } from "next/navigation";
import { currentUserEmail } from "@/lib/session";

// Onboarding is post-sign-in setup, so it requires a session too. Unauthenticated visitors are
// sent to sign-in; once they sign in they land back here.
export default async function OnboardingLayout({ children }: { children: ReactNode }) {
  if (!(await currentUserEmail())) redirect("/sign-in");
  return children;
}
