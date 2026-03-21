"""
api/router.py

FastAPI 路由模块：提供 HTTP REST API 和 Server-Sent Events (SSE) 接口。

路由设计：
1. REST API: 传统的请求-响应模式，用于配置的 CRUD 操作
2. SSE Endpoint: 长连接实时推送，用于文件变更通知

SSE 实现要点：
- 使用 async generator 保持连接活跃
- 每个连接创建独立的文件监控器（watchdog Observer）
- 连接断开时自动清理资源，防止句柄泄漏
- 防抖机制聚合频繁的文件修改事件

依赖注入：
- get_path_validator: 提供 PathSecurityValidator 单例
- get_workspace_dir: 提供已配置的 WORKSPACE_DIR
"""

import json
import asyncio
import weakref
from pathlib import Path
from typing import AsyncGenerator, Dict, Any, Optional, Set
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import anyio

# 导入核心模块
from core.security import PathSecurityValidator, SecurityError
from core.adapter import (
    BaseConfigAdapter,
    AdapterFactory,
    ConfigResult,
    ConfigException,
    ConcurrencyConflictException,
    ConfigNotFoundException,
    ConfigFormatException,
)

# 尝试导入 watchdog，如果不存在则使用 asyncio 轮询作为备选
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler, FileModifiedEvent

    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False


# ============================================================================
# 配置与依赖
# ============================================================================

# 从环境变量或配置文件读取，这里使用硬编码作为示例
WORKSPACE_DIR = Path("./configs").resolve()

# 全局路径校验器（单例模式）
_path_validator: Optional[PathSecurityValidator] = None


def get_path_validator() -> PathSecurityValidator:
    """
    依赖注入：获取路径安全校验器单例

    Returns:
        PathSecurityValidator: 已初始化的路径校验器
    """
    global _path_validator
    if _path_validator is None:
        _path_validator = PathSecurityValidator(WORKSPACE_DIR)
    return _path_validator


def get_workspace_dir() -> Path:
    """
    依赖注入：获取工作目录

    Returns:
        Path: 配置文件的基准目录
    """
    return WORKSPACE_DIR


# ============================================================================
# Pydantic 请求/响应模型
# ============================================================================


class ConfigResponse(BaseModel):
    """配置读取响应模型"""

    data: Dict[str, Any] = Field(..., description="配置数据字典")
    meta: Dict[str, Any] = Field(
        ..., description="元数据（包含 versionHash 和 lastModified）"
    )


class SaveConfigRequest(BaseModel):
    """保存配置请求模型"""

    data: Dict[str, Any] = Field(..., description="要保存的配置数据")
    oldVersionHash: str = Field(..., description="读取时获取的版本哈希，用于并发控制")


class SaveConfigResponse(BaseModel):
    """保存配置响应模型"""

    success: bool = Field(True, description="是否保存成功")
    data: Dict[str, Any] = Field(..., description="保存后的配置数据")
    meta: Dict[str, Any] = Field(..., description="新的元数据")


class SchemaResponse(BaseModel):
    """Schema 响应模型"""

    schema_def: Dict[str, Any] = Field(
        ..., alias="schema", description="JSON Schema 定义"
    )

    class Config:
        populate_by_name = True


class SSEEvent(BaseModel):
    """SSE 事件数据模型"""

    event: str = Field(..., description="事件类型: modified | deleted | error")
    timestamp: float = Field(..., description="事件发生的时间戳")
    data: Optional[Dict[str, Any]] = Field(None, description="事件附加数据")
    message: Optional[str] = Field(None, description="事件描述消息")


# ============================================================================
# 路由定义
# ============================================================================

router = APIRouter(prefix="/api", tags=["config"])


@router.get(
    "/config/{source_path:path}",
    response_model=ConfigResponse,
    summary="读取配置",
    description="读取指定路径的配置文件内容及其元数据",
    responses={
        200: {"description": "成功返回配置数据"},
        403: {"description": "路径穿越攻击被拦截"},
        404: {"description": "配置文件不存在"},
        422: {"description": "配置文件格式错误"},
    },
)
async def read_config(
    source_path: str,
    validator: PathSecurityValidator = Depends(get_path_validator),
    workspace: Path = Depends(get_workspace_dir),
) -> Dict[str, Any]:
    """
    异步读取配置文件

    流程：
    1. 安全校验：将 source_path 限制在 WORKSPACE_DIR 内
    2. 适配器选择：根据文件扩展名选择对应的适配器（如 JSON）
    3. 异步读取：在线程池中执行文件 I/O，不阻塞事件循环

    Args:
        source_path: 配置文件的相对路径（如 "app/settings.json"）

    Returns:
        包含 data 和 meta 的 JSON 对象
    """
    # 1. 安全校验：防止路径穿越攻击
    try:
        file_path = validator.validate(source_path)
    except SecurityError:
        raise

    # 2. 获取适配器（工厂模式）
    adapter = AdapterFactory.get_adapter(file_path, workspace)

    # 3. 异步读取配置
    result = await adapter.read_config(file_path)

    return result.to_dict()


@router.post(
    "/config/{source_path:path}",
    response_model=SaveConfigResponse,
    summary="保存配置",
    description="保存配置数据，必须提供 oldVersionHash 进行并发冲突校验",
    responses={
        200: {"description": "配置保存成功"},
        403: {"description": "路径穿越攻击被拦截"},
        409: {"description": "并发冲突 - 文件已被其他进程修改"},
        422: {"description": "数据格式错误或 JSON 序列化失败"},
    },
)
async def write_config(
    source_path: str,
    request: SaveConfigRequest,
    validator: PathSecurityValidator = Depends(get_path_validator),
    workspace: Path = Depends(get_workspace_dir),
) -> Dict[str, Any]:
    """
    原子性保存配置（带乐观并发控制）

    并发控制算法：
    1. 校验 source_path 安全
    2. 计算当前文件的 SHA256 哈希
    3. 比较 oldVersionHash，如果不匹配抛出 409 冲突
    4. 原子性写入新数据（临时文件 + os.replace）
    5. 返回新的 versionHash

    Args:
        source_path: 配置文件的相对路径
        request: 包含 data 和 oldVersionHash 的请求体

    Returns:
        包含新配置数据和新版本哈希的响应

    Raises:
        HTTPException 409: 当检测到并发冲突时
    """
    # 1. 安全校验
    file_path = validator.validate(source_path)

    # 2. 获取适配器
    adapter = AdapterFactory.get_adapter(file_path, workspace)

    # 3. 原子性写入（适配器内部处理并发控制）
    try:
        result = await adapter.write_config(
            file_path=file_path,
            data=request.data,
            old_version_hash=request.oldVersionHash,
        )
    except ConcurrencyConflictException:
        raise
    except ConfigException:
        raise

    return {"success": True, **result.to_dict()}


@router.get(
    "/schema/{source_path:path}",
    response_model=SchemaResponse,
    summary="获取配置 Schema",
    description="根据配置数据自动推导 JSON Schema 结构",
    responses={
        200: {"description": "成功返回 Schema 定义"},
        403: {"description": "路径穿越攻击被拦截"},
        404: {"description": "配置文件不存在"},
    },
)
async def generate_schema(
    source_path: str,
    validator: PathSecurityValidator = Depends(get_path_validator),
    workspace: Path = Depends(get_workspace_dir),
) -> Dict[str, Any]:
    """
    异步推导 JSON Schema

    根据配置文件的当前数据，递归推导符合 JSON Schema Draft-07 的结构定义。
    前端可基于此 Schema 动态渲染 GUI 表单。

    Args:
        source_path: 配置文件的相对路径

    Returns:
        包含完整 JSON Schema 定义的对象
    """
    # 安全校验
    file_path = validator.validate(source_path)

    # 获取适配器
    adapter = AdapterFactory.get_adapter(file_path, workspace)

    # 生成 Schema
    schema = await adapter.generate_schema(file_path)

    return {"schema": schema}


# ============================================================================
# SSE 实时热更新接口
# ============================================================================


class ConfigFileWatcher:
    """
    配置文件监控器

    封装 watchdog 的文件监控逻辑，提供：
    1. 防抖机制：聚合 500ms 内的多次修改事件
    2. 连接管理：使用 weakref 自动追踪活跃的监控连接
    3. 优雅关闭：连接断开时自动停止监控并释放资源

    实现选择：
    - 优先使用 watchdog（基于 inotify/kqueue/FSEvents，系统级高效）
    - 备选使用 asyncio 轮询（纯 Python，无额外依赖）
    """

    # 类级别的活跃连接集合，用于自动清理
    _active_watchers: Set["ConfigFileWatcher"] = set()

    def __init__(self, file_path: Path, debounce_ms: float = 500) -> None:
        """
        初始化监控器

        Args:
            file_path: 要监控的文件完整路径
            debounce_ms: 防抖时间窗口（毫秒），默认 500ms
        """
        self.file_path = file_path
        self.debounce_ms = debounce_ms
        self._event_queue: asyncio.Queue[Optional[str]] = asyncio.Queue()
        self._observer: Optional[Observer] = None
        self._stopped = False
        self._debounce_task: Optional[asyncio.Task] = None

        # 注册到活跃集合
        ConfigFileWatcher._active_watchers.add(self)

    async def start(self) -> None:
        """
        启动文件监控

        根据平台能力选择监控策略：
        - 有 watchdog：使用系统级文件系统事件通知
        - 无 watchdog：使用 asyncio 轮询（每 1 秒检查 mtime）
        """
        if WATCHDOG_AVAILABLE:
            await self._start_watchdog()
        else:
            await self._start_polling()

    async def _start_watchdog(self) -> None:
        """使用 watchdog 进行高效监控"""

        # 定义事件处理器
        class ConfigEventHandler(FileSystemEventHandler):
            def __init__(self, watcher: "ConfigFileWatcher"):
                self.watcher = watcher

            def on_modified(self, event):
                if isinstance(event, FileModifiedEvent):
                    # 检查是否是目标文件被修改
                    if Path(event.src_path) == self.watcher.file_path:
                        # 触发防抖逻辑
                        asyncio.create_task(self.watcher._trigger_event("modified"))

            def on_deleted(self, event):
                if Path(event.src_path) == self.watcher.file_path:
                    asyncio.create_task(self.watcher._trigger_event("deleted"))

        # 创建并启动观察者
        self._observer = Observer()
        handler = ConfigEventHandler(self)

        # 监控父目录（因为某些系统无法直接监控单个文件）
        watch_path = str(self.file_path.parent)
        self._observer.schedule(handler, watch_path, recursive=False)
        self._observer.start()

    async def _start_polling(self) -> None:
        """
        使用 asyncio 轮询作为备选方案

        当 watchdog 不可用时，每 1 秒检查一次文件的 mtime。
        这是次优方案，但保证了功能的可用性。
        """
        last_mtime = 0

        try:
            if self.file_path.exists():
                last_mtime = (await anyio.Path(self.file_path).stat()).st_mtime
        except OSError:
            pass

        while not self._stopped:
            await asyncio.sleep(1.0)  # 每秒检查一次

            if self._stopped:
                break

            try:
                if await anyio.Path(self.file_path).exists():
                    current_mtime = (await anyio.Path(self.file_path).stat()).st_mtime
                    if current_mtime != last_mtime:
                        last_mtime = current_mtime
                        await self._trigger_event("modified")
                else:
                    # 文件被删除
                    if last_mtime != 0:
                        last_mtime = 0
                        await self._trigger_event("deleted")
            except OSError:
                pass

    async def _trigger_event(self, event_type: str) -> None:
        """
        触发防抖逻辑

        原理：当事件到来时，启动一个延迟任务。
        如果在延迟期间有新事件到来，取消旧任务并重新开始计时。
        这样可以聚合频繁的文件修改事件（如编辑器保存时的多次写入）。
        """
        # 取消之前的防抖任务
        if self._debounce_task and not self._debounce_task.done():
            self._debounce_task.cancel()
            try:
                await self._debounce_task
            except asyncio.CancelledError:
                pass

        # 创建新的防抖任务
        self._debounce_task = asyncio.create_task(self._debounced_emit(event_type))

    async def _debounced_emit(self, event_type: str) -> None:
        """防抖后的实际事件发送"""
        await asyncio.sleep(self.debounce_ms / 1000.0)

        if not self._stopped:
            await self._event_queue.put(event_type)

    async def get_event(self) -> Optional[str]:
        """
        获取下一个事件

        Returns:
            事件类型字符串，或 None（如果监控已停止）
        """
        if self._stopped:
            return None

        try:
            return await self._event_queue.get()
        except asyncio.CancelledError:
            return None

    def stop(self) -> None:
        """
        停止监控并清理资源

        连接断开时自动调用，确保：
        1. 停止 watchdog observer
        2. 取消待处理的防抖任务
        3. 发送结束信号到事件队列
        """
        if self._stopped:
            return

        self._stopped = True

        # 停止 watchdog
        if self._observer:
            self._observer.stop()
            self._observer.join()
            self._observer = None

        # 取消防抖任务
        if self._debounce_task and not self._debounce_task.done():
            self._debounce_task.cancel()

        # 发送结束信号
        try:
            self._event_queue.put_nowait(None)
        except asyncio.QueueFull:
            pass

        # 从活跃集合中移除
        ConfigFileWatcher._active_watchers.discard(self)

    async def __aenter__(self) -> "ConfigFileWatcher":
        """异步上下文管理器入口"""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """异步上下文管理器出口"""
        self.stop()


@router.get(
    "/watch/{source_path:path}",
    summary="实时监控配置变更（SSE）",
    description="使用 Server-Sent Events 实时推送文件变更通知",
    responses={
        200: {
            "description": "SSE 流连接建立成功",
            "content": {
                "text/event-stream": {
                    "example": 'data: {"event": "modified", "timestamp": 1711000000.0}'
                }
            },
        },
        403: {"description": "路径穿越攻击被拦截"},
    },
)
async def watch_config(
    source_path: str,
    validator: PathSecurityValidator = Depends(get_path_validator),
    workspace: Path = Depends(get_workspace_dir),
):
    """
    Server-Sent Events 实时监控接口

    功能：
    当指定配置文件被外部 Agent 或脚本修改时，主动向前端推送事件。
    使用 SSE 而非 WebSocket，因为：
    1. 单向通信足够（服务器 -> 客户端）
    2. 基于 HTTP，更易穿越防火墙和代理
    3. 自动重连机制（浏览器原生支持 EventSource）

    事件类型：
    - modified: 文件内容被修改
    - deleted: 文件被删除
    - error: 监控过程中发生错误
    - connected: 连接建立成功（首次推送）
    - heartbeat: 保活心跳（每 30 秒）

    Args:
        source_path: 要监控的配置文件相对路径

    Returns:
        StreamingResponse: text/event-stream 格式的 SSE 流

    前端使用示例（JavaScript）：
    ```javascript
    const es = new EventSource('/api/watch/app/config.json');
    es.onmessage = (event) => {
        const data = JSON.parse(event.data);
        console.log('Config changed:', data);
    };
    ```
    """
    # 安全校验
    file_path = validator.validate(source_path)

    async def event_generator() -> AsyncGenerator[str, None]:
        """
        SSE 事件生成器

        格式规范：
        - 每行以 "data: " 开头
        - 事件之间用空行分隔
        - 支持 "event: " 指定事件类型（可选）
        - 支持 "id: " 指定事件 ID（用于断线重连）
        """
        event_id = 0

        async with ConfigFileWatcher(file_path) as watcher:
            # 发送连接成功事件
            connected_payload = {
                "event": "connected",
                "timestamp": datetime.now().timestamp(),
                "message": f"Started watching {source_path}",
                "using_watchdog": WATCHDOG_AVAILABLE,
            }
            connected_data = json.dumps(connected_payload)
            yield f"id: {event_id}\nevent: connected\ndata: {connected_data}\n\n"
            event_id += 1

            # 心跳任务：每 30 秒发送一次保活
            heartbeat_interval = 30.0
            last_heartbeat = asyncio.get_event_loop().time()

            try:
                while True:
                    # 检查是否需要发送心跳
                    current_time = asyncio.get_event_loop().time()
                    if current_time - last_heartbeat >= heartbeat_interval:
                        heartbeat_payload = {
                            "event": "heartbeat",
                            "timestamp": datetime.now().timestamp(),
                        }
                        heartbeat_data = json.dumps(heartbeat_payload)
                        yield f"id: {event_id}\nevent: heartbeat\ndata: {heartbeat_data}\n\n"
                        event_id += 1
                        last_heartbeat = current_time

                    # 等待文件变更事件（带超时以便发送心跳）
                    try:
                        event_type = await asyncio.wait_for(
                            watcher.get_event(), timeout=1.0
                        )
                    except asyncio.TimeoutError:
                        continue

                    if event_type is None:
                        # 监控器停止
                        break

                    # 构建事件数据
                    event_data_payload = {
                        "event": event_type,
                        "timestamp": datetime.now().timestamp(),
                        "path": source_path,
                    }

                    # 如果是修改事件，尝试读取新内容
                    if event_type == "modified":
                        try:
                            adapter = AdapterFactory.get_adapter(file_path, workspace)
                            result = await adapter.read_config(file_path)
                            event_data_payload["newVersionHash"] = (
                                result.meta.version_hash
                            )
                            event_data_payload["newData"] = result.data
                        except Exception as e:
                            event_data_payload["error"] = str(e)

                    # 发送 SSE 事件
                    event_data_str = json.dumps(event_data_payload)
                    yield f"id: {event_id}\nevent: {event_type}\ndata: {event_data_str}\n\n"
                    event_id += 1

            except asyncio.CancelledError:
                # 客户端断开连接
                pass
            finally:
                # 发送断开事件
                disconnected_payload = {
                    "event": "disconnected",
                    "timestamp": datetime.now().timestamp(),
                }
                disconnected_data = json.dumps(disconnected_payload)
                yield f"id: {event_id}\nevent: disconnected\ndata: {disconnected_data}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            # 禁用缓存，确保实时性
            "Cache-Control": "no-cache",
            # 保持连接活跃
            "Connection": "keep-alive",
            # 允许跨域（根据需求调整）
            "Access-Control-Allow-Origin": "*",
        },
    )


# ============================================================================
# 健康检查
# ============================================================================


@router.get("/health", summary="健康检查", description="服务健康状态检查")
async def health_check() -> Dict[str, Any]:
    """健康检查端点"""
    return {
        "status": "healthy",
        "service": "OminiConfig API",
        "version": "2.0.0",
        "features": {
            "watchdog": WATCHDOG_AVAILABLE,
            "supported_formats": AdapterFactory.get_supported_extensions(),
        },
        "timestamp": datetime.now().isoformat(),
    }
