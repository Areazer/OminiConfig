"""
core/adapter.py

适配器模块：定义配置管理器的抽象接口与多态实现。

设计模式应用：
1. 抽象基类 (ABC): 定义统一的 IOminiConfigAdapter 接口契约
2. 工厂模式 (Factory): 根据文件扩展名动态创建对应类型的适配器
3. 策略模式 (Strategy): 不同的文件格式（JSON/YAML/TOML）对应不同的解析策略

扩展性设计：
- 新增格式支持只需：继承 BaseConfigAdapter + 注册到工厂 + 添加路由
- 完全解耦业务逻辑与底层存储细节
"""

import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, Optional, Type, Protocol, runtime_checkable
from dataclasses import dataclass
from datetime import datetime

from fastapi import HTTPException, status


# ============================================================================
# 数据模型
# ============================================================================


@dataclass(frozen=True)
class ConfigMeta:
    """
    配置元数据 - 不可变数据类

    Attributes:
        version_hash: 用于乐观并发控制的版本哈希（SHA256）
        last_modified: Unix 时间戳，表示最后修改时间
    """

    version_hash: str
    last_modified: float

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于 JSON 序列化）"""
        return {"versionHash": self.version_hash, "lastModified": self.last_modified}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConfigMeta":
        """从字典构造"""
        return cls(
            version_hash=data.get("versionHash", ""),
            last_modified=data.get("lastModified", datetime.now().timestamp()),
        )


@dataclass(frozen=True)
class ConfigResult:
    """
    配置读取结果 - 不可变数据类

    Attributes:
        data: 配置数据字典
        meta: 配置元数据
    """

    data: Dict[str, Any]
    meta: ConfigMeta

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {"data": self.data, "meta": self.meta.to_dict()}


# ============================================================================
# 异常定义
# ============================================================================


class ConfigException(HTTPException):
    """基础配置异常"""

    def __init__(
        self, status_code: int, detail: str, error_type: str = "ConfigException"
    ) -> None:
        super().__init__(
            status_code=status_code, detail={"error": error_type, "message": detail}
        )


class ConfigNotFoundException(ConfigException):
    """配置文件不存在异常（HTTP 404）"""

    def __init__(self, source_path: str) -> None:
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"配置文件不存在: {source_path}",
            error_type="ConfigNotFoundException",
        )


class ConfigFormatException(ConfigException):
    """配置文件格式损坏异常（HTTP 422）"""

    def __init__(self, source_path: str, reason: str) -> None:
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"配置文件格式错误 '{source_path}': {reason}",
            error_type="ConfigFormatException",
        )


class ConcurrencyConflictException(ConfigException):
    """
    乐观并发冲突异常（HTTP 409）

    当客户端提供的 oldVersionHash 与服务器端当前文件的哈希不匹配时抛出。
    这意味着在客户端读取和尝试写入期间，文件被其他进程修改过。
    """

    def __init__(self, source_path: str, expected_hash: str, actual_hash: str) -> None:
        self.source_path = source_path
        self.expected_hash = expected_hash
        self.actual_hash = actual_hash

        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"配置冲突: 路径 '{source_path}' 在读取后被其他进程修改。"
                f"期望哈希: {expected_hash[:16]}..., "
                f"实际哈希: {actual_hash[:16]}..."
            ),
            error_type="ConcurrencyConflictException",
        )


# ============================================================================
# 抽象基类定义
# ============================================================================


class BaseConfigAdapter(ABC):
    """
    OminiConfig 适配器抽象基类

    定义所有配置适配器必须实现的接口契约。
    子类必须实现：
    - read_config: 读取配置内容与元数据
    - write_config: 原子性写入配置（带版本校验）
    - generate_schema: 根据数据推导 JSON Schema

    设计原则：
    1. 单一职责：每个适配器只负责一种文件格式的解析
    2. 无状态：适配器实例不持有配置状态，支持并发复用
    3. 防御性：输入输出都经过严格类型校验
    """

    # 类属性：此适配器支持的文件扩展名列表（如 ['.json']）
    supported_extensions: list[str] = []

    def __init__(self, workspace_dir: Path) -> None:
        """
        初始化适配器

        Args:
            workspace_dir: 配置文件的基准目录（已校验的安全路径）
        """
        self._workspace = workspace_dir

    @abstractmethod
    async def read_config(self, file_path: Path) -> ConfigResult:
        """
        异步读取配置文件

        Args:
            file_path: 配置文件的完整路径（已通过安全校验）

        Returns:
            ConfigResult: 包含配置数据和元数据的结果对象

        Raises:
            ConfigNotFoundException: 文件不存在（且无法自动初始化时）
            ConfigFormatException: 文件格式损坏或解析失败
        """
        pass

    @abstractmethod
    async def write_config(
        self, file_path: Path, data: Dict[str, Any], old_version_hash: str
    ) -> ConfigResult:
        """
        原子性写入配置（带乐观并发控制）

        算法流程：
        1. 如果文件存在，计算当前哈希并与 old_version_hash 比较
        2. 如果不匹配，抛出 ConcurrencyConflictException
        3. 如果匹配或文件不存在，原子性地写入新数据
        4. 重新读取以获取新的版本哈希

        Args:
            file_path: 配置文件完整路径
            data: 要写入的配置数据（必须是字典）
            old_version_hash: 读取时获取的版本哈希，用于并发控制

        Returns:
            ConfigResult: 写入后的新配置数据和新版本哈希

        Raises:
            ConcurrencyConflictException: 版本哈希不匹配，说明文件被外部修改
            ConfigFormatException: 数据无法序列化为目标格式
        """
        pass

    @abstractmethod
    async def generate_schema(self, file_path: Path) -> Dict[str, Any]:
        """
        异步推导 JSON Schema

        根据配置文件的当前数据内容，自动推导符合 JSON Schema Draft-07 的结构定义。
        前端可基于此 Schema 动态渲染 GUI 表单。

        Args:
            file_path: 配置文件完整路径

        Returns:
            Dict[str, Any]: JSON Schema 定义字典

        Schema 推导逻辑：
        - null -> {"type": "null"}
        - bool -> {"type": "boolean"}
        - int/float -> {"type": "number"}
        - str -> {"type": "string"}
        - list -> {"type": "array", "items": {...}}
        - dict -> {"type": "object", "properties": {...}, "required": [...]}
        """
        pass

    def _derive_schema(
        self, value: Any, depth: int = 0, max_depth: int = 50
    ) -> Dict[str, Any]:
        """
        递归推导值对应的 JSON Schema（同步方法，可在异步方法中调用）

        Args:
            value: 任意 Python 值
            depth: 当前递归深度
            max_depth: 最大递归深度限制，防止栈溢出攻击

        Returns:
            JSON Schema 定义字典
        """
        if depth > max_depth:
            return {"type": "object", "description": "Maximum nesting depth exceeded"}

        if value is None:
            return {"type": "null"}

        if isinstance(value, bool):
            return {"type": "boolean"}

        if isinstance(value, (int, float)):
            return {"type": "number"}

        if isinstance(value, str):
            return {"type": "string"}

        if isinstance(value, list):
            if not value:
                return {"type": "array", "items": {}}

            # 简化处理：取第一个元素的类型作为数组项的 Schema
            # 生产环境可能需要更复杂的类型合并逻辑
            items_schema = self._derive_schema(value[0], depth + 1, max_depth)
            return {"type": "array", "items": items_schema}

        if isinstance(value, dict):
            properties = {}
            required = []

            for key, val in value.items():
                properties[key] = self._derive_schema(val, depth + 1, max_depth)
                # 非 null 值视为 required
                if val is not None:
                    required.append(key)

            schema: Dict[str, Any] = {"type": "object", "properties": properties}
            schema["required"] = required
            return schema

        # 未知类型，标记为通用对象
        return {
            "type": "object",
            "description": f"Unknown type: {type(value).__name__}",
        }


# ============================================================================
# JSON 适配器实现
# ============================================================================


class JsonAdapter(BaseConfigAdapter):
    """
    JSON 格式配置适配器

    支持特性：
    - UTF-8 编码，支持 Unicode 字符
    - 格式化输出（2 空格缩进）
    - 自动处理空文件（初始化为空对象 {}）
    - 详细的 JSON 解析错误信息（行号、列号）
    """

    supported_extensions = [".json"]

    async def read_config(self, file_path: Path) -> ConfigResult:
        """
        读取 JSON 配置文件

        如果文件不存在，自动初始化为空配置 {} 并返回。
        """
        from core.security import ConfigMeta as SecurityConfigMeta
        import anyio

        # 异步检查文件是否存在
        exists = await anyio.Path(file_path).exists()

        if not exists:
            # 自动初始化：创建空配置
            await self._init_empty_config(file_path)

        # 异步读取并解析
        return await anyio.to_thread.run_sync(self._sync_read, file_path)

    def _sync_read(self, file_path: Path) -> ConfigResult:
        """同步读取逻辑（在线程池执行）"""
        from core.security import AtomicFileWriter, ConfigMeta as SecurityConfigMeta

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            if not content.strip():
                # 空文件视为空配置
                data: Dict[str, Any] = {}
            else:
                data = json.loads(content)

            # 校验根类型必须是对象
            if not isinstance(data, dict):
                raise ConfigFormatException(
                    str(file_path), f"配置根必须是对象，但得到 {type(data).__name__}"
                )

        except json.JSONDecodeError as e:
            raise ConfigFormatException(
                str(file_path), f"JSON 解析错误 (行 {e.lineno}, 列 {e.colno}): {e.msg}"
            )
        except UnicodeDecodeError as e:
            raise ConfigFormatException(
                str(file_path), f"文件编码错误，期望 UTF-8: {str(e)}"
            )

        # 计算元数据
        version_hash = AtomicFileWriter._sync_compute_hash(file_path, "sha256")
        last_modified = file_path.stat().st_mtime

        return ConfigResult(
            data=data,
            meta=ConfigMeta(version_hash=version_hash, last_modified=last_modified),
        )

    async def _init_empty_config(self, file_path: Path) -> None:
        """异步初始化空配置"""
        from core.security import AtomicFileWriter

        await AtomicFileWriter.write_atomic(file_path, "{}")

    async def write_config(
        self, file_path: Path, data: Dict[str, Any], old_version_hash: str
    ) -> ConfigResult:
        """
        原子性写入 JSON 配置

        实现乐观并发控制：
        1. 检查当前文件哈希
        2. 与 old_version_hash 比较
        3. 原子写入新数据
        """
        from core.security import AtomicFileWriter
        import anyio

        # 校验数据类型
        if not isinstance(data, dict):
            raise ConfigFormatException(
                str(file_path), f"配置数据必须是对象，但得到 {type(data).__name__}"
            )

        # 检查并发冲突
        exists = await anyio.Path(file_path).exists()

        if exists:
            current_hash = await AtomicFileWriter.compute_file_hash(file_path)
            if current_hash != old_version_hash:
                raise ConcurrencyConflictException(
                    source_path=str(file_path),
                    expected_hash=old_version_hash,
                    actual_hash=current_hash,
                )

        # 序列化数据
        try:
            json_content = json.dumps(data, indent=2, ensure_ascii=False)
        except (TypeError, ValueError) as e:
            raise ConfigFormatException(
                str(file_path), f"数据无法序列化为 JSON: {str(e)}"
            )

        # 原子写入
        await AtomicFileWriter.write_atomic(file_path, json_content)

        # 返回写入后的结果（包含新哈希）
        return await self.read_config(file_path)

    async def generate_schema(self, file_path: Path) -> Dict[str, Any]:
        """
        从 JSON 数据推导 JSON Schema
        """
        result = await self.read_config(file_path)

        # 构建 Schema
        schema = self._derive_schema(result.data)

        # 添加标准 JSON Schema 元数据
        schema["$schema"] = "http://json-schema.org/draft-07/schema#"
        schema["$id"] = f"file://{file_path}"

        return schema


# ============================================================================
# 适配器工厂
# ============================================================================


class AdapterFactory:
    """
    适配器工厂 - 多态创建器

    设计模式：工厂模式 + 注册表模式

    职责：
    1. 根据文件扩展名动态选择并创建对应的适配器实例
    2. 管理所有已注册的适配器类型
    3. 提供统一的适配器获取入口

    扩展方式：
    要支持新的配置格式（如 YAML、TOML）：
    1. 创建新的适配器类继承 BaseConfigAdapter
    2. 在类中定义 supported_extensions = ['.yaml', '.yml']
    3. 调用 AdapterFactory.register(YamlAdapter)
    4. 工厂会自动识别 .yaml 文件并使用 YamlAdapter 处理
    """

    # 类级别的注册表：{'.json': JsonAdapter, '.yaml': YamlAdapter, ...}
    _registry: Dict[str, Type[BaseConfigAdapter]] = {}
    _initialized: bool = False

    @classmethod
    def register(
        cls, adapter_class: Type[BaseConfigAdapter]
    ) -> Type[BaseConfigAdapter]:
        """
        注册适配器类到工厂

        使用装饰器语法或显式调用均可：

        @AdapterFactory.register
        class YamlAdapter(BaseConfigAdapter):
            supported_extensions = ['.yaml', '.yml']
            ...

        Args:
            adapter_class: 适配器类（必须是 BaseConfigAdapter 的子类）

        Returns:
            传入的适配器类（便于装饰器语法使用）

        Raises:
            TypeError: 如果 adapter_class 不是 BaseConfigAdapter 的子类
            ValueError: 如果适配器没有定义 supported_extensions
        """
        if not issubclass(adapter_class, BaseConfigAdapter):
            raise TypeError(
                f"适配器必须是 BaseConfigAdapter 的子类，得到 {adapter_class.__name__}"
            )

        if not adapter_class.supported_extensions:
            raise ValueError(
                f"适配器 {adapter_class.__name__} 必须定义 supported_extensions"
            )

        for ext in adapter_class.supported_extensions:
            # 统一转换为小写进行比较
            ext_lower = ext.lower()
            if ext_lower in cls._registry:
                existing = cls._registry[ext_lower].__name__
                raise ValueError(
                    f"扩展名 '{ext}' 已被 {existing} 注册，"
                    f"无法重复注册 {adapter_class.__name__}"
                )

            cls._registry[ext_lower] = adapter_class

        return adapter_class

    @classmethod
    def get_adapter(cls, file_path: Path, workspace_dir: Path) -> BaseConfigAdapter:
        """
        根据文件路径获取对应的适配器实例

        算法：
        1. 提取文件扩展名（如 .json）
        2. 在注册表中查找对应的适配器类
        3. 实例化并返回

        Args:
            file_path: 目标文件路径（用于提取扩展名）
            workspace_dir: 工作目录（传递给适配器构造函数）

        Returns:
            BaseConfigAdapter: 对应类型的适配器实例

        Raises:
            ConfigException: 当文件扩展名不受支持时抛出 400 错误
        """
        # 确保已注册默认适配器
        if not cls._initialized:
            cls._register_defaults()

        # 提取扩展名
        ext = file_path.suffix.lower()

        if not ext:
            raise ConfigException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"文件缺少扩展名，无法确定格式: {file_path.name}",
                error_type="UnsupportedFormatException",
            )

        if ext not in cls._registry:
            supported = ", ".join(cls._registry.keys())
            raise ConfigException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(f"不支持的文件格式 '{ext}'。支持的格式: {supported}"),
                error_type="UnsupportedFormatException",
            )

        adapter_class = cls._registry[ext]
        return adapter_class(workspace_dir)

    @classmethod
    def _register_defaults(cls) -> None:
        """注册默认的适配器（延迟初始化）"""
        if cls._initialized:
            return

        # 注册 JSON 适配器
        cls.register(JsonAdapter)

        cls._initialized = True

    @classmethod
    def get_supported_extensions(cls) -> list[str]:
        """获取所有支持的文件扩展名列表"""
        if not cls._initialized:
            cls._register_defaults()
        return list(cls._registry.keys())


# ============================================================================
# 便捷函数
# ============================================================================


def get_adapter_for_path(file_path: Path, workspace_dir: Path) -> BaseConfigAdapter:
    """
    便捷函数：获取文件对应的适配器

    这是 AdapterFactory.get_adapter 的简写形式。
    """
    return AdapterFactory.get_adapter(file_path, workspace_dir)
