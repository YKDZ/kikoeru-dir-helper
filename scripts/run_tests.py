#!/usr/bin/env python3
"""
统一测试入口 - Kikoeru Directory Helper
自动发现并运行所有测试
"""

import sys
import logging
import importlib
import inspect
from pathlib import Path
from typing import List, Dict, Callable, Tuple

# 添加项目目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "tests"))
sys.path.insert(0, str(project_root / "src"))

# 测试类型定义
class TestResult:
    """测试结果类"""
    def __init__(self, name: str, description: str, passed: bool, error: str = None):
        self.name = name
        self.description = description
        self.passed = passed
        self.error = error

def discover_test_modules() -> Dict[str, str]:
    """
    自动发现测试模块
    
    Returns:
        Dict[str, str]: {module_name: description}
    """
    tests_dir = project_root / "tests"
    test_modules = {}
    
    # 定义测试模块和描述
    known_tests = {
        "compatibility_test": "依赖兼容性测试",
        "functional_tests": "功能测试",
        "test_space_passwords": "空格密码测试",
        "simple_test": "简化测试",
        "multilayer_test": "多层密码测试",
        "test_unknown_extensions": "未知扩展名测试"
    }
    
    # 扫描测试目录
    for test_file in tests_dir.glob("*.py"):
        if (test_file.name.startswith("test_") or 
            test_file.name.endswith("_test.py") or
            test_file.name.endswith("_tests.py")):
            module_name = test_file.stem
            if module_name != "__init__":
                description = known_tests.get(module_name, f"{module_name} 测试")
                test_modules[module_name] = description
    
    return test_modules

def run_test_module(module_name: str, description: str) -> TestResult:
    """
    运行单个测试模块
    
    Args:
        module_name: 模块名
        description: 测试描述
        
    Returns:
        TestResult: 测试结果
    """
    try:
        # 导入模块
        module = importlib.import_module(module_name)
        
        # 查找入口函数（优先级：main > run_all_tests > test_* 函数）
        entry_function = None
        
        # 1. 尝试 main 函数
        if hasattr(module, 'main'):
            entry_function = module.main
        # 2. 尝试 run_all_tests 函数
        elif hasattr(module, 'run_all_tests'):
            entry_function = module.run_all_tests
        # 3. 尝试查找 test_ 开头的函数
        else:
            for name, obj in inspect.getmembers(module):
                if (name.startswith('test_') and callable(obj) and 
                    not name.startswith('test_case')):
                    entry_function = obj
                    break
        
        if not entry_function:
            return TestResult(module_name, description, False, "未找到测试入口函数")
        
        # 运行测试
        print(f"\n📋 运行{description}...")
        
        # 检查函数签名，判断是否返回退出码
        sig = inspect.signature(entry_function)
        
        try:
            result = entry_function()
            
            # 如果函数返回了值，则作为退出码处理
            if result is not None:
                if isinstance(result, int):
                    success = result == 0
                else:
                    success = bool(result)
            else:
                # 无返回值表示成功
                success = True
            
            if success:
                print(f"✅ {description}通过")
                return TestResult(module_name, description, True)
            else:
                print(f"❌ {description}失败")
                return TestResult(module_name, description, False, f"测试返回错误码: {result}")
                
        except SystemExit as e:
            success = e.code == 0
            if success:
                print(f"✅ {description}通过")
                return TestResult(module_name, description, True)
            else:
                print(f"❌ {description}失败")
                return TestResult(module_name, description, False, f"SystemExit: {e.code}")
        
    except ImportError as e:
        error_msg = f"模块导入失败: {e}"
        print(f"❌ {description}异常: {error_msg}")
        return TestResult(module_name, description, False, error_msg)
    except Exception as e:
        error_msg = f"测试运行异常: {e}"
        print(f"❌ {description}异常: {error_msg}")
        return TestResult(module_name, description, False, error_msg)

def main():
    """主函数 - 自动发现并运行所有测试"""
    print("=" * 60)
    print("Kikoeru Directory Helper - 统一测试入口")
    print("=" * 60)
    
    # 设置日志级别
    logging.basicConfig(level=logging.WARNING)
    
    # 自动发现测试模块
    test_modules = discover_test_modules()
    
    if not test_modules:
        print("⚠️ 未发现任何测试模块")
        return 1
    
    print(f"\n🔍 发现 {len(test_modules)} 个测试模块:")
    for module_name, description in test_modules.items():
        print(f"  - {module_name}: {description}")
    
    # 运行所有测试
    test_results = []
    all_tests_passed = True
    
    for module_name, description in test_modules.items():
        result = run_test_module(module_name, description)
        test_results.append(result)
        if not result.passed:
            all_tests_passed = False
    
    # 生成测试报告
    print("\n" + "=" * 60)
    print("测试报告")
    print("=" * 60)
    
    passed_count = 0
    for result in test_results:
        status = "✅ 通过" if result.passed else "❌ 失败"
        print(f"{result.description:25} {status}")
        
        if result.passed:
            passed_count += 1
        elif result.error:
            print(f"{'':27} 错误: {result.error}")
    
    print("-" * 60)
    total_count = len(test_results)
    print(f"测试结果: {passed_count}/{total_count} 通过")
    
    if all_tests_passed:
        print("\n🎉 所有测试通过！系统可以正常使用。")
        return 0
    else:
        print("\n⚠️ 部分测试失败，请检查相关功能。")
        
        # 显示失败的测试详情
        failed_tests = [r for r in test_results if not r.passed]
        if failed_tests:
            print("\n失败的测试:")
            for result in failed_tests:
                print(f"  - {result.name}: {result.error or '未知错误'}")
        
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)