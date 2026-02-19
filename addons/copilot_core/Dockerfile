ARG BUILD_FROM
FROM $BUILD_FROM

# Install Python runtime and dependencies
RUN apk add --no-cache python3 py3-pip graphviz curl bash libstdc++ libgcc && \
    pip3 install --no-cache-dir \
        flask==3.0.2 \
        flask-compress==1.14 \
        waitress==3.0.0 \
        python-ulid==2.7.0 \
        pyyaml==6.0.1 \
        psutil==6.1.0 \
        neo4j==5.26.0 \
        pydantic==2.12.5 \
        requests==2.31.0

# Install Ollama from Alpine edge/community (native musl build)
# Falls back to binary download with gcompat if edge package unavailable
RUN echo "@edge-community https://dl-cdn.alpinelinux.org/alpine/edge/community" >> /etc/apk/repositories && \
    (apk add --no-cache ollama@edge-community 2>/dev/null || \
     (echo "INFO: edge package unavailable, trying binary download..." && \
      apk add --no-cache gcompat && \
      ARCH=$(uname -m) && \
      case "$ARCH" in \
        x86_64) DLARCH="amd64" ;; \
        aarch64) DLARCH="arm64" ;; \
        *) echo "ERROR: Unsupported arch $ARCH"; exit 1 ;; \
      esac && \
      curl -fsSL "https://ollama.com/download/ollama-linux-${DLARCH}.tgz" | tar xz -C /usr)) || \
    echo "WARNING: Ollama installation failed -- LLM features will be unavailable"

# Persist Ollama models in /share/ (NOT /data/) to avoid bloating HA backups
# /share/ is persistent, shared between addons, and can be excluded from backups
ENV OLLAMA_MODELS=/share/ai_home_copilot/ollama/models

WORKDIR /usr/src/app
COPY rootfs/usr/src/app /usr/src/app

EXPOSE 8909

# Start script that launches Ollama + PilotSuite
COPY rootfs/usr/src/app/start_dual.sh /start.sh
RUN chmod +x /start.sh
CMD ["/start.sh"]
