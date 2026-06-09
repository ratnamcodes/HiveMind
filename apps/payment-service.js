"use strict";
// payment-service — the downstream service whose config drives a REAL regression.
// It reads `downstream_delay_ms` from config/payment.yaml on EVERY request, so flipping that
// file (the same knob CodeArch fixes in the GitLab repo) changes real latency with no restart.
const express = require("express");
const fs = require("fs");
const path = require("path");
const YAML = require("yaml");

const app = express();
const PORT = process.env.PORT || 3101;
const CONFIG = path.join(__dirname, "config", "payment.yaml");

function delayMs() {
  try {
    const c = YAML.parse(fs.readFileSync(CONFIG, "utf8")) || {};
    return Number(c.downstream_delay_ms || 0);
  } catch {
    return 0;
  }
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

app.get("/charge", async (req, res) => {
  const t0 = Date.now();
  const d = delayMs();
  await sleep(d); // the real downstream latency
  const took = Date.now() - t0;
  if (took > 1000) {
    global.dtlog("ERROR", `payment charge slow: ${took}ms (downstream_delay_ms=${d})`, { "payment.latency_ms": took, "payment.delay_ms": d });
  }
  res.json({ ok: true, amount: 4200, latency_ms: took });
});

app.get("/healthz", (_req, res) => res.json({ ok: true, service: "payment-service", delay_ms: delayMs() }));

app.listen(PORT, () => global.dtlog("INFO", `payment-service listening on ${PORT} (delay=${delayMs()}ms)`));
