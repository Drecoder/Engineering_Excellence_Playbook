# The RED Method

Derived from the Google SRE "Four Golden Signals," the RED Method measures the health of the request flow through a service.

| Metric | Academic Root | Agnostic PromQL Implementation |
| :--- | :--- | :--- |
| **Rate** | Arrival Rate ($\lambda$) | `sum(rate(http_requests_total[5m]))` |
| **Errors** | Failure Probability | `sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(http_requests_total[5m]))` |
| **Duration** | Residence Time ($W$) | `histogram_quantile(0.99, sum by (le) (rate(http_request_duration_seconds_bucket[5m])))` |



### The Physics Connection
By monitoring the relationship between **Rate** and **Duration**, we apply **Little's Law** to ensure our Concurrency Governors are sized correctly. If Duration spikes while Rate is constant, we are experiencing **Coherency Delay**.