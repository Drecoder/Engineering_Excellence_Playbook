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

## 6. Reuse, Review Loop, and Routing

See `00_UniversalStandards/09_Reuse_and_DRY.md` and `06_AgentZone/01_Agent_Standards.md` §6–7.

| Goal | PromQL Query |
| :--- | :--- |
| **Duplication Trend** | `max by (repo) (code_duplication_ratio)` |
| **New Clones per Change** | `sum by (repo, kind) (increase(pr_new_clones_total[7d]))` |
| **Builder Reuse Hit Rate** | `sum(rate(reuse_hits_total[7d])) / sum(rate(builder_tasks_total[7d]))` |
| **Review Rounds (P90, target ≤ 3)** | `histogram_quantile(0.90, sum by (le) (rate(review_loop_rounds_bucket[7d])))` |
| **Changes Reaching the Round Cap** | `sum(increase(review_loop_rounds_count{outcome="round_cap"}[7d])) / sum(increase(review_loop_rounds_count[7d]))` |
| **Build Failures by Class** | `sum by (class) (increase(build_failures_total[1d]))` |
| **Fix Success by Rung** | `sum by (rung, error_class) (increase(fix_attempts_total{outcome="success"}[7d])) / sum by (rung, error_class) (increase(fix_attempts_total[7d]))` |
| **Findings Dropped (failed evidence check)** | `sum by (lens, reason) (increase(review_findings_dropped_total[7d]))` |
| **Complexity Conformance vs Sonar** | `sum by (language) (increase(complexity_conformance_mismatch_total[1d]))` (must be 0) |

## 7. Autonomy by Evidence

See `00_UniversalStandards/10_Autonomy_by_Evidence.md`. Long-term target: 3.4 DPMO (Six Sigma).

| Goal | PromQL Query |
| :--- | :--- |
| **Autonomy Level per Class** | `max by (process_class) (autonomy_level)` |
| **Defect Proportion per Class (p-chart input)** | `sum by (process_class) (increase(process_events_total{outcome="defect"}[1w])) / sum by (process_class) (increase(process_events_total[1w]))` |
| **Demonstrated Defect-Rate Bound** | `max by (process_class) (process_defect_rate_upper_bound)` |
| **DPMO Toward Six Sigma** | `max by (process_class) (process_dpmo_estimate)` (target 3.4) |
| **Out-of-Control Signals** | `sum by (process_class, rule) (increase(process_out_of_control_total[1w]))` |
| **Demotions** | `sum by (process_class, reason) (increase(autonomy_demotions_total[30d]))` |
| **Human Wait Share of Lead Time** | `sum by (process_class) (rate(human_wait_seconds_sum[1w])) / sum by (process_class) (rate(change_lead_time_seconds_sum[1w]))` |
| **Reviewer Agreement (Gage R&R analogue)** | `avg by (process_class) (reviewer_agreement_ratio)` |
