# Master Metric Index (PromQL)

Standardized queries for validating the **Flow Audit** across the platform.

## 1. RED Method (Request Health)

| Goal | PromQL Query |
| :--- | :--- |
| **Throughput (Rate)** | `sum(rate(http_requests_total[5m]))` |
| **Availability (Errors)** | `sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(http_requests_total[5m]))` |
| **Latency (P99)** | `histogram_quantile(0.99, sum by (le) (rate(http_request_duration_seconds_bucket[5m])))` |

## 2. USE Method (Substrate Health)

| Goal | PromQL Query |
| :--- | :--- |
| **CPU Utilization** | `1 - avg(rate(node_cpu_seconds_total{mode="idle"}[5m]))` |
| **Memory Utilization** | `1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)` |
| **Memory Saturation** | `rate(node_pressure_memory_waiting_seconds_total[5m])` (PSI: share of time tasks stall on memory) |
| **Network Errors** | `rate(node_network_receive_errs_total[5m])` |

## 3. Governor & Flow Metrics

| Goal | PromQL Query |
| :--- | :--- |
| **Concurrency Saturation** | `avg(governor_active_tasks / governor_max_limit)` |
| **Queue Jitter** | `histogram_quantile(0.99, sum by (le) (rate(governor_wait_duration_seconds_bucket[5m])))` |

## 4. Governance Guardrails

See `00_UniversalStandards/08_Governance_Guardrails.md` §9.

| Goal | PromQL Query |
| :--- | :--- |
| **Controls Enforced** | `sum(governance_controls_total{mode="enforce"}) / sum(governance_controls_total)` |
| **Dry-Run Violations** | `sum by (control) (increase(governance_dry_run_violations_total[1d]))` |
| **Active Exceptions** | `sum by (control) (governance_exceptions_active)` |
| **Drift Findings** | `increase(governance_drift_findings_total[1d])` |
| **Conformance Failures** | `sum by (control, cloud) (increase(governance_conformance_checks_total{result="fail"}[1d]))` (must be 0; `result="fail"` means `observed != expected`) |
| **Exception Expiry Latency (P99)** | `histogram_quantile(0.99, sum by (le, control) (rate(governance_exception_expiry_latency_seconds_bucket[30d])))` |

## 5. CI Health

Found missing in the 2026-10-21 incidents (sovereign-vpc-gcp `docs/incidents/`): every CI failure that day was found by a person looking.

| Goal | PromQL Query |
| :--- | :--- |
| **Runner Bootstrap Failures** | `sum by (pool) (increase(ci_runner_bootstrap_failures_total[15m])) > 0` |
| **Stuck Apply Jobs** | `max(ci_job_queue_age_seconds{workflow="apply"}) > 900` |
