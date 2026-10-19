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
