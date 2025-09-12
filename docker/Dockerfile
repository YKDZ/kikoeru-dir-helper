FROM python:3.13-slim

# 工作目录
WORKDIR /app

RUN apt update && \
    apt install -y \
        ca-certificates \
        unzip \
        p7zip-full \
        inotify-tools \
        libmagic1 \
        libmagic-dev; \
    rm -rf /var/lib/apt/lists/*

# 复制依赖文件（根据你的 build context，保持原路径）
COPY ./requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制源代码和脚本
COPY ./src/ ./src/
COPY ./scripts/ ./scripts/
COPY ./main.py .
COPY ./docker/ ./docker/

# 安装本地RAR库文件（通用版本匹配）
RUN for rar_file in ./docker/libs/rarlinux-*.tar.gz; do \
        if [ -f "$rar_file" ]; then \
            echo "Found RAR library: $rar_file"; \
            tar -xzf "$rar_file" && \
            cp rar/unrar /usr/local/bin/ && \
            cp rar/rar /usr/local/bin/ && \
            chmod +x /usr/local/bin/unrar && \
            chmod +x /usr/local/bin/rar && \
            rm -rf rar/ && \
            echo "RAR library installed successfully from $rar_file"; \
            break; \
        fi; \
    done && \
    # 验证安装
    if ! /usr/local/bin/unrar >/dev/null 2>&1; then \
        echo "Warning: unrar installation verification failed"; \
    else \
        echo "RAR tools installed and verified successfully"; \
    fi

# 确保 entrypoint 可执行
RUN chmod +x ./docker/entrypoint.sh

# 创建所需目录
RUN mkdir -p /data/.helper

# 环境变量
ENV WORK_DIR=/data
ENV CHECK_INTERVAL=5
ENV STABILITY_WAIT_TIME=15
ENV MIN_STABLE_CHECKS=2
ENV SMALL_FILE_THRESHOLD=10485760
ENV LOG_DIR=/data/.helper

# 启动脚本
ENTRYPOINT ["./docker/entrypoint.sh"]
