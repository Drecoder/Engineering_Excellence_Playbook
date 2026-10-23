# Network Fundamentals and Cloud Guardrails

*From the OSI model to organization policy: why each network guardrail exists, and why some of them
cannot be written as an access policy at all.*

This document is **explanatory**. It defines no policy: the normative controls are the `GOV-*`
guardrails in `00_UniversalStandards/08_Governance_Guardrails.md` and the `SEC-*` checks in
`00_UniversalStandards/07_Security_In_Depth.md`. Where this document and those disagree, they win.

---

## 1️⃣ From Fundamentals to Controls

Classic networking topics, as taught in engineering fundamentals courses, map directly onto the
platform's cloud controls:

| Fundamental | In the cloud | Platform control | Enforced by |
| :--- | :--- | :--- | :--- |
| **Layering (OSI, TCP/IP)** | L3/L4 isolation inside the network; L7 at the edge (load balancers, API gateways) | `GOV-003`: no VM directly reachable from the internet; ingress only through managed load balancers | Org policy (no external IPs, GCP); SCPs on public IPs, Elastic IPs, internet gateways (AWS) |
| **Addressing and subnetting** | Private subnets, Private Google Access, NAT for egress | Private-only subnets in the platform VPC; NAT only where a subnet needs egress | IaC review and plan-time checks; `GOV-001` removes unmanaged default networks |
| **Routing** | Hub-and-spoke, peering, transit gateways | `GOV-009`: no peering side channels; connectivity is owned by the platform network role | Org policy (GCP); SCP on peering (AWS) |
| **Port and protocol filtering** | Firewall rules, security groups, network ACLs | `GOV-014`: no management port open to the internet; the VPC's deny-all ingress and egress defaults | Plan-time `SEC-011`, then detective controls with remediation |
| **Name resolution (DNS)** | Cloud resolvers, private zones, resolver logging | `GOV-015`: DNS only through the approved resolvers | Network policy above the project or account |
| **Geography** | Regions and locations | `GOV-006`: resources only in approved regions | Org policy (GCP); SCP on the requested region (AWS) |

---

## 2️⃣ The Control Plane and the Data Plane

The most important distinction for choosing a mechanism:

- **The control plane** is the cloud's API: create a firewall rule, attach a gateway, launch a VM.
  Organization policies and SCPs act here. They decide whether an **API request** is allowed,
  using the request attributes the cloud exposes as **condition keys**.
- **The data plane** is the traffic itself: packets on ports between addresses. Firewalls,
  security groups, network policies, and resolvers act here.

An access policy never sees a packet. It also cannot read any part of a request the cloud does not
expose as a condition key. Two consequences follow, and both have caught real policies:

1. **"Deny SSH from the internet" cannot be an SCP.** A security-group rule's source CIDR and port
   are not condition keys on `AuthorizeSecurityGroupIngress`, so no SCP can tell a safe rule from an
   open one. A policy that appears to do so (for example with an invented condition operator) is
   rejected by AWS or, worse, authorizes nothing while looking correct. `GOV-014` therefore combines
   a plan-time check, a detective cloud control with automatic remediation, and `GOV-003`, which
   keeps the port unreachable in the first place.
2. **"Force DNS through the corporate resolver" is not an access-policy problem.** It is traffic,
   so it needs network policy on the data plane (`GOV-015`). Even that has a limit: DNS-over-HTTPS
   travels as ordinary HTTPS on port 443, indistinguishable at L4, so no port filter can stop it.
   Resolver filtering, such as Route 53 Resolver DNS Firewall, only sees queries actually sent to
   the resolver; it is not an egress firewall.

---

## 3️⃣ Defense in Depth for One Port

Port 22 shows how the layers stack, each assuming the one before it can fail:

| Layer | What stops an internet SSH connection | Fails when |
| :--- | :--- | :--- |
| **No public address** (`GOV-003`) | The VM has no internet-routable address, or no gateway route | A load balancer forwards the port, or a public IP slips through |
| **Deny-all ingress** (VPC default) | No rule allows the traffic | Someone adds an allow rule |
| **Plan-time check** (`SEC-011`) | The pull request adding an open rule fails | The rule is created outside the pipeline |
| **Detective control** (`GOV-014`) | The open rule is found and removed | During the remediation window |
| **Identity-based access** (`GOV-012`) | Interactive access requires IAM through OS Login, IAP, or Session Manager | Credentials are stolen |

No single layer is trusted alone, which is the platform's security principle applied to the network
(`00_UniversalStandards/07_Security_In_Depth.md`).

---

## 4️⃣ Rolling Out Network Guardrails

New network guardrails follow the governance rollout, not the module refactor framework (which is
for restructuring existing infrastructure code):

1. **Stage in dry run.** Organization policies support dry run directly. **SCPs do not have a dry-run
   or audit mode**: they are staged by attaching them to a test organizational unit first. Network
   policies are staged in log-only or alert-only mode where the product supports it.
2. **Prove it with a conformance test on both planes**: the prohibited configuration is rejected or
   removed, and the traffic is actually blocked, while the allowed path still works
   (`00_UniversalStandards/08_Governance_Guardrails.md` §5a).
3. **Handle exceptions** at the narrowest scope, with an owner and an expiry.
4. **Promote** to enforcement through a reviewed change to the baseline.

---

## Principle

Choose the mechanism by what it can see. Access policies see API requests, network policies see
packets, and detective controls see configuration after the fact. A control is written in the
mechanism that can actually express it, and its limits are stated, not hidden.
