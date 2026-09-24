FROM node:24.14.0-bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends tmux git ripgrep ca-certificates python3 make g++ \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /opt/openrig
RUN npm install --omit=dev --save-exact @openrig/cli@0.5.14 @openai/codex@0.144.6 @anthropic-ai/claude-code@2.1.280
ENV PATH="/opt/openrig/node_modules/.bin:${PATH}" HOME=/home/node OPENRIG_HOME=/home/node/.openrig CODEX_HOME=/home/node/.codex CLAUDE_CONFIG_DIR=/home/node/.claude
COPY entrypoint.sh /usr/local/bin/account-environment
USER node
WORKDIR /workspace
ENTRYPOINT ["/usr/local/bin/account-environment"]
