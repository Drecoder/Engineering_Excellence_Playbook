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