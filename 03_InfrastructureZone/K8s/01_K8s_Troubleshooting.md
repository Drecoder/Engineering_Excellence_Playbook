# Kubernetes Production Troubleshooting Guide
*Operational flow for managing pods, services, nodes, and cluster edge cases.*

---

## 1️⃣ Philosophy

I manage Kubernetes clusters with a **flow-first approach**:

- Detect issues through observability and metrics
- Drill down systematically using anchors
- Identify root cause via YAML/config inspection
- Apply deterministic fixes
- Reobserve to validate resolution

This ensures reliability and repeatability without guessing.

---

## 2️⃣ Key Anchors & Drills

| Anchor | Drill / Mental Simulation | Key Focus |
|--------|--------------------------|-----------|
| `kubectl get pods` | Identify Pending, CrashLoopBackOff, Running | Pod status, cluster resources |
| `kubectl describe pod` | Check scheduler messages, events, node assignment | Reasoning: why pod is pending or crashing |
| `kubectl get svc` | Examine ClusterIP, NodePort, LoadBalancer | Service selectors, TargetPort, annotations |
| `kubectl get nodes` | Check taints, allocatable resources, preemptible nodes | Node readiness, capacity, labels |
| `kubectl get hpa` | Inspect autoscaling | Max/min replicas, metrics, pod readiness |
| `kubectl logs` | Check container logs | CrashLoopBackOff, imagePullBackOff, probes |

---

## 3️⃣ Probable Actions / Forks

| Anchor | Common Drill Actions |
|--------|-------------------|
| `kubectl get pods` | Pending → describe pod → get nodes → adjust resources → recheck pods |
| `kubectl describe pod` | Scheduler messages → adjust taints, affinity, hostPort, node selector |
| `kubectl get svc` | Selector mismatch → fix labels; TargetPort mismatch → fix YAML; NodePort range; NetworkPolicies |
| `kubectl get nodes` | Node NotReady → check kubelet logs; resource exhaustion → add nodes / adjust requests |
| `kubectl get hpa` | Scale issues → adjust min/max replicas; pod metrics missing → check metrics-server |
| `kubectl logs` | CrashLoopBackOff → check container spec, env vars, volumes, init containers, probes |

---

## 4️⃣ Edge Cases & Key Paths

| Scenario | Drill / Action | YAML / Path | Type |
|----------|----------------|------------|------|
| Node NotReady | ssh node → `systemctl status kubelet` → `journalctl -u kubelet` | /var/lib/kubelet/config.yaml | Node |
| Selector Mismatch | Compare service labels vs pod labels | Service + Pod YAML | Networking |
| NetworkPolicies | Pod running but curl times out → edit NetworkPolicy | NetworkPolicy YAML | Security / Networking |
| Static Pod Failure | Check `/etc/kubernetes/manifests/` | etcd.yaml, api-server.yaml | Pod / API |
| ETCD Backup | `ETCDCTL_API=3 etcdctl snapshot save` | /etc/kubernetes/pki/etcd/ | Cluster / Storage |
| TargetPort Confusion | Verify containerPort vs targetPort | Pod + Service YAML | Networking |
| CoreDNS Failure | Check kube-dns service + `/etc/resolv.conf` | Pod DNS config | Networking / DNS |

---

## 5️⃣ Drill Flow Sequences

| Sequence | Step / Anchor | Edge Case / YAML Path / Action |
|----------|---------------|--------------------------------|
| Pod Scheduling / Pending | `kubectl get pods` | Detect Pending / CrashLoopBackOff |
|  | `kubectl describe pod <pod>` | Scheduler events / node assignment |
|  | `kubectl get nodes` | Node NotReady → check kubelet logs |
|  | Adjust CPU / Memory | Static Pod Failure → fix manifests & restart static pods |
| Service Exposure / Connectivity | `kubectl get svc` | Selector Mismatch → Correct service selector |
|  | Check annotations / TargetPort | TargetPort Confusion → adjust containerPort / targetPort |
|  | `kubectl describe pod <pod>` | NetworkPolicies → Allow proper ingress/egress rules |
| Pod Crash / Container Issue | `kubectl logs <pod>` | CrashLoopBackOff → fix container spec / volumes / env / probes |
|  | `kubectl get pods` | CoreDNS Failure → Fix CoreDNS deployment / pod DNS config |

---

## 6️⃣ Frequency & Focus

- **High Frequency / High Focus:** Pod Scheduling, Service Connectivity, Node NotReady  
- **Medium Frequency:** HPA issues, CoreDNS, Static Pods, TargetPort mismatches  
- Use this guide as a **mental simulation map** before touching production

---

## 7️⃣ Principle

I don’t just fix pods — I **manage flow, prevent drift, and maintain deterministic cluster behavior**.  

This ensures that issues are caught, resolved, and documented in a repeatable way.