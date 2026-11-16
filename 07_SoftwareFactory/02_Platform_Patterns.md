# Platform Patterns: DataOps, FinOps, MLOps and SecOps (Proposed)

*Status: proposed. Nothing on this page is built. Each pattern is built by a run of the software
factory after the factory reaches its MVP, and stays proposed until that run's MVP is merged and
verified.*

The software factory builds platforms. Four patterns attach to any platform it builds, the factory
itself first:

- **DataOps:** the shared pipe every other pattern reads from.
- **FinOps:** what the platform costs, and the budgets that gate it.
- **MLOps:** what the platform has learned, from its CAPA record.
- **SecOps:** how security events are investigated, remediated and verified.

A pattern is not a platform of its own. It is written once and attached to a host platform through
a versioned contract, the way the central CI is written once and called by every repository
(`00_UniversalStandards/15_Central_CI.md`).

---

## 1️⃣ The Attachment Model

```text
 host platforms ──► DataOps pipe ──► Gold ──┬──► FinOps ─────► budgets and tag rules (gates)
 (the factory,      ingest · validate ·      ├──► MLOps ──────► retrieval context
  the pentest       normalize · resolve IDs  └──► SecOps ─────► investigation, remediation, verification
  platform, …)      Bronze → Silver → Gold
```

- **Logic once, host injected.** A pattern's logic lives in one place. What changes per host is
  injected: the host's identity, its event sources, and its configuration. Attaching a pattern to a
  new platform is configuration, not a rebuild.
- **One versioned contract per pattern.** Each pattern names what a host sends it and what it sends
  back, as schemas in `schemas/`, evolved by version, never by edit
  (`00_UniversalStandards/09_Reuse_and_DRY.md`).
- **The rules travel with the pattern.** A pattern brings its constraints to every host. SecOps
  remediation stays at L2 on every platform it attaches to.
- **A pattern proves reuse on its second host.** The first attachment proves the contract works;
  the second proves the pattern is a pattern.

## 2️⃣ DataOps: the Shared Pipe

DataOps carries the information every other pattern uses. No pattern builds its own ingestion.

| Stage | What it does |
| :--- | :--- |
| Ingest | Receives host records: spend and usage, CAPA records, security events |
| Validate | Checks each record against its versioned contract; an invalid record is rejected, never repaired, and dead-lettered |
| Normalize | Brings records to one shape per type |
| Resolve | Resolves identifiers across sources (run, ticket, repository, workspace, account) and extracts entities and relationships |
| Land | Writes the Medallion layers: Bronze as received, Silver validated and normalized, Gold curated for the patterns |

Patterns read Gold only. The pipe is the trust boundary at the door: what fails validation never
reaches a pattern. Payloads larger than a message travel by claim check, with the consumer verifying
the SHA-256 before use (`02_BackendZone/05_Application_Architecture.md`).

## 3️⃣ FinOps

Cost telemetry, workload optimization and closed-loop control, on a lakehouse.

| Layer | What it does |
| :--- | :--- |
| Inform | Attributes every unit of spend to an owner: billing and usage tables (FOCUS-aligned) joined on shared identifiers, cloud billing exports, mandatory cost-attribution tags |
| Optimize | Right-sizes compute and storage, and finds idle and unattributed spend |
| Operate and control | Budgets and tag rules become gates; an overrun stops new spend for the owner to decide |

**Attached to the factory:** per-ticket spend from the token ledger (`token_record.v1`, priced by a
versioned table) and the cloud spend of both clouds flow in; per-ticket budgets and the rule that
compute runs only when called (`03_InfrastructureZone/05_Cost.md`) come back as gates. The FinOps
compute itself is serverless, so it costs nothing when no query runs.

## 4️⃣ MLOps: CAPA to Institutional Learning

Turns what the platform has learned into context its agents and people can retrieve.

1. **Operations** produce incidents, changes, decisions, costs and outcomes.
2. **The CAPA journal and register** hold them as canonical, versioned records: problem, root cause,
   correction, preventive action, evidence and outcome (`docs/POC_JOURNAL.md`,
   `findings_register.v2`).
3. **DataOps** ingests, validates and resolves them.
4. **A knowledge graph and a vector index** hold the records and their relationships, and their
   semantic similarity.
5. **Retrieval** returns context with its source records.

It builds on what the playbook already proposes and does not replace it
(`06_AgentZone/10_CAPA_Graph_and_Risk_Weighted_Learning.md`): similarity finds candidates but never
establishes trust, risk weights steer nothing until calibrated, and fine-tuning stays closed until it
is decided as a protected change. At its MVP, "learning" means retrieval only.

**Attached to the factory:** the factory's own journal and register are the first source; FinOps
outcomes are the second.

## 5️⃣ SecOps: Agentic Incident Response

A cloud-portable pattern for investigating, remediating and verifying security events.

| Stage | What it does |
| :--- | :--- |
| Detect | Security findings and alerts become events (AWS: GuardDuty and CloudWatch to EventBridge; GCP: Security Command Center to Pub/Sub) |
| Contextualize | Enriches the event from DataOps Gold and MLOps retrieval |
| Decide | Proposes a response; a model proposes within a deterministic decision table, never outside it |
| Execute | Carries out an approved response with a scoped identity |
| Verify | Confirms the response worked, from evidence the pattern did not produce |

**Constraints on every host:**

- Remediation is a protected class (security) and **never exceeds L2**: a person approves every
  remediating action (`00_UniversalStandards/10_Autonomy_by_Evidence.md`).
- A responder authorizes from a signed grant, never from the event or message it received.
- Tokens are signed by a key the responder does not hold, scoped to one action, and consumed once.
- Human approvals are signed records from an authenticated identity, bound to the content they
  approve.

These four come from executed failure cases against the pentest platform (2026-11-12): authority
taken from an unsigned message, an unscoped and reusable token minted by its own verifier, and an
approval anyone could edit.

**Attached to:** the software factory first, then the pentest platform.

## 6️⃣ The Factory Runs

Each pattern is built as a run of the software factory, at the MVP stage: approved specs on the
board, acceptance tests written first, the central gates, the owner's approved merges, and a metered
budget per ticket.

| Run | Builds | Attaches to | Depends on |
| :--- | :--- | :--- | :--- |
| 0 | The factory's own MVP: one real ticket built, gated, approved, merged, within budget | (the factory) | |
| 1 | DataOps pipe, then FinOps | the factory | Run 0 |
| 2 | MLOps: CAPA to institutional learning | the factory | Run 1 (the pipe) |
| 3 | SecOps | the factory | Run 2 (context), Run 1 (cost) |
| 4 | The pentest platform, through the factory, with SecOps attached | its own host | Run 3 (the signed-grant and token work is reused) |

A run that cannot meet the playbook is not built, and no run starts before the one it depends on
reaches its MVP.

---

## Principle

Build a capability once, attach it everywhere. Patterns are written once and injected into each
platform the factory builds, so every platform inherits the same cost control, learning and
security response, under the same rules.
