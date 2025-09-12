#!/usr/bin/env python3
"""
Kikoeru Directory Monitor
监控指定目录中的压缩文件变化，并调用处理器进行自动化处理
"""

import os
import sys
import time
import logging
import signal
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

try:
    from .helper import ArchiveProcessor
    from .logger import setup_logger
except ImportError:
    sys.path.insert(0, os.path.dirname(__file__))
    from helper import ArchiveProcessor
    from logger import setup_logger


class ArchiveEventHandler(FileSystemEventHandler):
    """文件系统事件处理器"""

    def __init__(self, processor, work_dir):
        super().__init__()
        self.processor = processor
        self.work_dir = Path(work_dir)
        self.pending_files = {}  # 等待队列

        self.stability_wait_time = int(os.getenv("STABILITY_WAIT_TIME", "15"))
        self.min_stable_checks = int(os.getenv("MIN_STABLE_CHECKS", "2"))
        self.max_wait_time = int(os.getenv("MAX_WAIT_TIME", "3600"))

    def on_created(self, event):
        """文件创建事件"""
        if event.is_directory:
            return

        file_path = Path(event.src_path)
        if self._is_archive_file(file_path):
            logging.info(f"检测到新文件: {file_path}")
            self._handle_new_file(file_path)

    def on_modified(self, event):
        """文件修改事件"""
        if event.is_directory:
            return

        file_path = Path(event.src_path)
        if self._is_archive_file(file_path):
            self._handle_modified_file(file_path)

    def _is_archive_file(self, file_path):
        """检查是否为支持的压缩文件（包括无扩展名文件）"""
        # 先检查扩展名
        if file_path.suffix.lower() in [".zip", ".rar", ".7z"]:
            return True

        # 如果没有扩展名，尝试检测文件内容
        if not file_path.suffix:
            try:
                # 使用处理器的检测方法
                detected_type = self.processor._detect_file_type(file_path)
                return detected_type is not None
            except Exception as e:
                logging.warning(f"检测文件类型失败 {file_path}: {e}")
                return False

        return False

    def _handle_new_file(self, file_path):
        """处理新建文件"""
        current_time = time.time()
        try:
            file_size = file_path.stat().st_size if file_path.exists() else 0
            file_mtime = (
                file_path.stat().st_mtime if file_path.exists() else current_time
            )
        except OSError:
            file_size = 0
            file_mtime = current_time

        self.pending_files[str(file_path)] = {
            "path": file_path,
            "last_size": file_size,
            "last_mtime": file_mtime,
            "last_check": current_time,
            "created_time": current_time,
            "stable_count": 0,
        }

        logging.info(
            f"文件 {file_path} 添加到待处理队列 ({file_size / 1024 / 1024:.2f}MB)"
        )

    def _handle_modified_file(self, file_path):
        """处理文件修改"""
        if str(file_path) in self.pending_files:
            try:
                current_size = file_path.stat().st_size if file_path.exists() else 0
                current_mtime = (
                    file_path.stat().st_mtime if file_path.exists() else time.time()
                )
            except OSError:
                current_size = 0
                current_mtime = time.time()

            file_info = self.pending_files[str(file_path)]

            # 检查文件大小和修改时间稳定性
            size_stable = current_size == file_info["last_size"]
            mtime_stable = current_mtime == file_info.get("last_mtime", 0)

            if size_stable and mtime_stable:
                file_info["stable_count"] += 1
            else:
                file_info["stable_count"] = 0
                file_info["last_size"] = current_size
                file_info["last_mtime"] = current_mtime

            file_info["last_check"] = time.time()

    def check_pending_files(self):
        """检查待处理文件，处理已稳定的文件"""
        current_time = time.time()
        files_to_process = []

        for file_path_str, file_info in list(self.pending_files.items()):
            file_path = file_info["path"]

            # 检查文件是否还存在
            if not file_path.exists():
                logging.warning(f"文件 {file_path} 已被删除")
                del self.pending_files[file_path_str]
                continue

            # 获取当前文件信息并更新稳定性检查
            try:
                current_size = file_path.stat().st_size
                current_mtime = file_path.stat().st_mtime
            except OSError:
                logging.warning(f"无法获取文件信息 {file_path}")
                continue

            # 检查文件稳定性（在check_pending_files中主动检查）
            # 但是只有在文件创建一定时间后才开始计算稳定性
            time_since_creation = current_time - file_info["created_time"]

            # 只有在文件创建至少N秒后才开始检查稳定性（防止刚创建的文件被误判为稳定）
            min_check_delay = 3  # 最小检查延迟时间（秒）

            if time_since_creation >= min_check_delay:
                size_stable = current_size == file_info["last_size"]
                mtime_stable = current_mtime == file_info.get("last_mtime", 0)

                if size_stable and mtime_stable:
                    file_info["stable_count"] += 1
                else:
                    file_info["stable_count"] = 0
                    file_info["last_size"] = current_size
                    file_info["last_mtime"] = current_mtime
            else:
                # 文件太新，不计算稳定性，但更新文件信息
                file_info["last_size"] = current_size
                file_info["last_mtime"] = current_mtime
                file_info["stable_count"] = 0  # 重置稳定计数
            file_info["last_check"] = current_time

            # 修复后的判断逻辑：优先检查稳定性，然后检查超时
            should_process = False
            process_reason = ""

            if file_info["stable_count"] >= self.min_stable_checks:
                # 文件已经稳定，无论时间多长都应该处理
                should_process = True
                process_reason = f"文件稳定 (稳定{file_info['stable_count']}次)"
            elif time_since_creation > self.max_wait_time:
                # 超时强制处理，防止无限等待
                should_process = True
                process_reason = (
                    f"超时强制处理 ({time_since_creation:.1f}s > {self.max_wait_time}s)"
                )
            elif time_since_creation > self.stability_wait_time:
                # 已经等待了基础时间，但文件还不够稳定，继续等待但给出详细信息
                logging.info(
                    f"文件 {file_path} 等待中: {time_since_creation:.1f}s, 稳定次数: {file_info['stable_count']}/{self.min_stable_checks}"
                )
            else:
                # 还在初始等待期
                logging.debug(f"文件 {file_path} 初始等待: {time_since_creation:.1f}s")

            if should_process:
                logging.info(f"文件 {file_path} 准备处理: {process_reason}")
                files_to_process.append(file_path)
                del self.pending_files[file_path_str]

        # 处理稳定的文件
        for file_path in files_to_process:
            logging.info(f"📅 开始处理文件: {file_path}")
            try:
                self.processor.process_archive(file_path)
                logging.info(f"✅ 文件 {file_path} 处理完成")
            except Exception as e:
                logging.error(f"❌ 处理文件 {file_path} 时出错: {e}")


class DirectoryMonitor:
    """目录监控器"""

    def __init__(self, work_dir):
        self.work_dir = Path(work_dir)
        self.processor = ArchiveProcessor(work_dir)
        self.observer = Observer()
        self.event_handler = ArchiveEventHandler(self.processor, work_dir)
        self.running = False

        # 从环境变量获取检查间隔
        self.check_interval = int(os.getenv("CHECK_INTERVAL", "5"))  # 检查间隔（秒）

        # 使用统一日志配置
        setup_logger(work_dir, "monitor.log")

    def start(self):
        """启动监控"""
        logging.info(f"🔍 开始监控目录: {self.work_dir}")
        logging.info(
            f"⚙️ 监控配置: 检查间隔={self.check_interval}s, 稳定等待={self.event_handler.stability_wait_time}s, 最大等待={self.event_handler.max_wait_time}s"
        )

        # 确保目录存在
        self.work_dir.mkdir(exist_ok=True)

        # 设置监控
        self.observer.schedule(self.event_handler, str(self.work_dir), recursive=False)

        # 启动观察器
        self.observer.start()
        self.running = True

        try:
            while self.running:
                time.sleep(self.check_interval)  # 按配置间隔检查待处理文件
                self.event_handler.check_pending_files()

        except KeyboardInterrupt:
            logging.info(f"🔴 收到中断信号，正在停止监控...")
        finally:
            self.stop()

    def stop(self):
        """停止监控"""
        if self.running:
            self.running = False
            self.observer.stop()
            self.observer.join()
            logging.info("监控已停止")

    def signal_handler(self, signum, frame):
        """信号处理器"""
        logging.info(f"收到信号 {signum}，正在停止监控...")
        self.stop()
        sys.exit(0)


def main():
    """主函数"""
    if len(sys.argv) != 2:
        print("用法: python3 monitor.py <监控目录>")
        sys.exit(1)

    work_dir = sys.argv[1]

    # 创建监控器
    monitor = DirectoryMonitor(work_dir)

    # 设置信号处理
    signal.signal(signal.SIGTERM, monitor.signal_handler)
    signal.signal(signal.SIGINT, monitor.signal_handler)

    # 启动监控
    monitor.start()


if __name__ == "__main__":
    main()
