# Telemetry Standards (OpenTelemetry)

*Traces, metrics, and logs ship with the first line of code.*

The enforceable subset lives in `AGENTS.md` → **Observability Rules**. Query definitions live in
`metrics/promql/MASTER_INDEX.md`.

---

## 1️⃣ Philosophy

- Telemetry is part of the feature, not a follow-up task.
- Every signal must be **correlatable**: a log line links to its trace, a trace to its metrics.
- Names are contracts. Dashboards and alerts depend on them.

---

## 2️⃣ Bootstrap (Node / TypeScript)

- Use `@opentelemetry/sdk-node` with OTLP exporters for traces, metrics, and logs.
- Load telemetry **before** application code (e.g. `node --import ./telemetry.js`).
- Configure only through environment variables:

| Variable | Purpose |
| :--- | :--- |
| `OTEL_SERVICE_NAME` | Service / agent name (e.g. `builder`) |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | Collector endpoint |
| `OTEL_EXPORTER_OTLP_HEADERS` | Auth headers — injected from a secret store, never committed |
| `OTEL_RESOURCE_ATTRIBUTES` | e.g. `deployment.environment=dev,service.version=<git-sha>` |

- Shut the SDK down on `SIGTERM` so buffered telemetry is flushed.

---

## 3️⃣ Instrumentation Pattern

- Wrap operations with one shared helper (`traced(name, attrs, fn)`) that creates the span,
  records duration, counts errors, and sets span status. Business logic never builds spans by hand.
- Prefer auto-instrumentation for HTTP, gRPC, and database clients.

---

## 4️⃣ Naming

| Signal | Convention | Example |
| :--- | :--- | :--- |
| Span | `<kind> <name>` | `tool run_plan`, `llm.call` |
| Metric | `<service>.<area>.<measure>`, unit in metadata | `builder.tool.duration` (s) |
| Attribute | OTel semantic conventions first, then `<service>.*` | `gen_ai.request.model`, `builder.task_id` |

Avoid high-cardinality metric labels (task IDs, file paths, user IDs). Those belong on spans.

---

## 5️⃣ Required Signals

| Applies to | Signals |
| :--- | :--- |
| **Every service** | RED: request rate, error rate, duration histogram |
| **Every Governor** | `governor_active_tasks`, `governor_max_limit`, `governor_wait_duration_seconds` |
| **Every LLM call** | Span with `gen_ai.request.model`, `gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens`; token and cost counters |
| **Every agent** | Task outcome counter, attempts histogram, loop-iteration count, token budget used |
| **Every review loop** | Rounds per change, stall count, findings resolved per round (by fingerprint), cost per merged change |
| **Every Deployment Unit** | Creation time, teardown success, collector export failures |

---

## 6️⃣ Logs

- Structured JSON only (e.g. `pino`), with `trace_id` and `span_id` injected automatically.
- No secrets, tokens, or full prompts containing credentials in logs.

---

## 7️⃣ Pipeline: Local → Grafana Cloud

| Stage | Backend | How |
| :--- | :--- | :--- |
| **Local** | `grafana/otel-lgtm` container (Grafana, Tempo, Prometheus, Loki, collector) | App → OTLP gRPC `localhost:4317` |
| **Cloud** | Grafana Cloud | App → OTLP gRPC → collector (Grafana Alloy) → Grafana Cloud OTLP endpoint (HTTP) |

Switching stages changes environment variables and collector config only — never application code.

---

## 7️⃣a Decentralized Telemetry Stack

Across clouds, telemetry goes to an **independent observability Deployment Unit** that no workload
cloud owns:

- **The stack is its own DU**, launched by the platform like any other, in a dedicated account or
  neutral location (or a neutral SaaS).
- **Workloads never depend on it.** Every DU runs a local collector (OTel Collector / Grafana Alloy)
  that buffers and retries; if the stack is down, telemetry is delayed, not lost, and workloads
  keep running.
- **Outbound only.** DUs push OTLP; the stack never reaches into a DU. Each DU authenticates with
  its own identity so one DU cannot impersonate another.
- **Storage outlives compute.** Logs, metrics, and traces are kept in object storage, so ephemeral
  DUs — including an ephemeral stack — never take their history with them.
- **Cost controls at the edge.** Sampling, short retention, and dropping debug logs happen in the
  local collector, before cross-cloud egress is paid.
- **Agents report to the same stack**, so one trace and one dashboard cover infrastructure and the
  change loop that produced it.

---

## 8️⃣ Testing Telemetry

- Unit tests use an in-memory exporter to assert expected spans and attributes exist.
- Dashboards are committed as JSON (`dashboards/<service>.json`) and change in the same PR as
  the metrics they display.
- **Alerting and recording rules are linted** with pint against the playbook's policy
  (`metrics/promql/pint.hcl`; `AP-OBS-*` in `schemas/antipatterns.v1.json`): every alert has a
  `severity` (page or ticket), a `summary`, and a `runbook_url`, waits at least one minute (`for:`)
  before firing, and references only labels its query keeps; recording rules keep `job`.

---

## 9️⃣ Principle

If you cannot see it, you cannot operate it — and you cannot claim it is done.
