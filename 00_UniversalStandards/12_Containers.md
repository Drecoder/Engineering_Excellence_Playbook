# Containers

*How work runs (in pinned containers, the same image everywhere), how images are built, and how
they are secured.*

The enforceable subset is in `AGENTS.md` → **Container Rules**. Container anti-patterns are the
`AP-DOCKER-*` rules in `schemas/antipatterns.v1.json`; the security policy is `SEC-012` in
`00_UniversalStandards/07_Security_In_Depth.md`.

---

## 1️⃣ Containerized Execution

Every tool the platform runs (builds, tests, linters, scanners, benchmarks, verification) runs in a
**pinned container image**, never with tools installed on a workstation or a runner.

- **One image, everywhere.** The image a person runs locally is the image CI runs. A result counts
  only when it names the image it ran in, by digest.
- **Pinned completely.** Base images by tag and digest; language packages by exact version with a
  lockfile; downloaded binaries by version and checksum.
- **A workstation is not a home.** A result produced on one machine is provisional until CI
  repeats it in the same image.
- **Isolated dependencies.** Tools with large dependency trees each get their own environment
  (virtualenv or image). Forcing a resolver past a conflict (`--force`, `--legacy-peer-deps`, an
  ignored `pip check`) is the `AP-PY-007` / `AP-NODE-004` anti-pattern.

## 2️⃣ Image Architecture

| Rule | Why |
| :--- | :--- |
| **Multi-stage builds**: build tools in a builder stage, only the runtime in the final stage | Smaller images, smaller attack surface |
| **Minimal runtime base** (slim or distroless) | Fewer packages to patch and scan |
| **One process per container**, run in exec form (`CMD ["app"]`) | The process receives `SIGTERM` and shuts down gracefully (`AP-DOCKER-007`) |
| **Build once, promote the same digest** through dev, staging, and production | What was tested is what runs |
| **Configuration from the environment**, never baked into the image | One image for every environment |
| **Stateless**: state in the owning service's data store, not the container filesystem | Containers are replaced, not repaired (`02_BackendZone/05_Application_Architecture.md` §2) |
| **Health declared**: a `HEALTHCHECK` or the orchestrator's probes | A hung process is detected (`AP-DOCKER-008`) |
| **Resource limits** set by the orchestrator | One container cannot starve its neighbors, the Governor rule at the host level |
| **Telemetry configured by environment** (`OTEL_*`) | The same image reports from every environment |

## 3️⃣ Image Security (`SEC-012`)

- **Non-root.** The final `USER` is a numeric non-root UID (`AP-DOCKER-002`, `AP-DOCKER-003`).
- **Pinned base by digest** (`AP-DOCKER-001`).
- **No secrets in layers**: build secrets through `RUN --mount=type=secret`, runtime secrets from a
  secret manager; never `ENV` or `ARG` (`AP-DOCKER-009`).
- **Read-only root filesystem** and dropped Linux capabilities at run time, unless a reviewed
  exception says otherwise.
- **Every service ships an image**, because everything runs in the cloud as a container. The
  central gate's image job builds it, runs its tests inside it unprivileged with no network and no
  capabilities, and scans it (`15_Central_CI.md` §5). A repository that runs nothing declares why.
- **Scanned**: images are scanned before they are pushed and block on CRITICAL or CISA KEV, the
  same threshold as every other scanner. An image finding is fixed at its source (a smaller base,
  a narrower build, a dropped dependency), never excepted.
- **Provenance**: images are built by the pipeline and pushed to the organization's registry; a
  locally built image is never deployed.

## 4️⃣ Orchestrated Workloads

Kubernetes manifests carry the same rules at run time, checked by kube-linter and Checkov
(`AP-K8S-*` in `schemas/antipatterns.v1.json`): run as non-root, never privileged, no host network,
no `latest` images, memory limits set, a read-only root filesystem, no privilege escalation, and a
readiness probe. Helm charts are rendered (`helm template`) and the rendered manifests are checked
by the same rules; rendering is a pipeline step, not yet part of the catalog's verification.

## 5️⃣ Rolling It Out

The rules apply to new work immediately. Existing repositories move to containerized execution
step by step, each step its own change; until a tool runs in a container, its results carry the
caveat that they came from a host installation.

---

## Principle

Run everything in a pinned container so that a result means the same thing on every machine, build
images that are small and stateless, and give them no more privilege than the process needs.
