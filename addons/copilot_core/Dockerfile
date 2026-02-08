ARG BUILD_FROM
FROM $BUILD_FROM

# Minimal Python runtime
RUN apk add --no-cache python3 py3-pip && \
    pip3 install --no-cache-dir flask==3.0.2 waitress==3.0.0

WORKDIR /usr/src/app
COPY rootfs/usr/src/app /usr/src/app

EXPOSE 8909
CMD ["python3", "-u", "main.py"]
