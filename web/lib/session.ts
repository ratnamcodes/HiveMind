import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";

// Lightweight, dependency-free email/password auth: scrypt-hashed passwords in a JSON store +
// an HMAC-signed httpOnly session cookie. Real enough for the product (revocable, not plaintext),
// no native modules, no framework migration. Swap the store for Postgres + Better Auth later.

const SECRET = process.env.HIVEMIND_AUTH_SECRET || "hivemind-dev-secret-change-in-prod-0xA1";
const STORE = path.join(process.cwd(), ".hivemind-users.json");
export const SESSION_COOKIE = "hm_session";

type User = { email: string; name: string; hash: string };

function load(): Record<string, User> {
  try {
    return JSON.parse(fs.readFileSync(STORE, "utf8"));
  } catch {
    return {};
  }
}
function save(users: Record<string, User>) {
  fs.writeFileSync(STORE, JSON.stringify(users, null, 2));
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

export function signUp(email: string, password: string, name: string) {
  email = email.trim().toLowerCase();
  if (!email.includes("@") || password.length < 8) return { ok: false as const, error: "Enter a valid email and an 8+ char password." };
  const users = load();
  if (users[email]) return { ok: false as const, error: "An account with that email already exists." };
  users[email] = { email, name: name || email.split("@")[0], hash: hashPassword(password) };
  save(users);
  return { ok: true as const, token: sign(email), email };
}

export function signIn(email: string, password: string) {
  email = email.trim().toLowerCase();
  const users = load();
  const u = users[email];
  if (!u || !verifyPassword(password, u.hash)) return { ok: false as const, error: "Wrong email or password." };
  return { ok: true as const, token: sign(email), email };
}
