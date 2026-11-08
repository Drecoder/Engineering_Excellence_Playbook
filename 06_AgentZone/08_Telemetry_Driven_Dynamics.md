# Telemetry-Driven Dynamics

*Telemetry is a control input, not only a record. An agent that can see itself can steer itself —
within bounds. An agent that cannot see itself cannot be dynamic, and there is no point building the
dynamic version blind.*

This standard builds on `02_BackendZone/04_Telemetry_Standards.md` (the signals), `04_CONCURRENCY
_GOVERNORS.md` (the first feedback primitive), `01_Agent_Standards.md` (actors read tool-emitted
telemetry), and `10_Autonomy_by_Evidence.md` (a process adapts on measured signals). The enforceable
subset belongs in `AGENTS.md` → **Observability Rules** and **Agent Rules**. Status: proposed.
`09_Adaptive_Harness.md` extends this loop with organizational knowledge, reliability states and the
Policy Engine's quality evidence, under the same bounds.

---

## 1️⃣ The Loop

A dynamic agent (e.g. a scan or test harness) runs a closed loop: **observe → decide → act →
observe.** Telemetry is the sensory half; the agent's judgment is the other half.

- The Governor already carries the primitive (`04` §2): it `observe()`s latency and 429s and raises
  `backoff()`. A dynamic agent **generalizes** this from one reaction (slow down) to many (reorder
  work, shed a dead-end path, lean into a high-signal one, climb or drop a model rung).
- The loop is only as good as the signal. Telemetry **ships with the first line** of the agent
  (`04_Telemetry_Standards` §1), because a blind loop cannot steer.

## 2️⃣ Emit *and* Read Back

Telemetry Standards §5 covers emit (spans, metrics, logs). A dynamic agent needs the other
direction too:

- **A read-back API** exposes the current derived state the agent steers on — per-target backoff,
  in-flight load, recent error rate — from the same shared store the Governor uses, at low latency.
- The read-back is **derived telemetry, not raw**: it returns decisions-ready values (a backoff in
  seconds, a saturation ratio), never a firehose the agent must re-reduce.
- Reading a signal never mutates it. Emit and read-back are separate paths over one store.

## 3️⃣ Dynamic Within Bounds (the guardrail)

Adaptation operates **strictly inside** the deterministic gates and Governor ceilings. This is the
line that keeps "dynamic" from meaning "unbounded."

- Telemetry-driven steering may change **where** the agent looks and **how gently** it acts. It may
  **never** change **whether** an action is permitted.
- It may **never** widen scope, unlock a capability, raise a per-target rate ceiling, or skip a
  required human review — whatever the signals say. Those come from the gate, not the sensor.
- **Fail-closed on signal, too.** A missing or stale signal is read as *no headroom*, never as
  permission to push. An agent that loses its telemetry slows or stops; it does not run free.

| The agent MAY adapt | The agent MAY NOT adapt |
| :--- | :--- |
| Crawl / test order and prioritization | Scope (in-scope assets) |
| Pacing **down**; longer backoff under stress | Capability grants (detection vs exploitation) |
| Shedding dead-end paths; retry budgets | The per-target rate ceiling (never up) |
| Model rung for a sub-task (`01` §6) | The human-review requirement for protected classes |

Steering is advisory to *where / how-much-gentler*, authoritative never. The gate and Governor stay
the only sources of *whether* and *how-hard-at-most*.

## 4️⃣ Steering Is Evidence

Every adaptation is itself telemetry, so the loop is auditable (`10` §9a, evidence-is-telemetry):

- Each steering decision is a **span attribute** recording the signal that caused it and the change
  made (`agent.steer.reason`, `agent.steer.from`, `agent.steer.to`). A dynamic agent whose changes
  are invisible is not observable and not done.
- Counters track how often the agent slowed, shed, or re-prioritized, so a loop that thrashes is
  visible, not silent.

## 5️⃣ Testing a Dynamic Agent

Beyond Telemetry Standards §8 (in-memory exporter asserts spans exist), a dynamic agent is tested on
both halves of the loop:

1. **Responsiveness:** injected signals (rising latency, a 429 burst, an error-only path) must
   produce the specified adaptation — asserted against the in-memory exporter and the read-back.
2. **Bound-respecting (adversarial):** signals crafted to *imply headroom* — low latency, zero
   errors, a stale "all clear" — must **not** cause the agent to cross any bound. Assert the per-
   target ceiling, scope, and capability limits hold under the most permissive signals the test can
   forge. A dynamic agent that speeds past its ceiling because the sensor said it was quiet has
   failed this test.

---

## Principle

Give an agent eyes and it can steer; keep the steering inside the gates and the Governor and it
steers without ever stepping out. Telemetry is what turns a fixed harness into a dynamic one — and
the reason a dynamic harness is safe to build at all.
