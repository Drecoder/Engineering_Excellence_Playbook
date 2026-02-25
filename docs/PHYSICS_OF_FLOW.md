# The Physics of Flow

This document explains the mathematical foundations of our **Definition of Done**.

## 1. Little’s Law ($L = \lambda W$)
We use Little's Law to determine our **Governor Limits**. 
* **L (Lead):** The number of concurrent tasks.
* **$\lambda$ (Lambda):** The arrival rate of requests.
* **W (Wait):** The average time spent in the system.

**Application:** If our P99 duration (W) is 200ms and our arrival rate ($\lambda$) is 50 req/sec, our Governor must be set to at least $L = 50 \times 0.2 = 10$ to prevent queuing.

## 2. Universal Scalability Law (USL)
The USL helps us identify why performance plateaus.
$$X(N) = \frac{\gamma N}{1 + \sigma(N - 1) + \kappa N(N - 1)}$$

* **$\sigma$ (Contention):** Serialization delay (waiting for a lock).
* **$\kappa$ (Coherency):** The cost of keeping data consistent across workers.

**Application:** We monitor the "Knee of the Curve" to set our **-1σ buffer**, ensuring we shed load before Contention and Coherency delay cause non-linear latency spikes.



## 3. The -1σ Invariant
We do not alert at 100% capacity. We alert at the point of **Resonance Friction**.
* **Standard:** Identify the saturation point (Knee) and set the threshold one standard deviation ($\sigma$) below it.
* **Result:** We maintain a deterministic "Quiet Substrate."