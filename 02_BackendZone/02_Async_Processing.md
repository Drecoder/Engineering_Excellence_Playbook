# Asynchronous Processing Guidelines
*Managing backend async workflows with determinism, observability, and cross-layer flow.*

---

## 1️⃣ Philosophy

I design asynchronous workflows to ensure:

- **Deterministic outcomes** despite eventual consistency  
- Observability and traceability across services  
- Fault-tolerant retries and error handling  
- Lifecycle alignment with upstream (frontend) and downstream (infra) dependencies  

---

## 2️⃣ Common Patterns

- **Message Queues:** Pub/Sub, RabbitMQ, Kafka  
- **Background Jobs / Workers:** Node.js queues, Celery, serverless functions  
- **Event-Driven Workflows:** Triggered by DB changes, API calls, or infra events  
- **Retry / Dead Letter Queues:** Capture failed jobs for inspection and reprocessing  

---

## 3️⃣ Lifecycle Flow

1. **Submission / Trigger**  
   - Input validated and queued  
2. **Processing / Execution**  
   - Workers consume messages asynchronously  
   - Observability hooks (metrics, logs) enabled  
3. **Retry / Error Handling**  
   - Automatic retries for transient failures  
   - Failed messages pushed to dead-letter queues  
4. **Completion / Notification**  
   - Signal downstream systems or frontend  
   - Mark job as complete, log final state  

---

## 3️⃣a Idempotency & Safe Retries

Retries and at-least-once delivery mean every consumer **will** see duplicates. Handlers must be
safe to run more than once.

- **Idempotency key on every message / webhook.** Use the producer's event ID (e.g. GitHub
  `X-GitHub-Delivery`) or a deterministic hash of the payload — never a value generated on receipt.
- **Dedup store.** Record processed keys with a TTL at least as long as the producer's retry
  window. Check-and-record atomically (conditional write / unique constraint), not read-then-write.
- **Side effects keyed too.** Outbound effects (opening a PR, writing a file, calling an API)
  carry the same key so a replay finds the existing result instead of creating a second one.
- **Verify before dedup.** Authenticate the message (e.g. HMAC signature) before recording its
  key, so forged messages cannot poison the dedup store.
- **Retry policy.** Exponential backoff with jitter, a max attempt count, then the dead-letter
  queue. Only transient errors are retried; validation errors go straight to the DLQ.

---

## 4️⃣ Observability & Monitoring

- Track queue depth, processing latency, and failure rates  
- Ensure alerts trigger on stuck or backlogged messages  
- Maintain logs with contextual IDs for tracing across services  

---

## 5️⃣ Cross-Layer Coordination

- Frontend: Confirm UI feedback aligns with async processing delays  
- Infrastructure: Ensure message brokers and queues are highly available  
- Database: Avoid race conditions or double writes during async processing  

---

## 6️⃣ Principle

I treat async processing as a **flow**: from submission to completion, observable and recoverable at every stage.