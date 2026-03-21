"""
OminiConfig 适配器模块

提供通用配置管理器的核心适配器实现
"""

from .adapter import (
    IOminiConfigAdapter,
    JsonConfigAdapter,
    ConfigMeta,
    ConfigResult,
    ConfigException,
    ConfigNotFoundException,
    ConfigFormatException,
    ConcurrencyConflictException,
)
from typing import Dict, Any

# Type alias
ConfigData = Dict[str, Any]

__all__ = [
    "IOminiConfigAdapter",
    "JsonConfigAdapter",
    "ConfigData",
    "ConfigMeta",
    "ConfigResult",
    "ConfigException",
    "ConfigNotFoundException",
    "ConfigFormatException",
    "ConcurrencyConflictException",
]

__version__ = "1.0.0"
