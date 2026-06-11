import crypto from "node:crypto";
import { cookies } from "next/headers";

// Email/password auth: scrypt-hashed passwords + an HMAC-signed httpOnly session cookie.
// User records live in the backend (Vercel's filesystem is ephemeral); hashing and signing stay here.

const SECRET = process.env.HIVEMIND_AUTH_SECRET || "hivemind-dev-secret-change-in-prod-0xA1";
export const SESSION_COOKIE = "hm_session";

// NEXT_PUBLIC_* vars are readable server-side too, so they serve as fallbacks when HIVEMIND_BACKEND_URL isn't set.
const BACKEND = (
  process.env.HIVEMIND_BACKEND_URL ||
  process.env.NEXT_PUBLIC_BACKEND_BASE ||
  process.env.NEXT_PUBLIC_API_BASE ||
  "http://localhost:8000"
).replace(/\/$/, "");

type User = { email: string; name: string; hash: string };

async function fetchUser(email: string): Promise<User | null> {
  try {
    const r = await fetch(`${BACKEND}/api/users/${encodeURIComponent(email)}`, { cache: "no-store" });
    if (!r.ok) return null;
    const d = await r.json();
    return d.found ? { email: d.email, name: d.name, hash: d.hash } : null;
  } catch {
    return null;
  }
}
async function putUser(u: User): Promise<{ ok: boolean; error?: string }> {
  try {
    const r = await fetch(`${BACKEND}/api/users`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(u),
    });
    const d = await r.json().catch(() => ({}));
    return { ok: !!d.ok, error: d.error };
  } catch {
    return { ok: false, error: "store unavailable" };
  }
}

function hashPassword(pw: string): string {
  const salt = crypto.randomBytes(16).toString("hex");
  const dk = crypto.scryptSync(pw, salt, 32).toString("hex");
  return `${salt}:${dk}`;
}
function verifyPassword(pw: string, stored: string): boolean {
  const [salt, dk] = stored.split(":");
  if (!salt || !dk) return false;
  const test = crypto.scryptSync(pw, salt, 32).toString("hex");
  return crypto.timingSafeEqual(Buffer.from(dk), Buffer.from(test));
}

function sign(email: string): string {
  const payload = `${email}|${Date.now()}`;
  const mac = crypto.createHmac("sha256", SECRET).update(payload).digest("hex");
  return Buffer.from(`${payload}|${mac}`).toString("base64url");
}
export function verifySession(token: string | undefined): string | null {
  if (!token) return null;
  try {
    const [email, ts, mac] = Buffer.from(token, "base64url").toString().split("|");
    const expected = crypto.createHmac("sha256", SECRET).update(`${email}|${ts}`).digest("hex");
    if (!crypto.timingSafeEqual(Buffer.from(mac), Buffer.from(expected))) return null;
    if (Date.now() - Number(ts) > 7 * 24 * 3600 * 1000) return null; // 7-day expiry
    return email;
  } catch {
    return null;
  }
}

export async function signUp(email: string, password: string, name: string) {
  email = email.trim().toLowerCase();
  if (!email.includes("@") || password.length < 8)
    return { ok: false as const, error: "Enter a valid email and an 8+ character password." };
  const res = await putUser({ email, name: name || email.split("@")[0], hash: hashPassword(password) });
  if (!res.ok)
    return {
      ok: false as const,
      error: res.error === "exists" ? "An account with that email already exists." : "Could not create the account. Please try again.",
    };
  return { ok: true as const, token: sign(email), email };
}

export async function signIn(email: string, password: string) {
  email = email.trim().toLowerCase();
  const u = await fetchUser(email);
  if (!u || !verifyPassword(password, u.hash)) return { ok: false as const, error: "Wrong email or password." };
  return { ok: true as const, token: sign(email), email };
}

// The signed-in user's email from the session cookie, or null.
export async function currentUserEmail(): Promise<string | null> {
  const store = await cookies();
  return verifySession(store.get(SESSION_COOKIE)?.value);
}
