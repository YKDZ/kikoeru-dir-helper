#!/usr/bin/env python3
"""
Kikoeru Directory Helper - 主入口文件
提供直接访问核心功能的便捷方式
"""

import sys
from pathlib import Path

# 添加src目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("Kikoeru Directory Helper")
        print()
        print("用法:")
        print("  python main.py monitor <目录>     # 监控模式")
        print("  python main.py process <文件>     # 处理单个文件")
        print("  python main.py test              # 运行测试")
        print()
        print("或直接使用模块:")
        print("  python src/monitor.py <目录>      # 监控模式")
        print("  python scripts/run_tests.py      # 运行所有测试")
        sys.exit(1)

    command = sys.argv[1].lower()

    if command == "monitor":
        if len(sys.argv) != 3:
            print("用法: python main.py monitor <目录>")
            sys.exit(1)

        from src.monitor import DirectoryMonitor
        import signal

        work_dir = sys.argv[2]
        monitor = DirectoryMonitor(work_dir)

        # 设置信号处理
        signal.signal(signal.SIGTERM, monitor.signal_handler)
        signal.signal(signal.SIGINT, monitor.signal_handler)

        # 启动监控
        monitor.start()

    elif command == "process":
        if len(sys.argv) != 3:
            print("用法: python main.py process <文件>")
            sys.exit(1)

        from src.helper import ArchiveProcessor
        from pathlib import Path

        file_path = Path(sys.argv[2])
        if not file_path.exists():
            print(f"错误: 文件不存在 {file_path}")
            sys.exit(1)

        processor = ArchiveProcessor(file_path.parent)
        result = processor.process_archive(file_path)

        if result:
            print(f"✅ 处理成功: {file_path}")
        else:
            print(f"❌ 处理失败: {file_path}")
            sys.exit(1)

    elif command == "test":
        import subprocess

        test_script = project_root / "scripts" / "run_tests.py"
        result = subprocess.run([sys.executable, str(test_script)])
        sys.exit(result.returncode)

    else:
        print(f"未知命令: {command}")
        print("支持的命令: monitor, process, test")
        sys.exit(1)


if __name__ == "__main__":
    main()
