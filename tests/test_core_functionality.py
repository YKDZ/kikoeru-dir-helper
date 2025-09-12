#!/usr/bin/env python3
"""
核心功能测试
测试基本的压缩文件处理功能，包括：
- RJ文件夹处理
- 单文件夹重命名
- 混合内容处理
- 文件类型检测
"""

import os
import sys
import zipfile
import tempfile
import shutil
from pathlib import Path

# 添加src目录到路径以导入模块
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from src.helper import ArchiveProcessor


def create_test_archive(archive_path: Path, content_structure: dict):
    """创建测试用的压缩文件"""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # 创建内容结构
        for item_path, content in content_structure.items():
            full_path = temp_path / item_path
            full_path.parent.mkdir(parents=True, exist_ok=True)

            if content is None:  # 文件夹
                full_path.mkdir(exist_ok=True)
            else:  # 文件
                full_path.write_text(content, encoding="utf-8")

        # 创建压缩文件
        with zipfile.ZipFile(archive_path, "w") as zf:
            for root, dirs, files in os.walk(temp_path):
                for file in files:
                    file_path = Path(root) / file
                    arcname = file_path.relative_to(temp_path)
                    zf.write(file_path, arcname)


def test_rj_folders():
    """测试RJ文件夹处理"""
    print("=== 测试RJ文件夹处理 ===")

    project_root = Path(__file__).parent.parent
    test_dir = project_root / "test_data_rj"
    test_dir.mkdir(exist_ok=True)

    try:
        archive_path = test_dir / "test_rj.zip"

        # 创建包含RJ文件夹的压缩文件
        content = {
            "RJ123456/info.txt": "测试内容1",
            "RJ789012/info.txt": "测试内容2",
        }
        create_test_archive(archive_path, content)

        # 处理
        processor = ArchiveProcessor(test_dir, log_to_file=False)
        result = processor.process_archive(archive_path)

        # 验证结果
        assert result, "处理应该成功"
        assert not archive_path.exists(), "原压缩文件应该被删除"
        assert (test_dir / "RJ123456").exists(), "RJ123456文件夹应该存在"
        assert (test_dir / "RJ789012").exists(), "RJ789012文件夹应该存在"

        print("✓ RJ文件夹处理测试通过")
        return True

    finally:
        if test_dir.exists():
            try:
                shutil.rmtree(test_dir)
            except Exception:
                pass


def test_single_folder_rename():
    """测试单文件夹重命名"""
    print("=== 测试单文件夹重命名 ===")

    project_root = Path(__file__).parent.parent
    test_dir = project_root / "test_data_rename"
    test_dir.mkdir(exist_ok=True)

    try:
        archive_path = test_dir / "RJ123456.zip"

        # 创建包含单个非RJ文件夹的压缩文件
        content = {
            "audio/track1.mp3": "音频内容1",
            "audio/track2.mp3": "音频内容2",
        }
        create_test_archive(archive_path, content)

        # 处理
        processor = ArchiveProcessor(test_dir, log_to_file=False)
        result = processor.process_archive(archive_path)

        # 验证结果
        assert result, "处理应该成功"
        assert not archive_path.exists(), "原压缩文件应该被删除"
        assert (test_dir / "RJ123456").exists(), "重命名的文件夹应该存在"
        assert (test_dir / "RJ123456" / "track1.mp3").exists(), (
            "文件应该在重命名的文件夹中"
        )

        print("✓ 单文件夹重命名测试通过")
        return True

    finally:
        if test_dir.exists():
            try:
                shutil.rmtree(test_dir)
            except Exception:
                pass


def test_mixed_content():
    """测试混合内容处理"""
    print("=== 测试混合内容处理 ===")

    project_root = Path(__file__).parent.parent
    test_dir = project_root / "test_data_mixed"
    test_dir.mkdir(exist_ok=True)

    try:
        archive_path = test_dir / "mixed_content.zip"

        # 创建包含混合内容的压缩文件
        content = {
            "RJ123456/info.txt": "RJ内容",
            "other_folder/data.txt": "其他内容",
            "readme.txt": "说明文件",
        }
        create_test_archive(archive_path, content)

        # 处理
        processor = ArchiveProcessor(test_dir, log_to_file=False)
        result = processor.process_archive(archive_path)

        # 验证结果
        assert result, "处理应该成功"
        assert not archive_path.exists(), "原压缩文件应该被删除"

        # 查找日期目录
        date_dirs = [
            d for d in test_dir.iterdir() if d.is_dir() and d.name.startswith("2")
        ]
        assert len(date_dirs) == 1, "应该有一个日期目录"

        date_dir = date_dirs[0]
        assert (date_dir / "RJ123456").exists(), "RJ文件夹应该在日期目录中"
        assert (date_dir / "other_folder").exists(), "其他文件夹应该在日期目录中"
        assert (date_dir / "readme.txt").exists(), "文件应该在日期目录中"
        assert (date_dir / "processing_log.txt").exists(), "应该有处理日志"

        print("✓ 混合内容处理测试通过")
        return True

    finally:
        if test_dir.exists():
            try:
                shutil.rmtree(test_dir)
            except Exception:
                pass


def test_file_type_detection():
    """测试文件类型检测"""
    print("=== 测试文件类型检测 ===")

    project_root = Path(__file__).parent.parent
    test_dir = project_root / "test_data_detection"
    test_dir.mkdir(exist_ok=True)

    try:
        processor = ArchiveProcessor(test_dir, log_to_file=False)

        # 创建测试文件
        zip_file = test_dir / "test.zip"
        with zipfile.ZipFile(zip_file, "w") as zf:
            zf.writestr("test.txt", "测试内容")

        # 测试ZIP文件检测
        detected_type = processor._detect_file_type(zip_file)
        assert detected_type == ".zip", f"ZIP文件检测失败: {detected_type}"

        # 测试无扩展名文件
        no_ext_file = test_dir / "noextension"
        zip_file.rename(no_ext_file)

        detected_type = processor._detect_file_type(no_ext_file)
        assert detected_type == ".zip", f"无扩展名ZIP文件检测失败: {detected_type}"

        # 测试普通文件
        text_file = test_dir / "test.txt"
        text_file.write_text("普通文本文件")

        detected_type = processor._detect_file_type(text_file)
        assert detected_type is None, f"普通文件应该返回None: {detected_type}"

        print("✓ 文件类型检测测试通过")
        return True

    finally:
        if test_dir.exists():
            try:
                shutil.rmtree(test_dir)
            except Exception:
                pass


def main():
    """主函数"""
    print("开始核心功能测试...")
    print("=" * 50)

    try:
        tests = [
            test_rj_folders,
            test_single_folder_rename,
            test_mixed_content,
            test_file_type_detection,
        ]

        passed = 0
        for test_func in tests:
            try:
                if test_func():
                    passed += 1
            except Exception as e:
                print(f"❌ 测试 {test_func.__name__} 失败: {e}")

        print(f"\n✅ 核心功能测试完成: {passed}/{len(tests)} 通过")
        return 0 if passed == len(tests) else 1

    except Exception as e:
        print(f"❌ 核心功能测试异常: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
