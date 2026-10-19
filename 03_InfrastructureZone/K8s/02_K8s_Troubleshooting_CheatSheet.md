# Kubernetes Production Troubleshooting Cheat Sheet

*Quick reference for anchors, drills, and frequency.*

| Anchor / Step | Drill / Mental Simulation | Frequency | Key Focus | Notes |
|---------------|-------------------------|-----------|-----------|-------|
| `kubectl get pods` | Identify Pending, CrashLoopBackOff, Running | High | Pod status, resource availability | Start of most drills |
| `kubectl describe pod <pod>` | Check scheduler messages, node assignment | High | Understand why pods pending/crashing | Use with get pods |
| `kubectl get nodes` | Check taints, allocatable resources, readiness | High | Node health, capacity | Combine with describe pod for scheduling issues |
| Adjust CPU / Memory | Fix resource requests / limits | High | Pod scheduling, static pod failures | Always recheck pods after adjustment |
| `kubectl get svc` | Examine ClusterIP, NodePort, LoadBalancer | High | Service exposure, selector correctness | Check labels, annotations, targetPort |
| Check TargetPort / containerPort | Verify alignment | Medium | Service connectivity | TargetPort mismatch is common edge case |
| `kubectl describe pod <pod>` | Check NetworkPolicies | High | Connectivity issues | Fix ingress/egress rules |
| `kubectl logs <pod>` | Inspect container logs | Medium | CrashLoopBackOff, imagePullBackOff | Check init containers, env vars, probes |
| `kubectl get hpa` | Inspect autoscaling | Medium | Min/max replicas, metrics | Ensure metrics-server is running |
| CoreDNS / Pod DNS | Check kube-dns + `/etc/resolv.conf` | Medium | DNS resolution | Fix CoreDNS deployment if necessary |
| Static Pod Failure | Check `/etc/kubernetes/manifests/` | Medium | etcd, API server | Restart static pods after manifest fixes |
| ETCD Backup | `ETCDCTL_API=3 etcdctl snapshot save` | Medium | Cluster storage | Always verify snapshot integrity |

---

## How to Use

1. Start with the **Anchor** column — the first `kubectl` command or action.  
2. Follow the **Drill / Mental Simulation** column to investigate.  
3. Note **Frequency** to prioritize daily, weekly, or incident response drills.  
4. Use **Key Focus** to check the most common causes quickly.  
5. Add **Notes** for edge cases, YAML paths, or escalation points.  

---

## Principle

This cheat sheet is not exhaustive — it’s a **mental simulation map**.  
I follow it to **flow systematically through issues**, ensuring deterministic resolution and operational visibility.
