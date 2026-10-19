# Monitoring & Alert Thresholds
*Guidelines for defining metrics, thresholds, and alerting policies.*

---

## 1️⃣ Philosophy

I monitor the platform as **flow observability**, not just metrics collection:

- Metrics reflect real service behavior and SLA impact  
- Alerts are actionable, not noise  
- Dashboards provide context across frontend, backend, and infra  

---

## 2️⃣ Alerting Policy (Least Noise)

Three rules decide whether a signal pages, opens a ticket, or only appears on a dashboard:

1. **Page on symptoms, not causes.** User-facing pages come from **SLO burn rate** (multi-window),
   not from resource usage.
2. **Saturation alerts use the −1σ invariant.** Once a service's saturation knee is measured by
   load testing, saturation alerts fire at **knee − 1σ** (see `docs/PHYSICS_OF_FLOW.md`).
3. **Utilization never pages.** CPU / memory / disk utilization (e.g. 80%) is a dashboard and
   capacity-planning signal only. A service without a measured knee is covered by its burn-rate
   alerts until the knee is measured.

| Severity | Condition | Route |
| :--- | :--- | :--- |
| **Page** | Error-budget burn ≥ 14.4× over 1h **and** 5m | On-call |
| **Ticket** | Error-budget burn ≥ 6× over 6h **and** 30m; saturation ≥ knee − 1σ for 15m | Team queue |
| **Dashboard** | Utilization, restarts, single-window spikes | No notification |

---

## 3️⃣ Key Metrics

| Layer | Metric | Threshold / Notes |
|-------|--------|-----------------|
| **Infrastructure** | Saturation (PSI, governor ratio) | Ticket at knee − 1σ sustained 15m; utilization is dashboard-only |
| **Kubernetes** | CrashLoopBackOff, node NotReady | Ticket if sustained > 15m; page only via the affected service's burn rate |
| **Backend** | P99 latency, error ratio | SLO burn-rate alerts (page / ticket per policy above) |
| **Frontend** | Core Web Vitals, JS error ratio | SLO burn-rate alerts against the frontend SLO |
| **Async / Queues** | Queue age (oldest message), DLQ depth | Ticket when oldest message age exceeds the processing SLO; any DLQ growth is a ticket |

---

## 4️⃣ Alerting Workflow

1. **Define SLOs** → Each service declares its availability and latency SLOs  
2. **Measure the Knee** → Load-test to find saturation; set saturation alerts at knee − 1σ  
3. **Configure Routes** → Page / ticket / dashboard per the policy above  
4. **Incident Triage** → Use drill flows (e.g., K8s troubleshooting, async processing)  
5. **Refine** → Every page that needed no action is a post-mortem item: demote it or fix the threshold  

---

## 5️⃣ Principle

I treat monitoring as **operational visibility flow** — alerts guide deterministic actions, prevent outages, and provide continuous learning.