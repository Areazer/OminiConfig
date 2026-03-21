# OminiConfig v2.0 企业级重构文档

## 重构概览

本次重构将 OminiConfig 从初代原型升级为生产就绪的企业级后端服务，重点关注以下四个维度：

1. **安全性**：路径沙箱校验防御目录穿越攻击
2. **架构性**：工厂模式支持多格式适配器（JSON/YAML/...）
3. **健壮性**：跨平台原子写入（tempfile + os.replace）
4. **实时性**：SSE 接口支持文件变更热更新

---

## 项目结构

```
OminiConfig/
├── core/
│   ├── __init__.py          # 核心模块导出
│   ├── security.py          # 路径安全校验 + 原子写入工具
│   └── adapter.py           # 抽象基类 + JsonAdapter + AdapterFactory
├── api/
│   ├── __init__.py          # API 模块导出
│   └── router.py            # FastAPI 路由（REST + SSE）
├── main.py                  # 应用入口
├── requirements.txt         # 依赖列表
└── README.md               # 项目说明
```

---

## 核心模块详解

### 1. core/security.py - 安全与原子性

#### PathSecurityValidator
**职责**：将前端传入的路径严格限制在 `WORKSPACE_DIR` 根目录内，防御路径穿越攻击。

**核心算法**：
```python
def validate(self, source_path: str) -> Path:
    # 1. 防御空字节注入
    if '\x00' in source_path: raise SecurityError(...)
    
    # 2. 拒绝绝对路径
    if source_path.startswith('/'): raise SecurityError(...)
    
    # 3. 规范化路径（解析 . 和 ..）
    target_path = (self._workspace / source_path).resolve()
    
    # 4. 严格前缀匹配（使用 commonpath，而非 startswith）
    common = os.path.commonpath([str(self._workspace), str(target_path)])
    if common != str(self._workspace):
        raise SecurityError("路径穿越攻击被拦截")
    
    return target_path
```

**为什么用 `commonpath` 而非 `startswith`？**
- `startswith` 容易误判：`/workspace` 也会匹配 `/workspace2/secret.txt`
- `commonpath` 是严格的目录层级比较，更安全

#### AtomicFileWriter
**职责**：跨平台原子文件写入，保证并发安全和崩溃恢复。

**算法流程**：
1. 写入临时文件：`/workspace/config.tmp.abc123`
2. 强制刷盘：`fsync()` 确保数据落盘
3. 原子替换：`os.replace(temp, target)` 覆盖目标文件

**为什么用 `os.replace` 而非 `os.rename`？**
- `os.rename`: Windows 上目标存在时抛出 `FileExistsError`
- `os.replace`: POSIX 语义，始终原子性覆盖，跨平台一致

**为什么使用临时文件？**
- 写入过程中崩溃 → 临时文件不污染目标文件
- 读取者永远看到完整文件（要么旧版本，要么新版本）

---

### 2. core/adapter.py - 抽象与工厂

#### BaseConfigAdapter (ABC)
定义所有适配器必须实现的接口契约：
- `read_config`: 异步读取配置
- `write_config`: 原子写入 + 乐观锁
- `generate_schema`: 推导 JSON Schema

**设计原则**：
- 单一职责：每个适配器只负责一种格式
- 无状态：实例不持有配置，支持并发复用

#### JsonAdapter
JSON 格式适配器实现：
- UTF-8 编码，支持 Unicode
- 格式化输出（2 空格缩进）
- 自动初始化空配置（`{}`）
- 详细错误信息（JSON 解析行号、列号）

#### AdapterFactory
**设计模式**：工厂模式 + 注册表模式

**使用方式**：
```python
# 注册适配器
@AdapterFactory.register
class YamlAdapter(BaseConfigAdapter):
    supported_extensions = ['.yaml', '.yml']
    ...

# 动态获取适配器
adapter = AdapterFactory.get_adapter(
    Path("config.yaml"), 
    WORKSPACE_DIR
)  # 返回 YamlAdapter 实例
```

**扩展性**：
- 新增格式只需：继承基类 → 定义扩展名 → 注册到工厂
- 无需修改现有代码（开闭原则）

---

### 3. api/router.py - REST + SSE

#### REST API 端点

| 端点 | 方法 | 功能 |
|------|------|------|
| `/api/config/{path}` | GET | 读取配置 + 元数据 |
| `/api/config/{path}` | POST | 原子写入（带乐观锁） |
| `/api/schema/{path}` | GET | 推导 JSON Schema |

#### SSE 实时热更新

**端点**：`GET /api/watch/{source_path}`

**功能**：当配置文件被外部修改时，向前端实时推送事件。

**为什么用 SSE 而非 WebSocket？**
1. 单向通信足够（服务器 → 客户端）
2. 基于 HTTP，更易穿越防火墙和代理
3. 浏览器原生支持 `EventSource`，自动重连

**事件类型**：
- `connected`: 连接建立
- `modified`: 文件修改
- `deleted`: 文件删除
- `heartbeat`: 保活心跳（30秒）
- `disconnected`: 连接断开

**防抖机制**：
```python
# 聚合 500ms 内的多次修改事件
async def _trigger_event(self, event_type: str):
    # 取消之前的延迟任务
    if self._debounce_task:
        self._debounce_task.cancel()
    
    # 创建新的延迟任务
    self._debounce_task = asyncio.create_task(
        self._debounced_emit(event_type)
    )

async def _debounced_emit(self, event_type: str):
    await asyncio.sleep(0.5)  # 500ms 防抖
    await self._event_queue.put(event_type)
```

---

## 关键设计决策

### 1. 为什么使用 `anyio.to_thread`？

FastAPI 是异步框架，但文件 I/O 是阻塞操作。如果直接在协程中读写文件：
```python
# ❌ 阻塞事件循环！
data = open(file).read()  # 整个服务器卡住
```

正确做法：
```python
# ✅ 在线程池中执行，不阻塞事件循环
await anyio.to_thread.run_sync(read_file, file_path)
```

### 2. 乐观锁 vs 悲观锁

**悲观锁**（文件锁）：
- 优点：强一致性
- 缺点：性能差，易死锁，跨平台兼容性差

**乐观锁**（版本哈希）：
- 优点：高性能，无锁，跨平台，易扩展
- 缺点：ABA 问题（可通过时间戳缓解）

OminiConfig 选择乐观锁，因为配置修改通常是低频操作，冲突概率低。

### 3. 为什么用 `weakref.WeakSet` 管理 SSE 连接？

```python
_active_watchers: Set["ConfigFileWatcher"] = weakref.WeakSet()
```

- 自动清理：连接断开时，对象被 GC 回收，自动从集合中移除
- 防止内存泄漏：无需手动管理连接生命周期

---

## API 使用示例

### 读取配置
```bash
curl http://localhost:8000/api/config/app/settings.json
```

```json
{
  "data": {"debug": true, "port": 8080},
  "meta": {
    "versionHash": "abc123...",
    "lastModified": 1711000000.0
  }
}
```

### 保存配置（带乐观锁）
```bash
curl -X POST http://localhost:8000/api/config/app/settings.json \
  -H "Content-Type: application/json" \
  -d '{
    "data": {"debug": false, "port": 8080},
    "oldVersionHash": "abc123..."
  }'
```

**冲突响应（HTTP 409）**：
```json
{
  "error": "ConcurrencyConflictException",
  "message": "配置冲突: 路径 'app/settings.json' 在读取后被其他进程修改"
}
```

### 实时监控（SSE）
```javascript
const es = new EventSource('/api/watch/app/settings.json');

es.addEventListener('modified', (event) => {
  const data = JSON.parse(event.data);
  console.log('配置已更新:', data.newVersionHash);
  console.log('新数据:', data.newData);
});
```

---

## 扩展指南

### 添加 YAML 支持

```python
# adapters/yaml_adapter.py
import yaml
from core.adapter import BaseConfigAdapter, AdapterFactory

@AdapterFactory.register
class YamlAdapter(BaseConfigAdapter):
    supported_extensions = ['.yaml', '.yml']
    
    async def read_config(self, file_path: Path) -> ConfigResult:
        # 实现读取逻辑...
        pass
    
    async def write_config(self, file_path: Path, data: dict, old_hash: str) -> ConfigResult:
        # 实现写入逻辑...
        pass
    
    async def generate_schema(self, file_path: Path) -> dict:
        # 重用基类的 _derive_schema 方法
        result = await self.read_config(file_path)
        return self._derive_schema(result.data)
```

无需修改任何现有代码，工厂会自动识别 `.yaml` 文件并使用 `YamlAdapter` 处理。

---

## 性能优化建议

1. **缓存 Schema**：配置文件的 Schema 在不变时无需重复推导
2. **连接池**：大量 SSE 连接时考虑使用 Redis Pub/Sub 分发事件
3. **文件监听**：在 Docker 等容器环境中，watchdog 可能降级为轮询模式，考虑挂载 host 目录

---

## 安全加固清单

- [x] 路径沙箱校验（`PathSecurityValidator`）
- [x] 空字节注入防御
- [x] 绝对路径拒绝
- [x] 符号链接解析（`Path.resolve()`）
- [x] 前缀匹配（`commonpath`）
- [x] CORS 配置（生产环境应限制域名）

---

## 总结

OminiConfig v2.0 通过以下设计实现了企业级可靠性：

| 维度 | 技术方案 | 收益 |
|------|----------|------|
| **安全** | 路径沙箱 + commonpath | 防御路径穿越攻击 |
| **架构** | ABC + 工厂模式 | 易于扩展新格式 |
| **并发** | 乐观锁 + os.replace | 跨平台原子写入 |
| **实时** | SSE + watchdog | 毫秒级变更通知 |

代码遵循 PEP 8 规范，包含完整的 Type Hints 和中文注释，可直接用于生产环境。
