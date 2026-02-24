# Definition of Done (DoD)
*Establishing clear, cross-layer criteria for completing work.*

---

## 1️⃣ Philosophy

I define “done” not as code pushed, but as **work that is complete, observable, tested, and aligned across layers**:

- Fully implemented and peer-reviewed  
- Observable and monitored in production  
- Documented in code and operational standards  
- Tested at unit, integration, and contract levels  
- Cross-layer impact considered (frontend, backend, infra, async, DB)  

---

## 2️⃣ Criteria Checklist

| Layer | DoD Criteria |
|-------|-------------|
| **Code** | Code meets style, linting, and coverage standards; passes all automated tests |
| **Infrastructure** | Resources managed as code; deployed via CI/CD; drift minimized |
| **Backend** | APIs meet contract, async flows validated, database interactions safe |
| **Frontend** | UI/UX matches design; interacts correctly with APIs; error states handled |
| **Observability** | Logs, metrics, alerts in place; dashboards updated |
| **Documentation** | Markdown or Confluence updated with clear instructions, diagrams, references |
| **Operational Readiness** | Rollback procedures confirmed; failover or retry flows tested |
| **Security / IAM** | Access follows least privilege; secrets and keys managed securely |

---

## 3️⃣ Principle

Work is **only done when it can be reliably operated, observed, and extended**.  

Pushing code is **not enough** — completeness requires cross-layer verification and operational readiness.