#!/usr/bin/env python3
"""
密码处理测试
测试各种密码提取和处理功能，包括：
- 基本密码提取
- 空格密码处理
- 多层密码处理
- 密码文件名清理
"""

import sys
from pathlib import Path

# 添加src目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from src.helper import ArchiveProcessor


def test_basic_password_extraction():
    """测试基本密码提取"""
    print("=== 测试基本密码提取 ===")

    project_root = Path(__file__).parent.parent
    test_dir = project_root / "test_data_basic_pass"
    test_dir.mkdir(exist_ok=True)

    try:
        processor = ArchiveProcessor(test_dir, log_to_file=False)

        test_cases = [
            ("RJ123456 pass-password123.zip", "password123", "RJ123456.zip"),
            ("test pass-simple.rar", "simple", "test.rar"),
            ("archive pass-complex_pass.7z", "complex_pass", "archive.7z"),
            ("normal.zip", None, "normal.zip"),  # 无密码
        ]

        all_passed = True

        for filename, expected_password, expected_clean in test_cases:
            test_path = test_dir / filename
            password, clean_name = processor._extract_password_from_filename(test_path)

            print(f"  测试: {filename}")
            print(f"    提取密码: '{password}' (预期: '{expected_password}')")
            print(f"    清理文件名: '{clean_name}' (预期: '{expected_clean}')")

            if password != expected_password or clean_name != expected_clean:
                print(f"    ❌ 失败")
                all_passed = False
            else:
                print(f"    ✓ 通过")

        return all_passed

    finally:
        import shutil

        if test_dir.exists():
            try:
                shutil.rmtree(test_dir)
            except Exception:
                pass


def test_space_password_handling():
    """测试空格密码处理"""
    print("=== 测试空格密码处理 ===")

    project_root = Path(__file__).parent.parent
    test_dir = project_root / "test_data_space_pass"
    test_dir.mkdir(exist_ok=True)

    try:
        processor = ArchiveProcessor(test_dir, log_to_file=False)

        test_cases = [
            # 基本空格密码
            ("RJ123456 pass-(my password).zip", "my password", "RJ123456.zip"),
            (
                "test pass-(password with spaces).rar",
                "password with spaces",
                "test.rar",
            ),
            # 混合密码 - 空格密码和普通密码
            (
                "RJ123456 pass-(first password) second.zip",
                "first password",
                "RJ123456 pass-second.zip",
            ),
            (
                "test pass-simple (password with spaces).rar",
                "simple",
                "test pass-(password with spaces).rar",
            ),
            # 多个空格密码
            (
                "RJ123456 pass-(password 1) (password 2).zip",
                "password 1",
                "RJ123456 pass-(password 2).zip",
            ),
            # 边界情况
            ("RJ123456 pass-().zip", "", "RJ123456.zip"),  # 空括号
            ("test pass-(single).rar", "single", "test.rar"),  # 单词但在括号中
        ]

        all_passed = True

        for filename, expected_password, expected_clean in test_cases:
            test_path = test_dir / filename
            password, clean_name = processor._extract_password_from_filename(test_path)

            print(f"  测试: {filename}")
            print(f"    提取密码: '{password}' (预期: '{expected_password}')")
            print(f"    清理文件名: '{clean_name}' (预期: '{expected_clean}')")

            if password != expected_password or clean_name != expected_clean:
                print(f"    ❌ 失败")
                all_passed = False
            else:
                print(f"    ✓ 通过")

        return all_passed

    finally:
        import shutil

        if test_dir.exists():
            try:
                shutil.rmtree(test_dir)
            except Exception:
                pass


def test_password_parsing_internals():
    """测试密码解析内部逻辑"""
    print("=== 测试密码解析内部逻辑 ===")

    project_root = Path(__file__).parent.parent
    test_dir = project_root / "test_data_parse_internals"
    test_dir.mkdir(exist_ok=True)

    try:
        processor = ArchiveProcessor(test_dir, log_to_file=False)

        test_cases = [
            ("password1 password2", ["password1", "password2"]),
            ("(password with spaces)", ["password with spaces"]),
            (
                "simple (password with spaces) final",
                ["simple", "password with spaces", "final"],
            ),
            ("(first pass) (second pass)", ["first pass", "second pass"]),
            ("", []),
            ("single", ["single"]),
            ("()", [""]),  # 空括号
            ("  spaced  ", ["spaced"]),  # 处理额外空格
        ]

        all_passed = True

        for password_part, expected_passwords in test_cases:
            result = processor._parse_passwords(password_part)

            print(f"  测试: '{password_part}'")
            print(f"    结果: {result}")
            print(f"    预期: {expected_passwords}")

            if result != expected_passwords:
                print(f"    ❌ 解析错误")
                all_passed = False
            else:
                print(f"    ✓ 通过")

        return all_passed

    finally:
        import shutil

        if test_dir.exists():
            try:
                shutil.rmtree(test_dir)
            except Exception:
                pass


def test_multilayer_passwords():
    """测试多层密码处理"""
    print("=== 测试多层密码处理 ===")

    project_root = Path(__file__).parent.parent
    test_dir = project_root / "test_data_multilayer"
    test_dir.mkdir(exist_ok=True)

    try:
        processor = ArchiveProcessor(test_dir, log_to_file=False)

        test_cases = [
            # 多层普通密码
            ("test pass-first second third.zip", "first", "test pass-second third.zip"),
            # 第一层是空格密码，后续是普通密码
            (
                "RJ123456 pass-(outer password) inner1 inner2.zip",
                "outer password",
                "RJ123456 pass-inner1 inner2.zip",
            ),
            # 第一层是普通密码，后续有空格密码
            (
                "test pass-outer (inner password) final.rar",
                "outer",
                "test pass-(inner password) final.rar",
            ),
            # 多个空格密码
            (
                "RJ123456 pass-(layer 1) (layer 2) (layer 3).7z",
                "layer 1",
                "RJ123456 pass-(layer 2) (layer 3).7z",
            ),
        ]

        all_passed = True

        for filename, expected_password, expected_clean in test_cases:
            test_path = test_dir / filename
            password, clean_name = processor._extract_password_from_filename(test_path)

            print(f"  测试: {filename}")
            print(f"    提取密码: '{password}' (预期: '{expected_password}')")
            print(f"    清理文件名: '{clean_name}' (预期: '{expected_clean}')")

            if password != expected_password or clean_name != expected_clean:
                print(f"    ❌ 失败")
                all_passed = False
            else:
                print(f"    ✓ 通过")

        return all_passed

    finally:
        import shutil

        if test_dir.exists():
            try:
                shutil.rmtree(test_dir)
            except Exception:
                pass


def main():
    """主函数"""
    print("开始密码处理测试...")
    print("=" * 50)

    try:
        tests = [
            test_basic_password_extraction,
            test_space_password_handling,
            test_password_parsing_internals,
            test_multilayer_passwords,
        ]

        passed = 0
        for test_func in tests:
            try:
                if test_func():
                    passed += 1
            except Exception as e:
                print(f"❌ 测试 {test_func.__name__} 失败: {e}")

        print(f"\n✅ 密码处理测试完成: {passed}/{len(tests)} 通过")
        return 0 if passed == len(tests) else 1

    except Exception as e:
        print(f"❌ 密码处理测试异常: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
