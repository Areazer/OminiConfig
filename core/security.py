"""
core/security.py

安全工具模块：提供路径沙箱校验与跨平台原子文件写入功能。

设计原则：
1. 路径安全：绝不信任前端传入的路径，必须经过严格规范化与沙箱校验
2. 原子写入：使用临时文件 + os.replace 模式，保证在系统崩溃或并发场景下的数据完整性
3. 跨平台兼容：同时支持 Windows（NTFS）和类 Unix 系统（ext4/xfs/apfs）的原子操作语义
"""

import os
import platform
import tempfile
import hashlib
from pathlib import Path
from typing import Union, Optional, Tuple
from contextlib import contextmanager
from datetime import datetime

from fastapi import HTTPException, status


class SecurityError(HTTPException):
    """
    安全异常基类

    继承自 FastAPI 的 HTTPException，专门用于路径安全相关的错误。
    使用 403 Forbidden 状态码表示客户端无权访问指定路径。
    """

    def __init__(self, detail: str) -> None:
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "Security Violation", "message": detail},
        )


class PathSecurityValidator:
    """
    路径安全校验器

    采用白名单机制，将前端传入的路径严格限制在预设的 WORKSPACE_DIR 根目录内。
    防御目标：路径穿越攻击（Path Traversal）、符号链接劫持、空字节注入等。

    核心算法：
    1. 规范化：使用 Path.resolve() 消除 . 和 ..，并解析符号链接
    2. 前缀匹配：使用 commonpath() 确保解析后的路径位于白名单根目录之下
    """

    def __init__(self, workspace_dir: Union[str, Path]) -> None:
        """
        初始化路径安全校验器

        Args:
            workspace_dir: 允许访问的根目录绝对路径
        """
        # 使用 resolve() 确保是绝对路径且不存在符号链接歧义
        self._workspace = Path(workspace_dir).resolve()

        if not self._workspace.is_dir():
            raise ValueError(f"WORKSPACE_DIR 必须是已存在的目录: {self._workspace}")

    def validate(self, source_path: str) -> Path:
        """
        校验并规范化用户传入的路径

        安全策略：
        1. 拒绝包含空字节的路径（防止空字节注入攻击）
        2. 拒绝绝对路径（强制使用相对路径，避免误操作系统根目录）
        3. 规范化路径并解析所有符号链接
        4. 严格校验最终路径必须位于 WORKSPACE_DIR 之下

        Args:
            source_path: 前端传入的原始路径字符串

        Returns:
            Path: 规范化后的绝对路径对象

        Raises:
            SecurityError: 当检测到路径穿越攻击时抛出 403 异常
        """
        # 防御空字节注入（CVE-2006-7243 等）
        if "\x00" in source_path:
            raise SecurityError("路径中包含非法空字节字符")

        # 防御绝对路径攻击：禁止直接访问 /etc/passwd 或 C:\Windows\System32
        if source_path.startswith("/") or (
            len(source_path) > 1 and source_path[1] == ":"
        ):
            raise SecurityError("禁止使用绝对路径，请使用相对于工作目录的相对路径")

        # 构建目标路径并规范化（resolve 会处理 . 和 ..，并跟随符号链接）
        try:
            target_path = (self._workspace / source_path).resolve()
        except (OSError, ValueError) as e:
            raise SecurityError(f"路径解析失败: {str(e)}")

        # 关键防御：使用 commonpath 进行前缀匹配
        # 这比简单的 startswith 更安全，能正确处理路径边界（如 /workspace 和 /workspace2 的区别）
        try:
            common = os.path.commonpath([str(self._workspace), str(target_path)])
            if common != str(self._workspace):
                raise SecurityError(
                    f"检测到路径穿越攻击: '{source_path}' 解析后试图访问工作目录之外的区域"
                )
        except ValueError:
            # commonpath 在不同驱动器（Windows）上会抛出 ValueError
            raise SecurityError("非法路径：试图访问不同卷或驱动器")

        return target_path


class AtomicFileWriter:
    """
    跨平台原子文件写入器

    实现原理：
    1. 写入阶段：先将数据写入同目录下的临时文件（.tmp.{uuid}）
    2. 提交阶段：使用 os.replace() 原子性地将临时文件重命名为目标文件

    为什么使用 os.replace 而非 os.rename？
    - os.rename: 在 Windows 上，如果目标文件已存在会抛出 FileExistsError
    - os.replace: POSIX 语义，始终原子性地覆盖目标文件，跨平台行为一致
    - 在类 Unix 系统上，两者都是原子操作；在 Windows 上，os.replace 是原子操作的最佳实践

    并发安全保证：
    - 读取者要么看到旧文件完整内容，要么看到新文件完整内容，绝不会看到半写入状态
    - 即使进程在写入中途崩溃，临时文件也不会污染目标文件
    """

    @staticmethod
    async def write_atomic(
        file_path: Path,
        content: Union[str, bytes],
        mode: str = "w",
        encoding: str = "utf-8",
        newline: Optional[str] = None,
    ) -> None:
        """
        原子性地写入文件

        Args:
            file_path: 目标文件路径（必须是已校验的安全路径）
            content: 要写入的内容（字符串或字节）
            mode: 文件打开模式，'w' 表示文本，'wb' 表示二进制
            encoding: 文本模式下的编码，默认 UTF-8
            newline: 控制换行符处理，None 表示使用系统默认

        Raises:
            OSError: 当文件系统操作失败时抛出
        """
        import anyio

        # 使用 anyio.to_thread 将同步 I/O 操作 offload 到线程池
        # 避免阻塞 FastAPI 的主事件循环
        await anyio.to_thread.run_sync(
            AtomicFileWriter._sync_write_atomic,
            file_path,
            content,
            mode,
            encoding,
            newline,
        )

    @staticmethod
    def _sync_write_atomic(
        file_path: Path,
        content: Union[str, bytes],
        mode: str,
        encoding: str,
        newline: Optional[str],
    ) -> None:
        """
        同步版本的原子写入（在线程池中执行）
        """
        # 确保父目录存在
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # 创建临时文件：使用 uuid 避免并发冲突，使用 delete=False 确保我们能控制文件生命周期
        fd = None
        temp_path = None

        try:
            # 使用 tempfile.mkstemp 确保临时文件在同一文件系统（支持原子 rename）
            # dir=file_path.parent 确保临时文件与目标文件在同一挂载点
            fd, temp_path_str = tempfile.mkstemp(
                suffix=".tmp", prefix=f".{file_path.name}.", dir=str(file_path.parent)
            )
            temp_path = Path(temp_path_str)

            # 写入内容
            if "b" in mode:
                # 二进制模式
                if isinstance(content, str):
                    content = content.encode(encoding)
                os.write(fd, content)
            else:
                # 文本模式：使用 io 模块处理编码
                import io

                os.close(fd)  # 关闭文件描述符，使用文件对象写入
                fd = None
                with io.open(temp_path, mode, encoding=encoding, newline=newline) as f:
                    f.write(content)
                    f.flush()
                    # fsync 确保数据落盘，避免系统崩溃时数据丢失
                    os.fsync(f.fileno())

            if fd is not None:
                # 二进制模式下需要手动 fsync
                os.fsync(fd)
                os.close(fd)
                fd = None

            # 原子性地替换目标文件
            # 这是整个操作的关键：在 POSIX 和 Windows 上都是原子操作
            os.replace(str(temp_path), str(file_path))

            # 同步目录，确保文件系统元数据更新
            dir_fd = os.open(str(file_path.parent), os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(dir_fd)
            finally:
                os.close(dir_fd)

        except Exception:
            # 发生任何异常时，尝试清理临时文件
            if fd is not None:
                try:
                    os.close(fd)
                except OSError:
                    pass
            if temp_path and temp_path.exists():
                try:
                    temp_path.unlink()
                except OSError:
                    pass
            raise

    @staticmethod
    async def compute_file_hash(file_path: Path, algorithm: str = "sha256") -> str:
        """
        异步计算文件的哈希值（用于乐观锁的版本校验）

        Args:
            file_path: 目标文件路径
            algorithm: 哈希算法，默认 sha256

        Returns:
            str: 小写的十六进制哈希字符串
        """
        import anyio

        return await anyio.to_thread.run_sync(
            AtomicFileWriter._sync_compute_hash, file_path, algorithm
        )

    @staticmethod
    def _sync_compute_hash(file_path: Path, algorithm: str) -> str:
        """同步版本的哈希计算"""
        if not file_path.exists():
            # 文件不存在时返回空哈希（用于初始化场景）
            return hashlib.new(algorithm, b"").hexdigest()

        hash_obj = hashlib.new(algorithm)
        with open(file_path, "rb") as f:
            # 分块读取，避免大文件占用过多内存
            for chunk in iter(lambda: f.read(8192), b""):
                hash_obj.update(chunk)

        return hash_obj.hexdigest()


class ConfigMeta:
    """
    配置元数据工具类

    封装配置文件的元信息获取逻辑，包括版本哈希和最后修改时间。
    """

    @staticmethod
    async def get_meta(file_path: Path) -> Tuple[str, float]:
        """
        获取配置文件的元数据

        Returns:
            Tuple[str, float]: (version_hash, last_modified_timestamp)
        """
        import anyio

        return await anyio.to_thread.run_sync(ConfigMeta._sync_get_meta, file_path)

    @staticmethod
    def _sync_get_meta(file_path: Path) -> Tuple[str, float]:
        """同步获取元数据"""
        version_hash = AtomicFileWriter._sync_compute_hash(file_path, "sha256")

        if file_path.exists():
            last_modified = file_path.stat().st_mtime
        else:
            last_modified = datetime.now().timestamp()

        return version_hash, last_modified
