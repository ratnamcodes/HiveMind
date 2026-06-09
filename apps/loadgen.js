"use strict";
// Steady real traffic against checkout (~10 rps) so Dynatrace has a clean signal and the
// regression shows up as a real latency curve (not a synthetic blip).
const http = require("http");
const TARGET = process.env.CHECKOUT_URL || "http://localhost:3100";
const RPS = Number(process.env.RPS || 10);

let ok = 0, slow = 0, err = 0;
function hit() {
  const t0 = Date.now();
  const req = http.get(`${TARGET}/checkout`, (r) => {
    let b = ""; r.on("data", (c) => (b += c));
    r.on("end", () => { const took = Date.now() - t0; if (r.statusCode >= 500) err++; else if (took > 300) slow++; else ok++; });
  });
  req.on("error", () => err++);
  req.setTimeout(10000, () => req.destroy());
}
setInterval(hit, Math.max(1, Math.floor(1000 / RPS)));
setInterval(() => { console.log(`[loadgen] ok=${ok} slow=${slow} err=${err} (last 10s)`); ok = slow = err = 0; }, 10000);
console.log(`[loadgen] hitting ${TARGET}/checkout at ~${RPS} rps`);
