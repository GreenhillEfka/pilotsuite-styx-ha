ARG BUILD_FROM
FROM $BUILD_FROM

# Install Python runtime, dependencies, and Ollama
RUN apk add --no-cache python3 py3-pip graphviz curl bash && \
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

# Install Ollama (bundled in addon for offline LLM support)
RUN curl -fsSL https://ollama.com/install.sh | sh || \
    echo "WARNING: Ollama installation failed -- LLM features will be unavailable"

WORKDIR /usr/src/app
COPY rootfs/usr/src/app /usr/src/app

EXPOSE 8099

# Start script that launches Ollama + PilotSuite
COPY rootfs/usr/src/app/start_dual.sh /start.sh
RUN chmod +x /start.sh
CMD ["/start.sh"]
