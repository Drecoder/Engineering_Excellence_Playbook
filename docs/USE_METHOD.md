# The USE Method

The USE Method is used to identify bottlenecks in the substrate (CPU, Memory, Network) before they impact the application layer.

| Metric | Academic Root | Agnostic PromQL Implementation |
| :--- | :--- | :--- |
| **Utilization** | Service Time / Capacity | `1 - avg(rate(node_cpu_seconds_total{mode="idle"}[5m]))` |
| **Saturation** | Queue Depth ($L$) | `node_load1` OR `avg(governor_active_tasks / governor_max_limit)` |
| **Errors** | Hardware/VPC Faults | `rate(node_network_receive_errs_total[5m])` |



### The -1σ Invariant
We use **Saturation** as our primary alert trigger. We aim to keep the system operating at one standard deviation (-1σ) below the point of queue resonance to maintain deterministic performance.