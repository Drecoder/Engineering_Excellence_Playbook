# Pinned toolchain for verifying antipatterns.v1 mappings and running the catalog tests.
# The same image runs on a workstation and in CI (playbook: Containerized Execution). Base images
# are pinned by digest; downloaded binaries are checksum-verified; the runtime user is not root.

FROM golang:1.26-bookworm@sha256:632dff7351799a5a9954a48dc06670ade72ee44e8c351cdc0e5a57af2fea21af AS go
RUN GOBIN=/out go install honnef.co/go/tools/cmd/staticcheck@2026.2.2 \
    && GOBIN=/out go install github.com/rhysd/actionlint/cmd/actionlint@v1.7.12

FROM node:22.18.0-bookworm-slim@sha256:752ea8a2f758c34002a0461bd9f1cee4f9a3c36d48494586f60ffce1fc708e0e AS node
WORKDIR /opt/eslint
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund

FROM python:3.12-slim-bookworm@sha256:6a0e06f5ba0b373d051aabd3fffb9b873f27f9a2a3a14bcbe37dee6f0e3bbc70

ARG TRIVY_VERSION=0.71.1
ARG TRIVY_SHA256=3cbae37cd440cd8676e5ce9207fe460b5641c7579a17e9d00f8894928c41a88d
ARG TFLINT_VERSION=0.65.0
ARG TFLINT_SHA256=d4c545ed2e29d6338604b586f34f544f380f70f243aa72f7b484713835eaec61
ARG HADOLINT_VERSION=2.15.1
ARG HADOLINT_SHA256=c7187db94eeeeca956519a6af171adc31453941a1e777961f6e680f697c8c507
# shellcheck publishes no checksum file; this is the hash of the release artifact when first pinned.
ARG SHELLCHECK_VERSION=0.11.0
ARG SHELLCHECK_SHA256=8c3be12b05d5c177a04c29e3c78ce89ac86f1595681cab149b65b97c4e227198

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# hadolint ignore=DL3008
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl unzip xz-utils libstdc++6 \
    && rm -rf /var/lib/apt/lists/*

RUN curl -sSfLo /tmp/trivy.tgz "https://github.com/aquasecurity/trivy/releases/download/v${TRIVY_VERSION}/trivy_${TRIVY_VERSION}_Linux-64bit.tar.gz" \
    && echo "${TRIVY_SHA256}  /tmp/trivy.tgz" | sha256sum -c - \
    && tar -xzf /tmp/trivy.tgz -C /usr/local/bin trivy \
    && curl -sSfLo /tmp/tflint.zip "https://github.com/terraform-linters/tflint/releases/download/v${TFLINT_VERSION}/tflint_linux_amd64.zip" \
    && echo "${TFLINT_SHA256}  /tmp/tflint.zip" | sha256sum -c - \
    && unzip -q /tmp/tflint.zip -d /usr/local/bin \
    && curl -sSfLo /usr/local/bin/hadolint "https://github.com/hadolint/hadolint/releases/download/v${HADOLINT_VERSION}/hadolint-linux-x86_64" \
    && echo "${HADOLINT_SHA256}  /usr/local/bin/hadolint" | sha256sum -c - \
    && chmod 0755 /usr/local/bin/hadolint \
    && curl -sSfLo /tmp/sc.txz "https://github.com/koalaman/shellcheck/releases/download/v${SHELLCHECK_VERSION}/shellcheck-v${SHELLCHECK_VERSION}.linux.x86_64.tar.xz" \
    && echo "${SHELLCHECK_SHA256}  /tmp/sc.txz" | sha256sum -c - \
    && tar -xJf /tmp/sc.txz -C /tmp \
    && mv "/tmp/shellcheck-v${SHELLCHECK_VERSION}/shellcheck" /usr/local/bin/ \
    && rm -rf /tmp/trivy.tgz /tmp/tflint.zip /tmp/sc.txz /tmp/shellcheck-*

COPY requirements.txt /tmp/requirements.txt
# Each tool with a large dependency tree gets its own virtualenv, so their requirements can never
# collide (one shared environment is the AP-PY-007 anti-pattern).
RUN pip install --no-cache-dir -r /tmp/requirements.txt \
    && python -m venv /opt/semgrep \
    && /opt/semgrep/bin/pip install --no-cache-dir semgrep==1.182.1 \
    && ln -s /opt/semgrep/bin/semgrep /usr/local/bin/semgrep \
    && python -m venv /opt/zizmor \
    && /opt/zizmor/bin/pip install --no-cache-dir zizmor==1.31.1 \
    && ln -s /opt/zizmor/bin/zizmor /usr/local/bin/zizmor \
    && python -m venv /opt/checkov \
    && /opt/checkov/bin/pip install --no-cache-dir checkov==3.3.29 \
    && ln -s /opt/checkov/bin/checkov /usr/local/bin/checkov

COPY --from=golang:1.26-bookworm@sha256:632dff7351799a5a9954a48dc06670ade72ee44e8c351cdc0e5a57af2fea21af /usr/local/go /usr/local/go
COPY --from=go /out/staticcheck /out/actionlint /usr/local/bin/
COPY --from=node /usr/local/bin/node /usr/local/bin/node
COPY --from=node /opt/eslint /opt/eslint

RUN useradd --uid 10001 --create-home tool \
    && mkdir -p /opt/eslint/work /opt/trivy-cache \
    && chown tool /opt/eslint/work /opt/trivy-cache

ENV PATH=/usr/local/go/bin:/opt/eslint/node_modules/.bin:$PATH \
    GOPATH=/home/tool/go \
    GOFLAGS=-mod=mod \
    GOTOOLCHAIN=local \
    TRIVY_CACHE_DIR=/opt/trivy-cache \
    SEMGREP_SEND_METRICS=off \
    ESLINT_WORKDIR=/opt/eslint/work

USER tool
# Download Trivy's misconfiguration checks once, so verification runs do not depend on it.
RUN mkdir -p /tmp/empty && trivy config --quiet /tmp/empty >/dev/null

WORKDIR /work
HEALTHCHECK NONE
