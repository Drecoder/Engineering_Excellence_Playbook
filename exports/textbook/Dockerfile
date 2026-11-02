# Containerized textbook build: Markdown -> HTML -> PDF with headless Chromium.
FROM node:22.18.0-bookworm-slim@sha256:752ea8a2f758c34002a0461bd9f1cee4f9a3c36d48494586f60ffce1fc708e0e

# hadolint ignore=DL3008
RUN apt-get update \
    && apt-get install -y --no-install-recommends chromium fonts-dejavu-core fonts-noto-color-emoji git ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/textbook
RUN npm install --no-audit --no-fund markdown-it@14.1.0

ENV NODE_PATH=/opt/textbook/node_modules \
    BROWSER=/usr/bin/chromium \
    BROWSER_FLAGS="--no-sandbox"

USER node
WORKDIR /work
HEALTHCHECK NONE
CMD ["node", "exports/textbook/build.js"]
