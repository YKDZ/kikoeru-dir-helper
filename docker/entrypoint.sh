#!/bin/sh

set -e

# 设置虚拟环境路径
UV_VENV_PATH="/app/.venv"
export PATH="$UV_VENV_PATH/bin:$PATH"

# 日志函数
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') [ENTRYPOINT] $1"
}

log_error() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') [ENTRYPOINT ERROR] $1" >&2
}

# 初始化函数
init_environment() {
    log "正在初始化环境..."

    # 设置默认工作目录
    export WORK_DIR=${WORK_DIR:-/data}

    # 确保工作目录存在
    if [ ! -d "$WORK_DIR" ]; then
        log "创建工作目录: $WORK_DIR"
        mkdir -p "$WORK_DIR"
    fi

    # 确保日志目录存在
    mkdir -p "$WORK_DIR/.helper"

    # 设置权限
    chmod 755 "$WORK_DIR"
    chmod 755 "$WORK_DIR/.helper"

    log "环境初始化完成"
    log "工作目录: $WORK_DIR"
}

# 检查依赖
check_dependencies() {
    log "检查依赖..."

    missing_deps=""

    # 检查系统依赖
    for cmd in unzip unrar 7z; do
        if ! command -v "$cmd" >/dev/null 2>&1; then
            missing_deps="$missing_deps $cmd"
        fi
    done

    if [ -n "$missing_deps" ]; then
        log_error "缺少以下依赖: $missing_deps"
        log_error "PATH: $PATH"
        log_error "尝试查找命令:"
        for cmd in unzip unrar 7z; do
            log_error "  $cmd: $(which $cmd 2>/dev/null || echo '未找到')"
        done
        exit 1
    fi

    log "依赖检查通过"
}

# 启动监控服务
start_monitor() {
    log "启动目录监控服务..."

    # 在后台启动Python监控脚本
    cd /app
    python3 src/monitor.py "$WORK_DIR" &
    MONITOR_PID=$!

    log "监控服务已启动 (PID: $MONITOR_PID)"

    # 等待监控进程
    wait "$MONITOR_PID"
}

# 信号处理函数
cleanup() {
    log "正在关闭服务..."

    if [ -n "$MONITOR_PID" ]; then
        kill "$MONITOR_PID" 2>/dev/null || true
        wait "$MONITOR_PID" 2>/dev/null || true
    fi

    log "服务已关闭"
    exit 0
}

# 设置信号处理
trap cleanup SIGTERM SIGINT

# 主流程
main() {
    # 初始化环境
    init_environment

    # 检查系统依赖
    check_dependencies
    
    # 启动监控
    start_monitor
}

# 执行主函数
main "$@"