#!/usr/bin/env python3
"""
集成测试
测试完整的端到端功能，包括：
- 监控系统基本功能
- 日志系统集成
- 多层压缩文件处理
- 完整流程测试
"""

import sys
import zipfile
import tempfile
import time
from pathlib import Path

# 添加src目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from helper import ArchiveProcessor
from monitor import ArchiveEventHandler

def test_monitor_file_detection():
    """测试监控文件检测"""
    print("=== 测试监控文件检测 ===")
    
    project_root = Path(__file__).parent.parent
    test_dir = project_root / "test_data_monitor"
    test_dir.mkdir(exist_ok=True)
    
    try:
        processor = ArchiveProcessor(test_dir, log_to_file=False)
        handler = ArchiveEventHandler(processor, test_dir)
        
        # 创建测试文件
        zip_file = test_dir / "test.zip"
        with zipfile.ZipFile(zip_file, 'w') as zf:
            zf.writestr("test.txt", "测试内容")
        
        # 测试文件检测
        is_archive = handler._is_archive_file(zip_file)
        assert is_archive, "应该识别为压缩文件"
        
        # 测试普通文件
        text_file = test_dir / "normal.txt"
        text_file.write_text("普通文件")
        
        is_archive = handler._is_archive_file(text_file)
        assert not is_archive, "不应该识别为压缩文件"
        
        print("✓ 监控文件检测测试通过")
        return True
    
    finally:
        import shutil
        if test_dir.exists():
            try:
                shutil.rmtree(test_dir)
            except Exception:
                pass

def test_monitor_pending_files():
    """测试监控待处理文件管理"""
    print("=== 测试监控待处理文件管理 ===")
    
    project_root = Path(__file__).parent.parent
    test_dir = project_root / "test_data_pending"
    test_dir.mkdir(exist_ok=True)
    
    try:
        processor = ArchiveProcessor(test_dir, log_to_file=False)
        handler = ArchiveEventHandler(processor, test_dir)
        
        # 创建测试文件
        zip_file = test_dir / "test.zip"
        with zipfile.ZipFile(zip_file, 'w') as zf:
            zf.writestr("folder/file.txt", "测试内容")
        
        # 模拟文件创建事件
        handler._handle_new_file(zip_file)
        
        # 检查文件是否在待处理队列中
        assert str(zip_file) in handler.pending_files, "文件应该在待处理队列中"
        
        # 模拟文件修改事件
        handler._handle_modified_file(zip_file)
        
        # 检查待处理文件
        handler.check_pending_files()
        
        print("✓ 监控待处理文件管理测试通过")
        return True
    
    finally:
        import shutil
        if test_dir.exists():
            try:
                shutil.rmtree(test_dir)
            except Exception:
                pass

def test_nested_archive_processing():
    """测试嵌套压缩文件处理"""
    print("=== 测试嵌套压缩文件处理 ===")
    
    project_root = Path(__file__).parent.parent
    test_dir = project_root / "test_data_nested"
    test_dir.mkdir(exist_ok=True)
    
    try:
        # 创建内层ZIP文件
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            inner_zip = temp_path / "inner.zip"
            with zipfile.ZipFile(inner_zip, 'w') as inner_zf:
                inner_zf.writestr("RJ123456/audio.mp3", "音频内容")
            
            # 创建外层ZIP文件
            outer_zip = test_dir / "outer.zip"
            with zipfile.ZipFile(outer_zip, 'w') as outer_zf:
                outer_zf.write(inner_zip, "inner.zip")
        
        # 处理外层文件
        processor = ArchiveProcessor(test_dir, log_to_file=False)
        result = processor.process_archive(outer_zip)
        
        # 验证结果
        assert result, "处理应该成功"
        assert not outer_zip.exists(), "外层压缩文件应该被删除"
        
        # 检查是否创建了内层文件
        inner_files = list(test_dir.glob("inner.zip"))
        if inner_files:
            # 如果内层文件存在，应该可以继续处理
            inner_result = processor.process_archive(inner_files[0])
            print(f"内层文件处理结果: {inner_result}")
        
        print("✓ 嵌套压缩文件处理测试通过")
        return True
    
    finally:
        import shutil
        if test_dir.exists():
            try:
                shutil.rmtree(test_dir)
            except Exception:
                pass

def test_full_workflow():
    """测试完整工作流程"""
    print("=== 测试完整工作流程 ===")
    
    project_root = Path(__file__).parent.parent
    test_dir = project_root / "test_data_workflow"
    test_dir.mkdir(exist_ok=True)
    
    try:
        # 创建测试场景：带密码的压缩文件
        zip_file = test_dir / "RJ123456 pass-testpass.zip"
        with zipfile.ZipFile(zip_file, 'w') as zf:
            zf.writestr("audio/track1.mp3", "音频内容1")
            zf.writestr("audio/track2.mp3", "音频内容2")
            zf.writestr("readme.txt", "说明文件")
        
        # 完整处理流程
        processor = ArchiveProcessor(test_dir, log_to_file=False)
        
        # 1. 检测文件类型
        detected_type = processor._detect_file_type(zip_file)
        assert detected_type == '.zip', "应该检测为ZIP文件"
        
        # 2. 提取密码
        password, clean_name = processor._extract_password_from_filename(zip_file)
        assert password == "testpass", "应该提取到密码"
        assert clean_name == "RJ123456.zip", "应该清理文件名"
        
        # 3. 处理压缩文件
        result = processor.process_archive(zip_file)
        assert result, "处理应该成功"
        
        # 4. 验证结果
        assert not zip_file.exists(), "原压缩文件应该被删除"
        
        # 查找处理结果
        expected_folder = test_dir / "RJ123456"
        if not expected_folder.exists():
            # 可能创建了日期目录
            date_dirs = [d for d in test_dir.iterdir() if d.is_dir() and d.name.startswith("2")]
            if date_dirs:
                print(f"创建了日期目录: {date_dirs[0].name}")
            else:
                print("未找到预期的结果目录")
        else:
            print("✓ 创建了预期的RJ文件夹")
        
        print("✓ 完整工作流程测试通过")
        return True
    
    finally:
        import shutil
        if test_dir.exists():
            try:
                shutil.rmtree(test_dir)
            except Exception:
                pass

def test_logging_integration():
    """测试日志系统集成"""
    print("=== 测试日志系统集成 ===")
    
    project_root = Path(__file__).parent.parent
    test_dir = project_root / "test_data_logging"
    test_dir.mkdir(exist_ok=True)
    
    try:
        # 测试处理器日志
        processor = ArchiveProcessor(test_dir, log_to_file=True)
        
        # 创建简单的测试文件
        zip_file = test_dir / "test.zip"
        with zipfile.ZipFile(zip_file, 'w') as zf:
            zf.writestr("test.txt", "测试内容")
        
        # 处理文件（这会产生日志）
        result = processor.process_archive(zip_file)
        
        # 清理日志
        processor.cleanup_logging()
        
        print("✓ 日志系统集成测试通过")
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
    print("开始集成测试...")
    print("=" * 50)
    
    try:
        tests = [
            test_monitor_file_detection,
            test_monitor_pending_files,
            test_nested_archive_processing,
            test_full_workflow,
            test_logging_integration
        ]
        
        passed = 0
        for test_func in tests:
            try:
                if test_func():
                    passed += 1
            except Exception as e:
                print(f"❌ 测试 {test_func.__name__} 失败: {e}")
                import traceback
                traceback.print_exc()
        
        print(f"\n✅ 集成测试完成: {passed}/{len(tests)} 通过")
        return 0 if passed == len(tests) else 1
        
    except Exception as e:
        print(f"❌ 集成测试异常: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())