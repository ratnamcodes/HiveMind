import { redirect } from "next/navigation";

// The war room always lands in #ops; the sidebar handles the rest.
export default function Home() {
  redirect("/c/ops");
}
