# Agnostic Concurrency Governors

To ensure **Deterministic Flow**, no service shall execute unbounded parallel tasks. Every runtime must implement a "Governor" to manage the execution substrate.

## 1. Implementation by Runtime

Regardless of the language, the **Governor** maintains a fixed bound on active work to prevent substrate saturation.

| Runtime | Execution Unit | Governor Mechanism |
| :--- | :--- | :--- |
| **Node.js** | Worker Threads / Promises | Worker Pools (e.g., Piscina) or Promise Limiters (p-limit) |
| **Go** | Goroutines | Buffered Channels or Weighted Semaphores |
| **Python** | Asyncio Tasks / Processes | `asyncio.Semaphore` or ProcessPoolExecutor |

## 2. The Governor Logic (Agnostic)

Every Governor must respect **Little’s Law ($L = \lambda W$)**.

* If the arrival rate ($\lambda$) exceeds the Governor's capacity, the system must provide **Backpressure** (Rate Limiting).
* If the wait time ($W$) exceeds the P99 threshold, the task must be shed (Timeout/Cancellation).

## 3. Standardized Semantics for Workers

1. **Bounded:** Max concurrency must be a configurable constant based on CPU/Memory substrate.
2. **Context-Aware:** Every worker must respect a `timeout` or `abort_signal` to prevent "Zombie Execution."
3. **Observable:** Every worker must increment `governor_active_tasks` on start and decrement on completion.
