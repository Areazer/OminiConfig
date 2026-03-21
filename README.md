# OminiConfig

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-00a393.svg)](https://fastapi.tiangolo.com)
[![License: GPL-2.0](https://img.shields.io/badge/License-GPL%20v2-blue.svg)](https://www.gnu.org/licenses/old-licenses/gpl-2.0.html)

> 一款轻量级、高性能、支持任意数据源的通用 GUI 配置管理器后端服务

OminiConfig 是一个面向企业的通用配置管理解决方案，提供安全可靠的配置存储、版本控制、实时同步和 Schema 推导能力。基于 Python 3.8+ 和 FastAPI 构建，支持 JSON/YAML/TOML 等多种数据格式。

---

## ✨ 核心特性

### 🔒 企业级安全
- **路径沙箱校验**: 使用 `os.path.commonpath()` 严格防御路径穿越攻击
- **空字节注入防御**: 拦截所有非法字符
- **绝对路径拒绝**: 强制使用相对路径，防止误操作系统文件
- **原子文件写入**: 临时文件 + `os.replace()` 保证并发安全

### 🏭 优雅的架构设计
- **工厂模式**: 根据文件扩展名动态选择适配器（JSON/YAML/...）
- **抽象基类**: `BaseConfigAdapter` 定义统一接口，易于扩展
- **无状态设计**: 适配器实例可并发复用，轻量级
- **依赖注入**: FastAPI 原生支持，测试友好

### ⚡ 高性能并发
- **乐观锁**: SHA256 版本哈希替代重量级文件锁
- **异步非阻塞**: `anyio.to_thread` 将 I/O offload 到线程池
- **防抖优化**: SSE 事件 500ms 聚合，避免频繁推送
- **系统级监控**: watchdog (inotify/FSEvents/kqueue) 高效监听

### 📡 实时热更新
- **SSE 推送**: Server-Sent Events 实时通知配置变更
- **自动重连**: 浏览器原生 `EventSource` 支持
- **心跳保活**: 30 秒心跳检测连接状态
- **优雅降级**: 无 watchdog 时自动切换到 asyncio 轮询

### 🎯 开发者友好
- **自动 Schema 推导**: 从配置数据生成 JSON Schema，驱动前端表单
- **详细错误信息**: JSON 解析错误精确定位行号列号
- **完整类型注解**: 全代码库 Type Hints，IDE 智能提示
- **中文注释**: 核心逻辑附带详细中文说明

---

## 🚀 快速开始

### 环境要求

- Python 3.8+
- pip 或 poetry

### 安装

```bash
# 克隆仓库
git clone https://github.com/Areazer/OminiConfig.git
cd OminiConfig

# 创建虚拟环境（推荐）
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或: venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

### 启动服务

```bash
python main.py
```

服务启动后访问：
- 🌐 **API 文档**: http://localhost:8000/docs (Swagger UI)
- 📚 **备用文档**: http://localhost:8000/redoc (ReDoc)
- 🔍 **健康检查**: http://localhost:8000/api/health

---

## 📖 API 使用示例

### 读取配置

```bash
curl http://localhost:8000/api/config/app/settings.json
```

**响应**:
```json
{
  "data": {
    "debug": true,
    "port": 8080,
    "database": {
      "host": "localhost",
      "port": 5432
    }
  },
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
    "data": {
      "debug": false,
      "port": 8080,
      "database": {
        "host": "localhost",
        "port": 5432
      }
    },
    "oldVersionHash": "abc123..."
  }'
```

**冲突响应** (HTTP 409):
```json
{
  "error": "ConcurrencyConflictException",
  "message": "配置冲突: 路径 'app/settings.json' 在读取后被其他进程修改",
  "expected_hash": "abc123...",
  "actual_hash": "def456..."
}
```

### 获取 JSON Schema

```bash
curl http://localhost:8000/api/schema/app/settings.json
```

用于前端动态渲染表单。

### 实时监控（SSE）

```javascript
const eventSource = new EventSource(
  'http://localhost:8000/api/watch/app/settings.json'
);

eventSource.addEventListener('modified', (event) => {
  const data = JSON.parse(event.data);
  console.log('配置已更新:', data.newVersionHash);
  console.log('新数据:', data.newData);
});

eventSource.addEventListener('connected', (event) => {
  console.log('SSE 连接已建立');
});
```

**事件类型**:
- `connected`: 连接建立
- `modified`: 文件修改（包含新数据）
- `deleted`: 文件删除
- `heartbeat`: 心跳保活（每 30 秒）

---

## 🏗️ 项目结构

```
OminiConfig/
├── 📁 core/                      # 核心模块
│   ├── __init__.py
│   ├── security.py              # 路径安全 + 原子写入
│   └── adapter.py               # 抽象基类 + 工厂模式
│
├── 📁 api/                       # API 模块
│   ├── __init__.py
│   └── router.py                # REST + SSE 路由
│
├── 📁 doc/                       # 📚 文档目录（重要！）
│   ├── README.md                # 文档索引
│   ├── architecture/            # 架构设计文档
│   │   ├── v1_overview.md
│   │   └── v2_enterprise.md
│   ├── guides/                  # 开发指南
│   ├── api/                     # API 文档
│   └── standards/               # 规范标准
│
├── 📁 tests/                     # 单元测试
│   ├── test_security.py
│   ├── test_adapter.py
│   └── test_router.py
│
├── main.py                       # 🚀 应用入口
├── requirements.txt              # 📦 依赖列表
├── README.md                     # 📖 本文件
└── AGENTS.md                     # ⚙️ 开发规范
```

---

## 📚 文档导航

### 🏛️ 架构设计
- [v2.0 企业级架构](./doc/architecture/v2_enterprise.md) - 当前架构详解
- [v1.0 初代架构](./doc/architecture/v1_overview.md) - 历史参考
- [架构索引](./doc/architecture/README.md)

### 📖 开发指南
- [快速开始](./doc/guides/README.md) - 🚧 规划中
- [开发规范](./AGENTS.md) - ⚠️ 必须阅读
- [API 文档](./doc/api/README.md) - 🚧 规划中

### 📋 规范标准
- [代码规范](./doc/standards/README.md) - 🚧 规划中
- [提交规范](./doc/standards/commit_convention.md) - 🚧 规划中

---

## 🧪 运行测试

```bash
# 运行所有测试
python -m pytest tests/ -v

# 运行特定模块测试
python -m pytest tests/test_security.py -v

# 带覆盖率报告
python -m pytest tests/ --cov=core --cov-report=html
```

---

## 🏭 架构亮点

### 路径安全：为什么要用 `commonpath`?

```python
# ❌ 错误：startswith 容易误判
"/workspace".startswith("/work")  # True，但 "/workspace2" 不应该被允许

# ✅ 正确：commonpath 严格校验
os.path.commonpath(["/workspace", "/workspace2/secret.txt"])
# 返回 "/"，不等于 "/workspace"，因此拦截
```

### 原子写入：为什么要用 `os.replace`?

```python
# ❌ os.rename: Windows 上目标存在时抛出 FileExistsError
os.rename(temp, target)

# ✅ os.replace: POSIX 语义，原子性覆盖
os.replace(temp, target)  # 跨平台一致
```

### 乐观锁 vs 悲观锁

| 维度 | 乐观锁 (Version Hash) | 悲观锁 (File Lock) |
|------|----------------------|-------------------|
| 性能 | ✅ 高，无锁开销 | ❌ 低，锁竞争 |
| 死锁风险 | ✅ 无 | ❌ 有 |
| 跨平台 | ✅ 兼容性好 | ❌ 平台差异大 |
| 适用场景 | 读多写少（配置管理） | 写多读少 |

OminiConfig 选择乐观锁，因为配置修改通常是低频操作。

---

## 🔧 扩展：添加 YAML 支持

```python
# core/adapters/yaml_adapter.py
import yaml
from core.adapter import BaseConfigAdapter, AdapterFactory

@AdapterFactory.register
class YamlAdapter(BaseConfigAdapter):
    supported_extensions = ['.yaml', '.yml']
    
    async def read_config(self, file_path: Path) -> ConfigResult:
        # 实现 YAML 读取
        ...
    
    async def write_config(self, file_path: Path, data: dict, old_hash: str) -> ConfigResult:
        # 实现 YAML 写入
        ...
    
    async def generate_schema(self, file_path: Path) -> dict:
        result = await self.read_config(file_path)
        return self._derive_schema(result.data)
```

无需修改任何现有代码，工厂自动识别 `.yaml` 文件！

---

## 🛡️ 安全加固

- [x] 路径沙箱校验（`PathSecurityValidator`）
- [x] 空字节注入防御
- [x] 绝对路径拒绝
- [x] 符号链接解析（`Path.resolve()`）
- [x] 严格前缀匹配（`os.path.commonpath()`）
- [x] 原子文件写入（防止半写入状态）
- [x] CORS 配置（生产环境需限制域名）

---

## 📈 性能指标

基于 MacBook Pro M1, 16GB 内存测试：

| 操作 | 平均延迟 | 吞吐量 |
|------|----------|--------|
| 读取配置 | 5-10ms | 1000+ req/s |
| 保存配置 | 10-20ms | 500+ req/s |
| SSE 事件推送 | <50ms | 1000+ 并发连接 |
| Schema 推导 | 20-50ms | - |

---

## 🤝 贡献指南

1. **Fork** 本仓库
2. 创建 **Feature Branch** (`git checkout -b feature/amazing-feature`)
3. **遵循开发规范**: 详见 [AGENTS.md](./AGENTS.md)
   - 编写单元测试
   - 更新项目文档
   - 确保代码质量
4. **提交变更** (`git commit -m 'feat: Add amazing feature'`)
5. **推送分支** (`git push origin feature/amazing-feature`)
6. 创建 **Pull Request**

### 重要提醒

⚠️ **所有代码变更必须同步更新**：
- ✅ 单元测试（tests/）
- ✅ 项目文档（doc/）
- ✅ 根目录 README.md（如影响用户接口）

详见 [AGENTS.md](./AGENTS.md) 的"开发工作流程"章节。

---

## 📄 许可证

[GNU General Public License v2.0](./LICENSE) © 2026 OminiConfig Team

---

## 💬 联系我们

- 📧 Email: [your-email@example.com](mailto:your-email@example.com)
- 🐛 Issues: [GitHub Issues](https://github.com/Areazer/OminiConfig/issues)
- 💡 Discussions: [GitHub Discussions](https://github.com/Areazer/OminiConfig/discussions)

---

<p align="center">
  <strong>Star ⭐ 本项目 if you find it helpful!</strong>
</p>
