"""
core/__init__.py

核心模块初始化
"""

from .security import PathSecurityValidator, AtomicFileWriter, SecurityError
from .adapter import (
    BaseConfigAdapter,
    JsonAdapter,
    AdapterFactory,
    ConfigResult,
    ConfigMeta,
    ConfigException,
    ConcurrencyConflictException,
    ConfigNotFoundException,
    ConfigFormatException,
    get_adapter_for_path,
)

__all__ = [
    # Security
    "PathSecurityValidator",
    "AtomicFileWriter",
    "SecurityError",
    # Adapter
    "BaseConfigAdapter",
    "JsonAdapter",
    "AdapterFactory",
    "ConfigResult",
    "ConfigMeta",
    "ConfigException",
    "ConcurrencyConflictException",
    "ConfigNotFoundException",
    "ConfigFormatException",
    "get_adapter_for_path",
]
