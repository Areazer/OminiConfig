"""
OminiConfig JSON Adapter - 配置管理适配器实现
"""

import os
import json
import hashlib
import shutil
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, Optional, Protocol
from dataclasses import dataclass
from datetime import datetime


class ConfigException(Exception):
    """基础配置异常"""

    pass


class ConfigNotFoundException(ConfigException):
    """配置文件不存在异常"""

    pass


class ConfigFormatException(ConfigException):
    """配置文件格式损坏异常"""

    pass


class ConcurrencyConflictException(ConfigException):
    """
    并发冲突异常

    Attributes:
        source_path: 发生冲突的配置路径
        expected_hash: 客户端期望的版本哈希
        actual_hash: 服务器端实际的版本哈希
    """

    def __init__(
        self,
        source_path: str,
        expected_hash: str,
        actual_hash: str,
        message: Optional[str] = None,
    ):
        self.source_path = source_path
        self.expected_hash = expected_hash
        self.actual_hash = actual_hash
        super().__init__(
            message
            or f"配置冲突: 路径 '{source_path}' 在读取后被修改. "
            f"期望哈希: {expected_hash[:8]}..., 实际哈希: {actual_hash[:8]}..."
        )


@dataclass(frozen=True)
class ConfigMeta:
    """配置元数据 - 不可变数据类"""

    version_hash: str
    last_modified: float

    def to_dict(self) -> Dict[str, Any]:
        return {"versionHash": self.version_hash, "lastModified": self.last_modified}


@dataclass(frozen=True)
class ConfigResult:
    """配置读取结果 - 不可变数据类"""

    data: Dict[str, Any]
    meta: ConfigMeta

    def to_dict(self) -> Dict[str, Any]:
        return {"data": self.data, "meta": self.meta.to_dict()}


class IOminiConfigAdapter(ABC):
    """
    OminiConfig 适配器抽象接口

    所有具体的配置适配器必须实现此接口
    """

    @abstractmethod
    def read_config(self, source_path: str) -> ConfigResult:
        """
        读取配置内容与元数据

        Args:
            source_path: 配置文件的相对或绝对路径

        Returns:
            ConfigResult: 包含数据和元数据的结果对象

        Raises:
            ConfigNotFoundException: 文件不存在（且无法初始化时）
            ConfigFormatException: 文件格式损坏
        """
        pass

    @abstractmethod
    def write_config(
        self, source_path: str, data: Dict[str, Any], old_version_hash: str
    ) -> bool:
        """
        保存配置，必须校验 old_version_hash

        Args:
            source_path: 配置文件路径
            data: 要保存的配置数据
            old_version_hash: 读取时的版本哈希，用于并发控制

        Returns:
            bool: 写入成功返回 True

        Raises:
            ConcurrencyConflictException: 版本哈希不匹配，说明文件被外部修改
            ConfigException: 其他配置相关错误
        """
        pass

    @abstractmethod
    def generate_schema(self, source_path: str) -> Dict[str, Any]:
        """
        根据现有配置，推导出符合 JSON Schema 规范的结构

        Args:
            source_path: 配置文件路径

        Returns:
            Dict[str, Any]: 符合 JSON Schema Draft-07 的结构定义
        """
        pass


class JsonConfigAdapter(IOminiConfigAdapter):
    """
    JSON 格式配置适配器实现

    支持特性:
    - 乐观并发控制 (Version Hash)
    - 原子文件写入 (临时文件 + 重命名)
    - 自动初始化空配置
    - 递归 Schema 推导
    - 完整的错误处理和堆栈信息
    """

    def __init__(self, base_dir: Optional[str] = None):
        """
        初始化适配器

        Args:
            base_dir: 配置文件的基准目录，默认当前目录
        """
        self._base_dir = Path(base_dir) if base_dir else Path.cwd()
        # 确保基准目录存在
        self._base_dir.mkdir(parents=True, exist_ok=True)

    def _get_full_path(self, source_path: str) -> Path:
        """获取完整路径"""
        path = Path(source_path)
        if path.is_absolute():
            return path
        return self._base_dir / source_path

    def _compute_hash(self, content: str) -> str:
        """计算内容的 SHA256 哈希作为版本标识"""
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def _compute_file_hash(self, file_path: Path) -> str:
        """计算文件的 SHA256 哈希"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()

    def _load_json_file(self, file_path: Path) -> Dict[str, Any]:
        """加载 JSON 文件，包含完整的错误处理"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                if not content.strip():
                    # 空文件，返回空配置
                    return {}
                return json.loads(content)
        except json.JSONDecodeError as e:
            # 提供详细的错误堆栈信息
            raise ConfigFormatException(
                f"JSON 格式错误在文件 '{file_path}': {e.msg} (行 {e.lineno}, 列 {e.colno})"
            ) from e
        except UnicodeDecodeError as e:
            raise ConfigFormatException(
                f"文件编码错误 '{file_path}': 期望 UTF-8 编码"
            ) from e
        except Exception as e:
            raise ConfigException(f"读取文件失败 '{file_path}': {str(e)}") from e

    def _atomic_write(self, file_path: Path, data: Dict[str, Any]) -> None:
        """
        原子写入文件

        使用临时文件 + 重命名确保写入的原子性，
        避免写入过程中断导致文件损坏
        使用唯一临时文件名避免并发冲突
        """
        import uuid

        temp_path = file_path.with_suffix(f".tmp.{uuid.uuid4().hex}")
        try:
            # 写入临时文件
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            # 原子重命名（覆盖原文件）
            shutil.move(str(temp_path), str(file_path))
        except Exception:
            # 清理临时文件
            if temp_path.exists():
                temp_path.unlink()
            raise

    def read_config(self, source_path: str) -> ConfigResult:
        """
        读取 JSON 配置

        如果文件不存在，自动初始化为空配置并返回
        """
        full_path = self._get_full_path(source_path)

        # 自动初始化：文件不存在时创建空配置
        if not full_path.exists():
            # 确保父目录存在
            full_path.parent.mkdir(parents=True, exist_ok=True)
            # 创建空配置
            empty_config = {}
            self._atomic_write(full_path, empty_config)

        if not full_path.is_file():
            raise ConfigNotFoundException(f"路径 '{source_path}' 不是文件")

        # 读取并解析配置
        data = self._load_json_file(full_path)

        # 验证数据类型
        if not isinstance(data, dict):
            raise ConfigFormatException(
                f"配置根必须是对象，但得到 {type(data).__name__}"
            )

        # 计算版本哈希和修改时间
        version_hash = self._compute_file_hash(full_path)
        last_modified = full_path.stat().st_mtime

        meta = ConfigMeta(version_hash=version_hash, last_modified=last_modified)

        return ConfigResult(data=data, meta=meta)

    def write_config(
        self, source_path: str, data: Dict[str, Any], old_version_hash: str
    ) -> bool:
        """
        写入 JSON 配置（带并发冲突校验）

        采用乐观并发控制策略：
        1. 读取当前文件的哈希值
        2. 与客户端提供的 old_version_hash 比较
        3. 如果不匹配，抛出 ConcurrencyConflictException
        4. 使用原子写入保存新配置
        """
        if not isinstance(data, dict):
            raise ConfigException(f"配置数据必须是对象，但得到 {type(data).__name__}")

        full_path = self._get_full_path(source_path)

        # 确保父目录存在
        full_path.parent.mkdir(parents=True, exist_ok=True)

        # 检查文件是否存在，如果存在则进行版本校验
        if full_path.exists():
            current_hash = self._compute_file_hash(full_path)

            if current_hash != old_version_hash:
                raise ConcurrencyConflictException(
                    source_path=source_path,
                    expected_hash=old_version_hash,
                    actual_hash=current_hash,
                )
        else:
            # 文件不存在时，要求 old_version_hash 为空或特定标记
            # 这表示客户端知道这是一个新文件
            pass

        # 原子写入
        self._atomic_write(full_path, data)

        return True

    def generate_schema(self, source_path: str) -> Dict[str, Any]:
        """
        递归推导 JSON Schema

        根据配置数据的实际值推断类型结构
        """
        # 先读取当前配置
        result = self.read_config(source_path)
        data = result.data

        # 递归生成 Schema
        schema = self._derive_schema(data)

        # 添加标准 JSON Schema 元数据
        schema["$schema"] = "http://json-schema.org/draft-07/schema#"
        schema["$id"] = f"file://{self._get_full_path(source_path)}"

        return schema

    def _derive_schema(
        self, value: Any, depth: int = 0, max_depth: int = 100
    ) -> Dict[str, Any]:
        """
        递归推导值对应的 JSON Schema

        Args:
            value: 任意值
            depth: 当前递归深度
            max_depth: 最大递归深度，防止栈溢出

        Returns:
            JSON Schema 定义字典
        """
        if depth > max_depth:
            return {"type": "object", "description": "递归深度超出限制"}

        if value is None:
            return {"type": "null"}

        if isinstance(value, bool):
            return {"type": "boolean"}

        if isinstance(value, (int, float)):
            # 整数和浮点数都映射为 number 类型
            return {"type": "number"}

        if isinstance(value, str):
            return {"type": "string"}

        if isinstance(value, list):
            if not value:
                return {"type": "array", "items": {}}

            # 递归推导数组元素类型
            # 简化处理：取第一个元素的类型作为所有元素的类型
            items_schema = self._derive_schema(value[0], depth + 1, max_depth)
            return {"type": "array", "items": items_schema}

        if isinstance(value, dict):
            properties = {}
            required = []

            for key, val in value.items():
                properties[key] = self._derive_schema(val, depth + 1, max_depth)
                # 所有键都标记为 required，除非是 null 值
                if val is not None:
                    required.append(key)

            result = {"type": "object", "properties": properties}
            result["required"] = required
            return result

        # 未知类型，标记为 any
        return {"type": "object", "description": f"未知类型: {type(value).__name__}"}
