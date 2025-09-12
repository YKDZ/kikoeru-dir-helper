FROM ghcr.io/astral-sh/uv:python3.13-alpine

WORKDIR /app

COPY pyproject.toml uv.lock ./

RUN apk update && \
    apk add --no-cache \
        ca-certificates \
        unzip \
        p7zip \
        inotify-tools \
        file \
        libmagic \
        gcc \
        musl-dev \
        python3-dev \
        linux-headers && \
    uv sync --frozen --no-install-project && \
    apk del --purge gcc musl-dev python3-dev linux-headers && \
    rm -rf /var/cache/apk/*

RUN uv sync --frozen --no-install-project

COPY ./src/ ./src/
COPY ./scripts/ ./scripts/
COPY ./main.py .
COPY ./docker/ ./docker/
COPY ./.venv/ ./.venv/

RUN if ls ./docker/libs/rarlinux-*.tar.gz 1> /dev/null 2>&1; then \
        for rar_file in ./docker/libs/rarlinux-*.tar.gz; do \
            echo "Found RAR library: $rar_file"; \
            tar -xzf "$rar_file" -C /tmp && \
            if [ -d "/tmp/rar" ]; then \
                cp /tmp/rar/unrar /usr/local/bin/ && \
                cp /tmp/rar/rar /usr/local/bin/ && \
                chmod +x /usr/local/bin/unrar && \
                chmod +x /usr/local/bin/rar && \
                rm -rf /tmp/rar && \
                echo "RAR library installed successfully from $rar_file"; \
                break; \
            else \
                echo "Error: The RAR archive did not extract to a 'rar' directory."; \
                exit 1; \
            fi; \
        done; \
    else \
        echo "Error: No RAR library found in ./docker/libs/"; \
        exit 1; \
    fi

RUN which unrar && unrar | head -5

RUN chmod +x ./docker/entrypoint.sh

RUN mkdir -p /data/.helper

ENV WORK_DIR=/data
ENV CHECK_INTERVAL=5
ENV STABILITY_WAIT_TIME=15
ENV MIN_STABLE_CHECKS=2
ENV SMALL_FILE_THRESHOLD=10485760
ENV LOG_DIR=/data/.helper

ENTRYPOINT ["./docker/entrypoint.sh"]