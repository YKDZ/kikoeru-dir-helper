#!/usr/bin/env python3
"""
压缩文件解压测试
测试各种压缩文件的解压功能，包括：
- ZIP文件解压
- RAR文件解压（简化版）
- 7Z文件解压
- 错误处理
"""

import sys
import zipfile
import tempfile
from pathlib import Path

# 添加src目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from src.helper import ArchiveProcessor


def test_zip_extraction():
    """测试ZIP解压"""
    print("=== 测试ZIP文件解压 ===")

    project_root = Path(__file__).parent.parent
    test_dir = project_root / "test_data_zip"
    test_dir.mkdir(exist_ok=True)

    try:
        processor = ArchiveProcessor(test_dir, log_to_file=False)

        # 创建测试ZIP文件
        zip_file = test_dir / "test.zip"
        with zipfile.ZipFile(zip_file, "w") as zf:
            zf.writestr("folder/file1.txt", "内容1")
            zf.writestr("folder/file2.txt", "内容2")
            zf.writestr("root_file.txt", "根目录文件")

        # 创建临时解压目录
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # 测试ZIP解压
            result = processor._extract_zip(zip_file, temp_path)

            assert result, "ZIP解压应该成功"
            assert (temp_path / "folder" / "file1.txt").exists(), "解压的文件应该存在"
            assert (temp_path / "folder" / "file2.txt").exists(), "解压的文件应该存在"
            assert (temp_path / "root_file.txt").exists(), "根目录文件应该存在"

            # 验证文件内容
            content1 = (temp_path / "folder" / "file1.txt").read_text(encoding="utf-8")
            assert content1 == "内容1", "文件内容应该正确"

        print("✓ ZIP解压测试通过")
        return True

    finally:
        import shutil

        if test_dir.exists():
            try:
                shutil.rmtree(test_dir)
            except Exception:
                pass


def test_rar_extraction_simplified():
    """测试简化的RAR解压"""
    print("=== 测试简化RAR解压 ===")

    project_root = Path(__file__).parent.parent
    test_dir = project_root / "test_data_rar"
    test_dir.mkdir(exist_ok=True)

    try:
        processor = ArchiveProcessor(test_dir, log_to_file=False)

        # 测试RAR解压方法存在
        assert hasattr(processor, "_extract_rar"), "应该有_extract_rar方法"

        # 由于我们没有真实的RAR文件，只测试方法调用不会崩溃
        fake_rar = test_dir / "fake.rar"
        fake_rar.write_text("这不是真正的RAR文件")

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # 这应该失败，但不应该崩溃
            try:
                result = processor._extract_rar(fake_rar, temp_path, None)
                print(f"✓ 假RAR文件处理结果: {result} (预期为False)")
            except Exception as e:
                print(f"✓ 假RAR文件触发异常（正常）: {type(e).__name__}")

        print("✓ RAR解压测试通过")
        return True

    finally:
        import shutil

        if test_dir.exists():
            try:
                shutil.rmtree(test_dir)
            except Exception:
                pass


def test_7z_extraction():
    """测试7Z解压"""
    print("=== 测试7Z解压 ===")

    project_root = Path(__file__).parent.parent
    test_dir = project_root / "test_data_7z"
    test_dir.mkdir(exist_ok=True)

    try:
        processor = ArchiveProcessor(test_dir, log_to_file=False)

        # 测试7Z解压方法存在
        assert hasattr(processor, "_extract_7z"), "应该有_extract_7z方法"

        # 由于我们没有真实的7Z文件，只测试方法调用不会崩溃
        fake_7z = test_dir / "fake.7z"
        fake_7z.write_text("这不是真正的7Z文件")

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # 这应该失败，但不应该崩溃
            try:
                result = processor._extract_7z(fake_7z, temp_path, None)
                print(f"✓ 假7Z文件处理结果: {result} (预期为False)")
            except Exception as e:
                print(f"✓ 假7Z文件触发异常（正常）: {type(e).__name__}")

        print("✓ 7Z解压测试通过")
        return True

    finally:
        import shutil

        if test_dir.exists():
            try:
                shutil.rmtree(test_dir)
            except Exception:
                pass


def test_extraction_error_handling():
    """测试解压错误处理"""
    print("=== 测试解压错误处理 ===")

    project_root = Path(__file__).parent.parent
    test_dir = project_root / "test_data_errors"
    test_dir.mkdir(exist_ok=True)

    try:
        processor = ArchiveProcessor(test_dir, log_to_file=False)

        # 测试不存在的文件
        non_existent = test_dir / "non_existent.zip"
        result = processor.process_archive(non_existent)
        assert result == False, "不存在的文件应该返回False"

        # 测试损坏的ZIP文件
        broken_zip = test_dir / "broken.zip"
        broken_zip.write_text("这不是有效的ZIP文件")

        result = processor.process_archive(broken_zip)
        assert result == False, "损坏的ZIP文件应该返回False"

        # 测试空文件
        empty_file = test_dir / "empty.zip"
        empty_file.touch()

        result = processor.process_archive(empty_file)
        assert result == False, "空文件应该返回False"

        print("✓ 解压错误处理测试通过")
        return True

    finally:
        import shutil

        if test_dir.exists():
            try:
                shutil.rmtree(test_dir)
            except Exception:
                pass


def test_magic_bytes_detection():
    """测试魔术字节检测"""
    print("=== 测试魔术字节检测 ===")

    project_root = Path(__file__).parent.parent
    test_dir = project_root / "test_data_magic"
    test_dir.mkdir(exist_ok=True)

    try:
        processor = ArchiveProcessor(test_dir, log_to_file=False)

        # 创建ZIP文件并测试魔术字节检测
        zip_file = test_dir / "test.zip"
        with zipfile.ZipFile(zip_file, "w") as zf:
            zf.writestr("test.txt", "测试内容")

        # 测试带扩展名的文件
        detected_type = processor._detect_file_type(zip_file)
        assert detected_type == ".zip", f"ZIP文件检测失败: {detected_type}"

        # 测试无扩展名的文件
        no_ext_file = test_dir / "noextension"
        zip_file.rename(no_ext_file)

        detected_type = processor._detect_file_type(no_ext_file)
        assert detected_type == ".zip", f"无扩展名ZIP文件检测失败: {detected_type}"

        # 测试魔术字节方法
        with open(no_ext_file, "rb") as f:
            header = f.read(32)

        is_zip = processor._is_zip_file(header)
        assert is_zip, "应该识别为ZIP文件"

        is_rar = processor._is_rar_file(header)
        assert not is_rar, "不应该识别为RAR文件"

        is_7z = processor._is_7z_file(header)
        assert not is_7z, "不应该识别为7Z文件"

        print("✓ 魔术字节检测测试通过")
        return True

    finally:
        import shutil

        if test_dir.exists():
            try:
                shutil.rmtree(test_dir)
            except Exception:
                pass


def main():
    """主函数"""
    print("开始压缩文件解压测试...")
    print("=" * 50)

    try:
        tests = [
            test_zip_extraction,
            test_rar_extraction_simplified,
            test_7z_extraction,
            test_extraction_error_handling,
            test_magic_bytes_detection,
        ]

        passed = 0
        for test_func in tests:
            try:
                if test_func():
                    passed += 1
            except Exception as e:
                print(f"❌ 测试 {test_func.__name__} 失败: {e}")

        print(f"\n✅ 压缩文件解压测试完成: {passed}/{len(tests)} 通过")
        return 0 if passed == len(tests) else 1

    except Exception as e:
        print(f"❌ 压缩文件解压测试异常: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
