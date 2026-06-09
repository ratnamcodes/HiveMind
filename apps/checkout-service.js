"use strict";
// checkout-service — the user-facing service. Calls payment-service on every /checkout; the
// auto-instrumented HTTP call creates the real checkout->payment dependency + the real latency
// curve Dynatrace sees. When payment slows, checkout p95 spikes and ERROR logs appear in Grail.
const express = require("express");
const http = require("http");

const app = express();
const PORT = process.env.PORT || 3100;
const PAYMENT = process.env.PAYMENT_URL || "http://localhost:3101";
const SLO_MS = Number(process.env.CHECKOUT_SLO_MS || 300);
const HIVEMIND = process.env.HIVEMIND_URL || "http://localhost:8000";
const BREACH_TRIGGER = Number(process.env.BREACH_TRIGGER || 6); // sustained breaches before paging

// Self-monitor: when checkout's OWN real latency breaches the SLO repeatedly, page HiveMind
// once (debounced). This is the real, unfaked trigger — no seed, no manual fire.
let breaches = 0;
let paged = false;
function watchSlo(took, paymentMs) {
  if (took > SLO_MS) breaches += 1;
  else breaches = Math.max(0, breaches - 2);
  if (breaches >= BREACH_TRIGGER && !paged) {
    paged = true;
    const data = JSON.stringify({
      service: "checkout",
      severity: "sev1",
      symptom: "checkout p95 latency is breaching the 300ms SLO under load",
      evidence: `Observed ~${took}ms checkout latency (SLO 300ms), blocked on payment-service (~${paymentMs}ms) across sustained requests.`,
    });
    const req = http.request(`${HIVEMIND}/api/incoming/app-incident?user=hivemind`,
      { method: "POST", headers: { "Content-Type": "application/json", "Content-Length": Buffer.byteLength(data) } },
      (r) => r.resume());
    req.on("error", () => {});
    req.write(data); req.end();
    global.dtlog("ERROR", `sustained SLO breach (${breaches}x) — paged HiveMind`, {});
  }
  if (breaches === 0) paged = false; // re-arm after recovery so a future regression re-pages
}

function callPayment() {
  return new Promise((resolve, reject) => {
    const req = http.get(`${PAYMENT}/charge`, (r) => {
      let body = "";
      r.on("data", (c) => (body += c));
      r.on("end", () => resolve(JSON.parse(body || "{}")));
    });
    req.on("error", reject);
    req.setTimeout(8000, () => req.destroy(new Error("payment timeout")));
  });
}

app.get("/checkout", async (_req, res) => {
  const t0 = Date.now();
  try {
    const pay = await callPayment();
    const took = Date.now() - t0;
    watchSlo(took, pay.latency_ms);
    if (took > SLO_MS) {
      global.dtlog("ERROR", `checkout SLO breach: ${took}ms > ${SLO_MS}ms (blocked on payment ${pay.latency_ms}ms)`, { "checkout.latency_ms": took, "checkout.slo_ms": SLO_MS });
    } else {
      global.dtlog("INFO", `checkout ok ${took}ms`, { "checkout.latency_ms": took });
    }
    res.json({ ok: true, latency_ms: took });
  } catch (e) {
    const took = Date.now() - t0;
    global.dtlog("ERROR", `checkout failed after ${took}ms: ${e.message}`, { "checkout.latency_ms": took });
    res.status(502).json({ ok: false, error: e.message });
  }
});

app.get("/healthz", (_req, res) => res.json({ ok: true, service: "checkout-service" }));

app.listen(PORT, () => global.dtlog("INFO", `checkout-service listening on ${PORT} -> ${PAYMENT}`));
