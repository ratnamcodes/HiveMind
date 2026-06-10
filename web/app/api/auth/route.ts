import { SESSION_COOKIE, signIn, signUp, verifySession } from "@/lib/session";

// POST { action: "signin" | "signup" | "signout", email, password, name } — sets/clears the
// httpOnly session cookie. GET returns the current session (for the client to know who's in).

export async function POST(req: Request) {
  const body = await req.json().catch(() => ({}));
  const { action, email, password, name } = body as Record<string, string>;

  // Send the session cookie over HTTPS only in production (keeps local http dev working).
  const secure = process.env.NODE_ENV === "production" ? "; Secure" : "";

  if (action === "signout") {
    return new Response(JSON.stringify({ ok: true }), {
      headers: {
        "Content-Type": "application/json",
        "Set-Cookie": `${SESSION_COOKIE}=; HttpOnly; Path=/; SameSite=Lax${secure}; Max-Age=0`,
      },
    });
  }

  const res = action === "signup" ? await signUp(email, password, name) : await signIn(email, password);
  if (!res.ok) return Response.json({ ok: false, error: res.error }, { status: 400 });

  return new Response(JSON.stringify({ ok: true, email: res.email }), {
    headers: {
      "Content-Type": "application/json",
      "Set-Cookie": `${SESSION_COOKIE}=${res.token}; HttpOnly; Path=/; SameSite=Lax${secure}; Max-Age=${7 * 24 * 3600}`,
    },
  });
}

export async function GET(req: Request) {
  const cookie = req.headers.get("cookie") || "";
  const m = cookie.match(new RegExp(`${SESSION_COOKIE}=([^;]+)`));
  const email = verifySession(m?.[1]);
  return Response.json({ email });
}
