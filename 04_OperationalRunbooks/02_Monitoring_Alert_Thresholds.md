# Monitoring & Alert Thresholds
*Guidelines for defining metrics, thresholds, and alerting policies.*

---

## 1️⃣ Philosophy

I monitor the platform as **flow observability**, not just metrics collection:

- Metrics reflect real service behavior and SLA impact  
- Alerts are actionable, not noise  
- Dashboards provide context across frontend, backend, and infra  

---

## 2️⃣ Key Metrics

| Layer | Metric | Threshold / Notes |
|-------|--------|-----------------|
| **Infrastructure** | CPU, memory, disk I/O | Alert at 80% usage sustained for 5 min |
| **Kubernetes** | Pod restarts, pending pods, node NotReady | Alert on any CrashLoopBackOff or Node NotReady |
| **Backend** | API latency, error rate, DB connections | Alert if 95th percentile latency exceeds SLA or errors spike |
| **Frontend** | Page load time, JS errors | Alert if load exceeds threshold or errors > X per minute |
| **Async / Queues** | Queue depth, processing time | Alert if backlog exceeds SLA thresholds |

---

## 3️⃣ Alerting Workflow

1. **Define Thresholds** → Set actionable, measurable limits  
2. **Configure Alerts** → PagerDuty, Slack, email, or dashboard notifications  
3. **Incident Triage** → Use drill flows (e.g., K8s troubleshooting, async processing)  
4. **Refine Thresholds** → After incident post-mortems, adjust thresholds to reduce noise  

---

## 4️⃣ Principle

I treat monitoring as **operational visibility flow** — alerts guide deterministic actions, prevent outages, and provide continuous learning.