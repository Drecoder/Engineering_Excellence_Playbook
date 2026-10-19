# Deliverable Lifecycle
*One lifecycle for every deliverable: Terraform modules, APIs, frontend features, pipelines,
monitoring rules, and agents.*

**Design → Build → Validate → Deploy → Observe → Improve**

Each stage has an entry gate (what must be true to start), core activities, and an exit gate
(what must be true to move on). A stage that fails its exit gate is **Red** — it does not
advance (see `05_Metadata/RedGreen_Logic.md`).

---

## 1. Design

| Entry gate | Activities | Exit gate |
| :--- | :--- | :--- |
| Problem and owner identified | Define contracts (API schema, module inputs/outputs, JSON schemas); identify cross-layer impact; weigh trade-offs (`Two_Sides_of_the_Coin.md`); define SLOs and the telemetry the change will emit | Contracts and SLOs written down and reviewed |

## 2. Build

| Entry gate | Activities | Exit gate |
| :--- | :--- | :--- |
| Design exit gate met | Implement with telemetry from the first commit; keep structural and behavioral changes in separate PRs; bound all concurrency with a Governor (`04_CONCURRENCY_GOVERNORS.md`) | Local validation commands in `CLAUDE.md` pass |

## 3. Validate

| Entry gate | Activities | Exit gate |
| :--- | :--- | :--- |
| Build exit gate met | Unit, integration, and contract tests; `terragrunt plan` reviewed (no unexplained deletes/replaces); `tflint` / `checkov`; rollback path confirmed | PR approved; plan and test evidence attached |

## 4. Deploy

| Entry gate | Activities | Exit gate |
| :--- | :--- | :--- |
| Validate exit gate met | Deploy only through CI/CD with federated identity; `apply` runs post-merge, never by hand | Deployed state matches the reviewed plan; no drift |

## 5. Observe

| Entry gate | Activities | Exit gate |
| :--- | :--- | :--- |
| Deployed | Watch RED/USE signals and SLO burn rate; verify dashboards and alerts reflect the change (`02_Monitoring_Alert_Thresholds.md`) | Signals within SLO for the agreed soak period |

## 6. Improve

| Entry gate | Activities | Exit gate |
| :--- | :--- | :--- |
| Observation data or an incident | Post-mortems (`03_Post_Mortem_Template.md`); tune thresholds; update standards via PR | Learnings merged into the playbook |

---

## Documentation as Infrastructure

If it affects production behavior, it belongs in version control. Standards live in Git, evolve
through Pull Requests, and may be published to Confluence automatically (e.g., an `md2conf`
GitHub Action) so the docs never drift from the repo.

The work is complete when it meets the [Definition of Done](02_Definition_of_Done.md).
