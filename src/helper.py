#!/usr/bin/env python3
"""
Kikoeru Directory Helper - 核心处理器
根据指定规则自动处理压缩文件
"""

import os
import re
import sys
import shutil
import logging
import tempfile
import zipfile
import rarfile
import py7zr
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Tuple, Union

# 导入统一日志配置
try:
    from .logger import setup_logger, cleanup_logger
except ImportError:
    sys.path.insert(0, os.path.dirname(__file__))
    from logger import setup_logger, cleanup_logger


class ArchiveProcessor:
    """压缩文件处理器"""

    def __init__(self, work_dir: Union[str, Path], log_to_file: bool = True):
        self.work_dir = Path(work_dir)

        # 初始化支持的压缩格式
        self.supported_formats = {".zip", ".rar", ".7z"}

        # 文件魔术字节检测映射
        self.magic_signatures = {
            b"PK\x03\x04": ".zip",  # ZIP文件头
            b"PK\x05\x06": ".zip",  # ZIP空文件头
            b"PK\x07\x08": ".zip",  # ZIP另一种头
            b"Rar!\x1a\x07\x00": ".rar",  # RAR 4.x文件头
            b"Rar!\x1a\x07\x01\x00": ".rar",  # RAR 5.x文件头
            b"7z\xbc\xaf'\x1c": ".7z",  # 7Z文件头
        }

        # 配置RAR解压工具
        self._configure_rar_tool()

        # 使用统一日志配置
        setup_logger(work_dir, "helper.log")

    def cleanup_logging(self):
        """清理日志处理器，释放文件句柄"""
        cleanup_logger()

    def _configure_rar_tool(self):
        """
        配置RAR解压工具路径
        """
        try:
            # 尝试常见的unrar工具路径
            possible_paths = [
                "/usr/local/bin/unrar",  # 官方下载安装路径
                "/usr/bin/unrar",  # 系统包管理器安装路径
                "/bin/unrar",  # 替代路径
                "unrar",  # PATH中的命令
            ]

            working_tool = None

            # 检测哪个路径可用
            for tool_path in possible_paths:
                try:
                    if tool_path == "unrar":
                        # 检查PATH中是否存在
                        found_path = shutil.which("unrar")
                        if found_path:
                            working_tool = found_path
                            break
                    else:
                        # 检查绝对路径是否存在
                        if Path(tool_path).exists():
                            working_tool = tool_path
                            break
                except Exception:
                    continue

            if working_tool:
                rarfile.UNRAR_TOOL = working_tool
                logging.info(f"🔧 RAR解压工具配置成功: {working_tool}")
            else:
                logging.warning(f"⚠️ 未找到unrar工具，将使用默认配置")

        except Exception as e:
            logging.warning(f"⚠️ 配置RAR工具时出错: {e}")

    def _detect_file_type(self, file_path: Path) -> Optional[str]:
        """
        检测文件类型，支持无扩展名文件

        Args:
            file_path: 文件路径

        Returns:
            Optional[str]: 检测到的文件类型（如.zip），如果不是压缩文件则返回none
        """
        try:
            # 如果是目录，直接返回None
            if file_path.is_dir():
                return None

            # 如果不是文件，也返回None
            if not file_path.is_file():
                return None

            # 先检查扩展名
            suffix = file_path.suffix.lower()
            if suffix in self.supported_formats:
                return suffix

            # 如果没有扩展名或不在支持列表中，尝试检测文件内容
            if not suffix or suffix not in self.supported_formats:
                return self._detect_by_magic_bytes(file_path)

            return None

        except Exception as e:
            logging.warning(f"检测文件类型失败 {file_path}: {e}")
            return None

    def _detect_by_magic_bytes(self, file_path: Path) -> Optional[str]:
        """
        通过魔术字节检测文件类型

        Args:
            file_path: 文件路径

        Returns:
            Optional[str]: 检测到的文件类型
        """
        try:
            with open(file_path, "rb") as f:
                # 读取文件前32字节用于签名检测
                header = f.read(32)

                # 检查魔术字节签名
                for signature, file_type in self.magic_signatures.items():
                    if header.startswith(signature):
                        logging.info(
                            f"通过魔术字节检测到文件类型: {file_path} -> {file_type}"
                        )
                        return file_type

                # 尝试使用python-magic库（如果可用）
                try:
                    import magic

                    mime_type = magic.from_buffer(header, mime=True)

                    if mime_type == "application/zip":
                        return ".zip"
                    elif mime_type == "application/x-rar-compressed":
                        return ".rar"
                    elif mime_type == "application/x-7z-compressed":
                        return ".7z"

                except ImportError:
                    # magic库不可用，使用手动检测
                    pass

                # 手动检测更多签名变体
                if self._is_zip_file(header):
                    return ".zip"
                elif self._is_rar_file(header):
                    return ".rar"
                elif self._is_7z_file(header):
                    return ".7z"

                return None

        except Exception as e:
            logging.warning(f"魔术字节检测失败 {file_path}: {e}")
            return None

    def _is_zip_file(self, header: bytes) -> bool:
        """检测ZIP文件签名"""
        zip_signatures = [
            b"PK\x03\x04",  # 普通ZIP
            b"PK\x05\x06",  # 空ZIP
            b"PK\x07\x08",  # 另一种ZIP签名
        ]
        return any(header.startswith(sig) for sig in zip_signatures)

    def _is_rar_file(self, header: bytes) -> bool:
        """检测RAR文件签名"""
        rar_signatures = [
            b"Rar!\x1a\x07\x00",  # RAR 4.x
            b"Rar!\x1a\x07\x01\x00",  # RAR 5.x
        ]
        return any(header.startswith(sig) for sig in rar_signatures)

    def _is_7z_file(self, header: bytes) -> bool:
        """检测7Z文件签名"""
        return header.startswith(b"7z\xbc\xaf'\x1c")

    def process_archive(self, archive_path: Path) -> bool:
        """
        处理压缩文件

        Args:
            archive_path: 压缩文件路径

        Returns:
            bool: 处理是否成功
        """
        try:
            logging.info(f"📦 开始处理压缩文件: {archive_path}")
            logging.info(
                f"📏 文件大小: {archive_path.stat().st_size / 1024 / 1024:.2f} MB"
            )

            # 检查文件是否存在
            if not archive_path.exists():
                logging.error(f"❌ 文件不存在: {archive_path}")
                return False

            # 检测文件类型（支持无扩展名文件）
            logging.info(f"🔍 开始检测文件类型...")
            detected_type = self._detect_file_type(archive_path)
            if not detected_type:
                logging.warning(f"⚠️ 不支持的文件类型或不是压缩文件: {archive_path}")
                return False

            logging.info(f"✅ 文件类型检测完成: {detected_type}")

            # 如果检测到的类型与文件名不符，更新文件名
            actual_suffix = archive_path.suffix.lower()
            if actual_suffix != detected_type:
                # 为无扩展名文件添加正确的扩展名
                new_path = archive_path.with_suffix(detected_type)
                if new_path != archive_path:
                    logging.info(
                        f"🏷️ 文件扩展名不符，重命名: {archive_path.name} -> {new_path.name}"
                    )
                    archive_path.rename(new_path)
                    archive_path = new_path

            # 提取密码信息
            logging.info(f"🔐 分析密码信息...")
            password, clean_filename = self._extract_password_from_filename(
                archive_path
            )
            if password:
                logging.info(f"🔑 检测到密码，将使用密码进行解压")
            else:
                logging.info(f"🔓 未检测到密码，将直接解压")

            # 如果文件名包含密码，重命名文件
            if password:
                new_path = archive_path.parent / clean_filename
                if new_path != archive_path:
                    logging.info(
                        f"🏷️ 移除密码后重命名: {archive_path.name} -> {clean_filename}"
                    )
                    archive_path.rename(new_path)
                    archive_path = new_path

            # 创建临时目录进行解压
            logging.info(f"📁 创建临时解压目录")
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                logging.info(f"📂 临时目录: {temp_path}")

                # 解压文件（使用检测到的类型）
                logging.info(f"🗜️ 开始解压文件到临时目录...")
                success = self._extract_archive_by_type(
                    archive_path, temp_path, detected_type, password
                )
                if not success:
                    logging.error(f"❌ 解压失败")
                    return False

                logging.info(f"✅ 解压完成")

                # 分析解压内容
                logging.info(f"📋 分析解压内容...")
                extracted_items = list(temp_path.iterdir())
                if not extracted_items:
                    logging.warning(f"⚠️ 压缩文件为空: {archive_path}")
                    self._delete_archive(archive_path)
                    return True

                logging.info(f"📊 解压内容统计: 共 {len(extracted_items)} 个项目")
                for i, item in enumerate(extracted_items, 1):
                    item_type = "文件夹" if item.is_dir() else "文件"
                    size_info = ""
                    if item.is_file():
                        size_mb = item.stat().st_size / 1024 / 1024
                        size_info = f" ({size_mb:.2f} MB)"
                    logging.info(f"  {i}. {item_type}: {item.name}{size_info}")

                # 应用处理规则
                logging.info(f"⚙️ 开始应用处理规则...")
                result = self._apply_rules(archive_path, extracted_items, temp_path)

                # 删除原压缩文件
                if result:
                    logging.info(f"🗑️ 处理成功，删除原压缩文件")
                    self._delete_archive(archive_path)
                    logging.info(f"✅ 压缩文件处理完成: {archive_path.name}")
                else:
                    logging.error(f"❌ 处理规则应用失败")

                return result

        except Exception as e:
            logging.error(f"处理压缩文件 {archive_path} 时发生错误: {e}")
            return False

    def _parse_passwords(self, password_part: str) -> List[str]:
        """
        解析密码部分，支持括号包裹的空格密码

        Args:
            password_part: 密码部分字符串，如 "password1 (password with spaces) password3"

        Returns:
            List[str]: 解析出的密码列表
        """
        passwords = []
        current_token = ""
        in_parentheses = False

        i = 0
        while i < len(password_part):
            char = password_part[i]

            if char == "(" and not in_parentheses:
                # 开始括号组
                if current_token.strip():
                    passwords.append(current_token.strip())
                    current_token = ""
                in_parentheses = True
            elif char == ")" and in_parentheses:
                # 结束括号组
                passwords.append(current_token.strip())  # 即使为空也要添加
                current_token = ""
                in_parentheses = False
            elif char == " " and not in_parentheses:
                # 空格分隔（不在括号内）
                if current_token.strip():
                    passwords.append(current_token.strip())
                    current_token = ""
            else:
                # 普通字符
                current_token += char

            i += 1

        # 处理最后一个token
        if current_token.strip():
            passwords.append(current_token.strip())

        return passwords

    def _extract_password_from_filename(
        self, file_path: Path
    ) -> Tuple[Optional[str], str]:
        """
        从文件名中提取密码信息
        支持格式：
        - RJ123456 pass-(password 1) (password 2) (password3).zip
        - RJ123456 pass-(password 1).zip

        Args:
            file_path: 文件路径

        Returns:
            Tuple[Optional[str], str]: (密码, 清理后的文件名)
        """
        filename = file_path.name
        
        # 查找密码模式: " pass-(password1) (password2) (password3)"
        pattern = r"\s+pass-((?:\([^)]+\)\s*)+)"
        match = re.search(pattern, filename, re.IGNORECASE)
        
        if not match:
            return None, filename
            
        password_part = match.group(1).strip()
        
        # 提取所有括号内的密码
        password_matches = re.findall(r"\(([^)]+)\)", password_part)
        
        if not password_matches:
            return None, filename
            
        # 第一个密码作为当前密码
        current_password = password_matches[0]
        
        # 剩余的密码
        remaining_passwords = password_matches[1:]
        
        # 构建清理后的文件名
        if remaining_passwords:
            # 保留剩余密码
            remaining_part = " ".join([f"({pwd})" for pwd in remaining_passwords])
            clean_filename = re.sub(
                pattern, f" pass-{remaining_part}", filename, flags=re.IGNORECASE
            )
        else:
            # 没有剩余密码，完全移除密码部分
            clean_filename = re.sub(pattern, "", filename, flags=re.IGNORECASE)
        
        return current_password, clean_filename

    def _extract_archive_by_type(
        self,
        archive_path: Path,
        extract_to: Path,
        file_type: str,
        password: Optional[str] = None,
    ) -> bool:
        """
        根据检测到的文件类型解压文件

        Args:
            archive_path: 压缩文件路径
            extract_to: 解压目标路径
            file_type: 检测到的文件类型
            password: 密码

        Returns:
            bool: 解压是否成功
        """
        try:
            logging.info(f"📦 解压方式: {file_type} 格式")
            if password:
                logging.info(f"🔑 使用密码解压")

            if file_type == ".zip":
                return self._extract_zip(archive_path, extract_to, password)
            elif file_type == ".rar":
                return self._extract_rar(archive_path, extract_to, password)
            elif file_type == ".7z":
                return self._extract_7z(archive_path, extract_to, password)
            else:
                logging.error(f"❌ 不支持的压缩格式: {file_type}")
                return False

        except Exception as e:
            logging.error(f"❌ 解压文件 {archive_path} 失败: {e}")
            return False

    def _extract_archive(
        self, archive_path: Path, extract_to: Path, password: Optional[str] = None
    ) -> bool:
        """
        解压文件（保留兼容性）

        Args:
            archive_path: 压缩文件路径
            extract_to: 解压目标路径
            password: 密码

        Returns:
            bool: 解压是否成功
        """
        try:
            suffix = archive_path.suffix.lower()
            return self._extract_archive_by_type(
                archive_path, extract_to, suffix, password
            )

        except Exception as e:
            logging.error(f"解压文件 {archive_path} 失败: {e}")
            return False

    def _extract_zip(
        self, archive_path: Path, extract_to: Path, password: Optional[str] = None
    ) -> bool:
        """解压ZIP文件"""
        try:
            logging.info(f"🗜️ 解压ZIP文件: {archive_path.name}")
            with zipfile.ZipFile(archive_path, "r") as zip_ref:
                if password:
                    zip_ref.setpassword(password.encode("utf-8"))
                    logging.info(f"🔑 ZIP密码设置成功")

                # 获取文件列表
                file_list = zip_ref.namelist()
                logging.info(f"📋 ZIP内部文件数量: {len(file_list)}")

                zip_ref.extractall(extract_to)
                logging.info(f"✅ ZIP解压完成")
            return True
        except Exception as e:
            logging.error(f"❌ 解压ZIP文件失败: {e}")
            return False

    def _extract_rar(
        self, archive_path: Path, extract_to: Path, password: Optional[str] = None
    ) -> bool:
        """解压RAR文件"""
        try:
            logging.info(f"🗜️ 解压RAR文件: {archive_path.name}")

            with rarfile.RarFile(archive_path, "r") as rar_ref:
                if password:
                    rar_ref.setpassword(password)
                    logging.info(f"🔑 RAR密码设置成功")

                # 获取文件列表
                file_list = rar_ref.namelist()
                logging.info(f"📋 RAR内部文件数量: {len(file_list)}")

                # 直接解压
                rar_ref.extractall(extract_to)
                logging.info(f"✅ RAR解压完成")
                return True

        except Exception as e:
            logging.error(f"❌ 解压RAR文件失败: {e}")
            return False

    def _extract_7z(
        self, archive_path: Path, extract_to: Path, password: Optional[str] = None
    ) -> bool:
        """解压7Z文件"""
        try:
            logging.info(f"🗜️ 解压7Z文件: {archive_path.name}")
            # py7zr 1.0.0+ 版本兼容性处理
            if password:
                logging.info(f"🔑 使用密码解压7Z文件")
                with py7zr.SevenZipFile(
                    archive_path, mode="r", password=password
                ) as sz_ref:
                    sz_ref.extractall(extract_to)
            else:
                with py7zr.SevenZipFile(archive_path, mode="r") as sz_ref:
                    sz_ref.extractall(extract_to)

            logging.info(f"✅ 7Z解压完成")
            return True
        except Exception as e:
            logging.error(f"❌ 解压7Z文件失败: {e}")
            # 尝试新版本的API（如果需要）
            try:
                logging.info(f"🔄 尝试使用新版本API")
                # 检查版本是否支持新API
                if hasattr(py7zr.SevenZipFile, "extract"):
                    with py7zr.SevenZipFile(archive_path) as sz_ref:
                        if password:
                            sz_ref.password = password
                        sz_ref.extractall(extract_to)
                    logging.info(f"✅ 7Z新API解压成功")
                    return True
            except Exception as e2:
                logging.error(f"❌ 7Z新API尝试也失败: {e2}")
            return False

    def _apply_rules(
        self, archive_path: Path, extracted_items: List[Path], temp_path: Path
    ) -> bool:
        """
        应用处理规则

        Args:
            archive_path: 原压缩文件路径
            extracted_items: 解压出的项目列表
            temp_path: 临时目录路径

        Returns:
            bool: 处理是否成功
        """
        try:
            archive_name = archive_path.stem
            logging.info(f"📝 压缩文件名: {archive_name}")

            # 递归处理压缩文件 - 使用新的检测方法
            logging.info(f"🔍 检查解压内容中是否包含压缩文件...")
            archive_files = []
            other_files = []

            for item in extracted_items:
                detected_type = self._detect_file_type(item)
                if detected_type:
                    archive_files.append(item)
                    logging.info(
                        f"  📦 发现内层压缩文件: {item.name} ({detected_type})"
                    )
                else:
                    other_files.append(item)
                    item_type = "文件夹" if item.is_dir() else "文件"
                    logging.info(f"  📝 非压缩{item_type}: {item.name}")

            # 规则：若解压出的内容全部都是压缩文件，则对每一个压缩文件都递归应用规则
            if archive_files and not other_files:
                logging.info(
                    f"🔄 规则匹配: 全部为压缩文件，递归处理 {len(archive_files)} 个文件"
                )

                # 检查是否需要传递密码
                original_name = archive_path.name
                has_remaining_passwords = " pass-" in original_name
                if has_remaining_passwords:
                    logging.info(f"🔑 检测到多层密码，将传递给内层文件")

                for archive_file in archive_files:
                    # 移动到工作目录
                    target_path = self.work_dir / archive_file.name

                    # 如果原始文件还有剩余密码，需要传递给内层文件
                    if has_remaining_passwords:
                        # 提取原始文件名中的剩余密码部分（去掉第一个密码后）
                        _, remaining_filename = self._extract_password_from_filename(
                            Path(original_name)
                        )
                        pass_pattern = r"\s+pass-([^.]+)"
                        match = re.search(
                            pass_pattern, remaining_filename, re.IGNORECASE
                        )
                        if match:
                            remaining_passwords = match.group(1).strip()
                            # 为内层文件添加剩余密码
                            file_stem = archive_file.stem
                            file_suffix = archive_file.suffix
                            new_name = (
                                f"{file_stem} pass-{remaining_passwords}{file_suffix}"
                            )
                            target_path = self.work_dir / new_name
                            logging.info(f"🔑 传递密码给内层文件: {new_name}")

                    logging.info(
                        f"📝 移动内层压缩文件: {archive_file.name} -> {target_path.name}"
                    )
                    shutil.move(str(archive_file), str(target_path))
                    # 递归处理
                    logging.info(f"🔄 递归处理: {target_path.name}")
                    self.process_archive(target_path)
                return True

            # 规则：若解压出的内容顶层包含压缩文件，且还包含任意非压缩文件
            if archive_files and other_files:
                logging.info(f"📋 规则匹配: 混合内容（包含压缩文件和其他文件）")
                return self._handle_mixed_content(archive_path, extracted_items)

            # 规则：若解压出的内容包含任意一个非文件夹
            non_dir_items = [item for item in extracted_items if not item.is_dir()]
            if non_dir_items:
                logging.info(
                    f"📝 规则匹配: 包含非文件夹项目 ({len(non_dir_items)} 个文件)"
                )
                return self._handle_mixed_content(archive_path, extracted_items)

            # 剩下的都是文件夹
            folders = [item for item in extracted_items if item.is_dir()]
            logging.info(f"📁 解压内容全部为文件夹: {len(folders)} 个")

            # 分析文件夹名称
            rj_folders = [f for f in folders if f.name.startswith("RJ")]
            non_rj_folders = [f for f in folders if not f.name.startswith("RJ")]

            logging.info(f"  🏷️ RJ开头文件夹: {len(rj_folders)} 个")
            logging.info(f"  📁 非RJ开头文件夹: {len(non_rj_folders)} 个")

            # 规则：若解压出的内容全部都是以RJ开头的文件夹
            if all(folder.name.startswith("RJ") for folder in folders):
                logging.info(f"✅ 规则匹配: 全部RJ文件夹，原样保留")
                return self._handle_rj_folders(folders)

            # 规则：若解压出的内容是一个不以RJ开头的文件夹，且压缩文件名以RJ开头
            if (
                len(folders) == 1
                and not folders[0].name.startswith("RJ")
                and archive_name.startswith("RJ")
            ):
                logging.info(f"✅ 规则匹配: 单个非RJ文件夹且压缩文件名以RJ开头，重命名")
                return self._handle_single_folder_rename(folders[0], archive_name)

            # 规则：若解压出的内容是多个文件夹，且有任意文件夹不以RJ开头
            if len(folders) > 1 and any(
                not folder.name.startswith("RJ") for folder in folders
            ):
                logging.info(f"📋 规则匹配: 多个文件夹且包含非RJ文件夹，移动到日期目录")
                return self._handle_mixed_content(archive_path, extracted_items)

            # 默认情况：移动到日期-文件名目录
            logging.info(f"📋 默认规则: 移动到日期目录")
            return self._handle_mixed_content(archive_path, extracted_items)

        except Exception as e:
            logging.error(f"应用规则时发生错误: {e}")
            return False

    def _handle_rj_folders(self, folders: List[Path]) -> bool:
        """处理全部以RJ开头的文件夹 - 原样保留"""
        try:
            logging.info(f"🏷️ 开始处理RJ文件夹: 原样保留 {len(folders)} 个文件夹")

            for i, folder in enumerate(folders, 1):
                target_path = self.work_dir / folder.name
                original_name = folder.name

                # 如果目标已存在，生成新名称
                if target_path.exists():
                    counter = 1
                    while target_path.exists():
                        target_path = self.work_dir / f"{folder.name}_{counter}"
                        counter += 1
                    logging.info(
                        f"  ⚠️ 目标已存在，重命名: {original_name} -> {target_path.name}"
                    )

                logging.info(
                    f"  {i}. 📁 移动RJ文件夹: {original_name} -> {target_path}"
                )
                shutil.move(str(folder), str(target_path))

            logging.info(f"✅ RJ文件夹处理完成")
            return True
        except Exception as e:
            logging.error(f"❌ 处理RJ文件夹时出错: {e}")
            return False

    def _handle_single_folder_rename(self, folder: Path, new_name: str) -> bool:
        """处理单个文件夹重命名"""
        try:
            logging.info(f"🏷️ 开始重命名单个文件夹: {folder.name} -> {new_name}")

            target_path = self.work_dir / new_name
            original_target = new_name

            # 如果目标已存在，生成新名称
            if target_path.exists():
                counter = 1
                while target_path.exists():
                    target_path = self.work_dir / f"{new_name}_{counter}"
                    counter += 1
                logging.info(f"  ⚠️ 目标名称已存在，修改为: {target_path.name}")

            logging.info(f"📁 移动文件夹: {folder.name} -> {target_path}")
            shutil.move(str(folder), str(target_path))

            logging.info(f"✅ 文件夹重命名完成")
            return True
        except Exception as e:
            logging.error(f"❌ 重命名文件夹时出错: {e}")
            return False

    def _handle_mixed_content(self, archive_path: Path, items: List[Path]) -> bool:
        """处理混合内容 - 移动到日期-文件名目录"""
        try:
            # 生成目标目录名
            date_str = datetime.now().strftime("%Y%m%d")
            archive_name = archive_path.stem
            target_dir_name = f"{date_str}-{archive_name}"
            target_dir = self.work_dir / target_dir_name

            logging.info(f"📋 开始处理混合内容")
            logging.info(f"📅 目标目录名: {target_dir_name}")

            # 如果目标目录已存在，添加序号
            counter = 1
            original_target = target_dir_name
            while target_dir.exists():
                target_dir = self.work_dir / f"{target_dir_name}_{counter}"
                counter += 1

            if counter > 1:
                logging.info(f"  ⚠️ 目标目录已存在，修改为: {target_dir.name}")

            # 创建目标目录
            logging.info(f"📁 创建目标目录: {target_dir}")
            target_dir.mkdir()

            # 移动所有内容
            logging.info(f"📁 移动内容到目标目录:")
            for i, item in enumerate(items, 1):
                target_path = target_dir / item.name
                item_type = "文件夹" if item.is_dir() else "文件"
                logging.info(f"  {i}. {item_type}: {item.name}")
                shutil.move(str(item), str(target_path))

            # 创建处理日志
            logging.info(f"📋 创建处理日志")
            self._create_processing_log(target_dir, archive_path, "需要手动处理")

            logging.info(f"✅ 混合内容处理完成: {target_dir}")
            return True

        except Exception as e:
            logging.error(f"❌ 处理混合内容时出错: {e}")
            return False

    def _create_processing_log(
        self, target_dir: Path, archive_path: Path, reason: str
    ) -> None:
        """创建处理日志文件"""
        try:
            log_file = target_dir / "processing_log.txt"
            with open(log_file, "w", encoding="utf-8") as f:
                f.write(f"Kikoeru Directory Helper 处理日志\n")
                f.write(f"=" * 50 + "\n")
                f.write(f"处理时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"原始文件: {archive_path.name}\n")
                f.write(f"处理原因: {reason}\n")
                f.write(f"目标目录: {target_dir.name}\n")
                f.write(f"\n注意：此目录需要手动检查和处理\n")

            logging.info(f"处理日志已创建: {log_file}")

        except Exception as e:
            logging.error(f"创建处理日志时出错: {e}")

    def _delete_archive(self, archive_path: Path) -> None:
        """删除压缩文件"""
        try:
            file_size = archive_path.stat().st_size / 1024 / 1024  # MB
            logging.info(f"🗑️ 删除压缩文件: {archive_path.name} ({file_size:.2f} MB)")
            archive_path.unlink()
            logging.info(f"✅ 压缩文件已删除")
        except Exception as e:
            logging.error(f"❌ 删除压缩文件时出错: {e}")


def main():
    """主函数，用于测试"""
    import sys

    if len(sys.argv) != 3:
        print("用法: python3 helper.py <工作目录> <压缩文件>")
        sys.exit(1)

    work_dir = sys.argv[1]
    archive_file = sys.argv[2]

    processor = ArchiveProcessor(work_dir)
    result = processor.process_archive(Path(archive_file))

    if result:
        print("处理成功")
    else:
        print("处理失败")
        sys.exit(1)


if __name__ == "__main__":
    main()
