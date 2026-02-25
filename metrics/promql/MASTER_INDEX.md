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
| **Memory Saturation** | `node_memory_Active_bytes / node_memory_MemTotal_bytes` |
| **I/O Errors** | `rate(node_network_receive_errs_total[5m])` |

## 3. Governor & Flow Metrics
| Goal | PromQL Query |
| :--- | :--- |
| **Concurrency Saturation** | `avg(governor_active_tasks) / avg(governor_max_limit)` |
| **Queue Jitter** | `histogram_quantile(0.99, rate(governor_wait_duration_seconds_bucket[5m]))` |