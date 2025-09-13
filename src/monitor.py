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

        self.min_stable_checks = int(os.getenv("MIN_STABLE_CHECKS", "3"))
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
        """文件修改事件 - 移除此方法实现，仅被动检测新文件"""
        # 不再处理文件修改事件，改为仅通过主动轮询检查文件状态
        pass

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

            # 获取当前文件信息
            try:
                current_size = file_path.stat().st_size
                current_mtime = file_path.stat().st_mtime
            except OSError:
                logging.warning(f"无法获取文件信息 {file_path}")
                continue

            # 记录当前文件信息
            prev_size = file_info.get("last_size", 0)
            prev_mtime = file_info.get("last_mtime", 0)
            
            # 更新文件信息
            file_info["last_size"] = current_size
            file_info["last_mtime"] = current_mtime
            file_info["last_check"] = current_time

            # 计算自上次检查以来的变化
            size_changed = current_size != prev_size
            mtime_changed = current_mtime != prev_mtime
            
            # 重置或增加稳定计数
            if size_changed or mtime_changed:
                file_info["stable_count"] = 0
                logging.debug(f"文件 {file_path} 有变化，重置稳定计数")
            else:
                time_since_creation = current_time - file_info["created_time"]
                min_check_delay = 10 
                
                # 稳定且不新
                if time_since_creation >= min_check_delay:
                    file_info["stable_count"] += 1
                    logging.debug(f"文件 {file_path} 稳定，稳定计数: {file_info["stable_count"]}")
                else:
                    file_info["stable_count"] = 0  # 文件太新，不计算稳定性
                    logging.debug(f"文件 {file_path} 太新，重置稳定计数")

            # 检查是否应该处理文件
            time_since_creation = current_time - file_info["created_time"]
            should_process = False
            process_reason = ""

            if file_info["stable_count"] >= self.min_stable_checks:
                should_process = True
                process_reason = f"文件稳定 (稳定{file_info['stable_count']}次)"
            elif time_since_creation > self.max_wait_time:
                should_process = True
                process_reason = f"超时强制处理 ({time_since_creation:.1f}s > {self.max_wait_time}s)"
            
            if should_process:
                logging.info(f"文件 {file_path} 准备处理: {process_reason}")
                files_to_process.append(file_path)
                del self.pending_files[file_path_str]
            else:
                # 记录等待状态
                logging.info(
                    f"文件 {file_path} 等待中: {time_since_creation:.1f}s, "
                    f"稳定次数: {file_info['stable_count']}/{self.min_stable_checks}, "
                    f"大小: {current_size / 1024 / 1024:.2f}MB"
                )

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
        self.check_interval = int(os.getenv("CHECK_INTERVAL", "5"))

        # 使用统一日志配置
        setup_logger(work_dir, "monitor.log")

    def start(self):
        """启动监控"""
        logging.info(f"🔍 开始监控目录: {self.work_dir}")
        logging.info(
            f"⚙️ 监控配置: "
            f"稳定性检查间隔={self.check_interval}s, "
            f"最大等待稳定时间={self.event_handler.max_wait_time}s, "
            f"稳定所需检查次数={self.event_handler.min_stable_checks}"
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
