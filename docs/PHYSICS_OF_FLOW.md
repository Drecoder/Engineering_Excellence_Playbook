# The Physics of Flow

This document explains the mathematical foundations of our **Definition of Done**.

**Notation:** σ always means *standard deviation* in this playbook. USL coefficients use
α / β / γ (Gunther's current notation) so the symbols never collide.

## 1. Little’s Law ($L = \lambda W$)
We use Little's Law to determine our **Governor Limits**.
* **L:** The average number of items in the system (in flight or queued).
* **$\lambda$ (Lambda):** The arrival rate of requests.
* **W:** The mean residence time (wait + service) in the system.

Little's Law holds for **means**. For sizing we deliberately substitute the **P99** duration
for W: this over-provisions the Governor so that slow requests do not cause queuing.

**Application:** If our P99 duration is 200ms and our arrival rate ($\lambda$) is 50 req/sec, our
Governor must be set to at least $L = 50 \times 0.2 = 10$ to prevent queuing.

## 2. Universal Scalability Law (USL)
The USL helps us identify why performance plateaus.
$$X(N) = \frac{\gamma N}{1 + \alpha(N - 1) + \beta N(N - 1)}$$

* **$\gamma$ (Concurrency):** Throughput of a single worker ($N = 1$).
* **$\alpha$ (Contention):** Serialization delay (waiting for a lock or shared resource).
* **$\beta$ (Coherency):** The cost of keeping data consistent across workers (crosstalk).

Throughput peaks at $N^* = \sqrt{(1 - \alpha) / \beta}$. Beyond $N^*$, adding workers *reduces*
throughput (retrograde scaling).

**Application:** We fit α and β from load tests and monitor the "Knee of the Curve" to set our
**−1σ buffer**, ensuring we shed load before contention and coherency delay cause non-linear
latency spikes.

## 3. The −1σ Invariant
We do not alert at 100% capacity. We alert at the point of **Resonance Friction**.
* **Knee:** The saturation point measured by load testing (where latency departs from linear).
* **σ:** The standard deviation of the knee across repeated load-test runs.
* **Standard:** Set the saturation threshold at **knee − 1σ**.
* **Result:** We maintain a deterministic "Quiet Substrate." Alert routing for this threshold is
  defined in `04_OperationalRunbooks/02_Monitoring_Alert_Thresholds.md`.
