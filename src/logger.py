#!/usr/bin/env python3
"""
日志配置
"""

import os
import sys
import logging
from pathlib import Path


def setup_logger(work_dir, log_file_name="helper.log"):
    """
    设置统一的日志配置

    Args:
        work_dir: 工作目录
        log_file_name: 日志文件名
    """
    # 获取根logger
    logger = logging.getLogger()

    # 如果已经配置过，先清除旧的handlers
    if logger.handlers:
        for handler in logger.handlers[:]:
            if hasattr(handler, "close"):
                handler.close()
            logger.removeHandler(handler)

    # 设置日志级别
    logger.setLevel(logging.INFO)

    # 创建格式化器
    formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )

    # 创建控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 创建文件处理器
    try:
        # 从环境变量获取日志路径
        log_dir = os.getenv("LOG_DIR", str(Path(work_dir) / ".helper"))
        log_file = Path(log_dir) / log_file_name

        # 确保日志目录存在
        log_file.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file, encoding="utf-8", mode="a")
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        logger.warning(f"⚠️ 无法创建日志文件: {e}")

    # 防止日志重复输出
    logger.propagate = False

    return logger


def cleanup_logger():
    """清理日志处理器，释放文件句柄"""
    logger = logging.getLogger()
    for handler in logger.handlers[:]:
        try:
            if hasattr(handler, "close"):
                handler.close()
            logger.removeHandler(handler)
        except Exception:
            # 忽略关闭失败，确保不影响主流程
            pass

    # 强制释放日志资源
    logging.shutdown()
