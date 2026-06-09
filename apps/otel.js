// Shared OpenTelemetry bootstrap for the demo services. Required via `node -r ./otel.js`.
// Exports REAL traces + metrics + logs to the Dynatrace tenant over OTLP/HTTP-protobuf, so a
// real regression in these services becomes real telemetry in Grail (no seed scripts).
//
// Env:
//   OTEL_SERVICE_NAME            e.g. payment-service
//   DT_OTLP_ENDPOINT             https://<tenant>.live.dynatrace.com/api/v2/otlp
//   DT_OTLP_TOKEN                a dt0c01 token with openTelemetryTrace.ingest / metrics.ingest / logs.ingest
//                                (logs work today; traces/metrics activate once the scoped token is provisioned)
"use strict";

if (process.env.OTEL_DEBUG) {
  const { diag, DiagConsoleLogger, DiagLogLevel } = require("@opentelemetry/api");
  diag.setLogger(new DiagConsoleLogger(), DiagLogLevel.DEBUG);
}
const { NodeSDK } = require("@opentelemetry/sdk-node");
const { getNodeAutoInstrumentations } = require("@opentelemetry/auto-instrumentations-node");
const { Resource } = require("@opentelemetry/resources");
const { OTLPTraceExporter } = require("@opentelemetry/exporter-trace-otlp-proto");
const { OTLPMetricExporter } = require("@opentelemetry/exporter-metrics-otlp-proto");
const { PeriodicExportingMetricReader } = require("@opentelemetry/sdk-metrics");
const { OTLPLogExporter } = require("@opentelemetry/exporter-logs-otlp-proto");
const { LoggerProvider, SimpleLogRecordProcessor } = require("@opentelemetry/sdk-logs");
const logsAPI = require("@opentelemetry/api-logs");

const SERVICE = process.env.OTEL_SERVICE_NAME || "unknown-service";
const ENDPOINT = (process.env.DT_OTLP_ENDPOINT || "").replace(/\/$/, "");
const TOKEN = process.env.DT_OTLP_TOKEN || "";
const HEADERS = { Authorization: `Api-Token ${TOKEN}` };

const resource = new Resource({
  "service.name": SERVICE,
  "app": "checkout-demo", // single tag the Dynatrace Workflow filters the demo on
  "deployment.environment": "demo",
});

// --- traces + metrics via the Node SDK (auto-instruments express + http) ---
// Gated on DT_TRACES: trace/metric ingest needs openTelemetryTrace.ingest + metrics.ingest scopes
// (not on our token yet). Left ON without them, the exporters 403 (metrics) and fall back to
// localhost:4318 (traces) — retry storms that starve the LOGS export, which is the one that works
// today and that the recovery proof / Detective evidence DQL back out of Grail. So: logs always,
// traces+metrics only once a scoped token is set (DT_TRACES=1).
const TRACES_ON = !!ENDPOINT && !!process.env.DT_TRACES;
let sdk;
if (TRACES_ON) {
  sdk = new NodeSDK({
    resource,
    traceExporter: new OTLPTraceExporter({ url: `${ENDPOINT}/v1/traces`, headers: HEADERS }),
    metricReader: new PeriodicExportingMetricReader({
      exporter: new OTLPMetricExporter({ url: `${ENDPOINT}/v1/metrics`, headers: HEADERS }),
      exportIntervalMillis: 15000,
    }),
    instrumentations: [getNodeAutoInstrumentations({
      "@opentelemetry/instrumentation-fs": { enabled: false },
      // Do NOT instrument our own outgoing calls to Dynatrace (OTLP trace/metric/log export +
      // any ingest). Instrumenting the exporters' requests creates span/connection feedback that
      // silently starves the SimpleLogRecordProcessor's log export when traces are on.
      "@opentelemetry/instrumentation-http": {
        ignoreOutgoingRequestHook: (opts) => {
          const h = (opts && (opts.hostname || opts.host)) || "";
          return h.includes("dynatrace.com");
        },
      },
    })],
  });
  sdk.start();
}

// --- logs via the CLASSIC log ingest API, decoupled from the OTel SDK ---
// The Node OTel SDK's trace/metric exporters silently starve the OTLP log exporter when traces are
// on (no error — logs just stop reaching Grail). So we ship logs over a plain HTTPS POST to
// /api/v2/logs/ingest instead: independent of the SDK, reliable whether or not DT_TRACES is set.
// These land in Grail under `service.name` (what the Detective evidence, recovery proof, and the
// log-event -> Davis-problem rule all key off). Outgoing calls to dynatrace.com are excluded from
// http instrumentation above, so this POST isn't self-instrumented.
const https = require("https");
const LOGS_INGEST = ENDPOINT ? ENDPOINT.replace(/\/otlp$/, "/logs/ingest") : "";
let _logBuf = [];
function _flushLogs() {
  if (!LOGS_INGEST || _logBuf.length === 0) return;
  const batch = _logBuf; _logBuf = [];
  const payload = Buffer.from(JSON.stringify(batch));
  const u = new URL(LOGS_INGEST);
  const req = https.request(
    { hostname: u.hostname, path: u.pathname, method: "POST",
      headers: { Authorization: `Api-Token ${TOKEN}`, "Content-Type": "application/json; charset=utf-8",
                 "Content-Length": payload.length } },
    (r) => r.resume(),
  );
  req.on("error", () => {});
  req.write(payload);
  req.end();
}
if (LOGS_INGEST) setInterval(_flushLogs, 2000).unref();

// Tiny helper the services use to emit structured, Grail-queryable log lines.
global.dtlog = (severity, body, attributes = {}) => {
  _logBuf.push({ content: body, "service.name": SERVICE, "log.source": SERVICE,
                 loglevel: severity, severity, timestamp: Date.now(), ...attributes });
  if (_logBuf.length >= 50) _flushLogs();
  console.log(`[${SERVICE}] ${severity} ${body}`);
};

process.on("SIGTERM", async () => { try { _flushLogs(); if (sdk) await sdk.shutdown(); } catch {} process.exit(0); });
