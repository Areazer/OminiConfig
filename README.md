# OminiConfig

一款通用编辑配置文件的 GUI 组件

轻量级、高性能、支持任意数据源的通用 GUI 配置管理器

## 项目结构

```
OminiConfig/
├── omini_config/          # 核心适配器模块
│   ├── __init__.py       # 模块初始化
│   ├── adapter.py        # JSON 适配器实现
│   └── api.py            # FastAPI HTTP 接口
├── tests/                 # 单元测试
│   ├── __init__.py
│   └── test_adapter.py   # 适配器完整测试套件
├── ARCHITECTURE.md        # 架构文档
├── requirements.txt       # 依赖列表
└── README.md             # 项目说明
```

## 核心特性

### 1. 并发安全
- 采用乐观并发控制（Optimistic Concurrency Control）
- 使用 SHA256 哈希作为版本标识（versionHash）
- 原子文件写入（临时文件 + 重命名）

### 2. 防御性编程
- 文件不存在时自动初始化空配置
- JSON 格式损坏时提供详细的错误堆栈
- 类型不匹配时优雅处理

### 3. 无状态设计
- 适配器实例不持有配置状态
- 每次操作都是独立的
- 轻量级、可复用

### 4. Schema 推导
- 根据配置数据自动推导 JSON Schema
- 支持无限层级嵌套
- 前端可基于 Schema 动态渲染 GUI

## 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 启动 API 服务

```bash
cd omini_config
python api.py
```

服务启动后访问:
- API 文档: http://localhost:8000/docs
- 替代文档: http://localhost:8000/redoc

### 运行测试

```bash
pytest tests/test_adapter.py -v
```

## API 接口

### 读取配置
```http
GET /api/config/{source_path}
```

响应示例:
```json
{
  "data": {
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

### 保存配置
```http
POST /api/config/{source_path}
```

请求体:
```json
{
  "data": {
    "database": {
      "host": "localhost",
      "port": 5432
    }
  },
  "oldVersionHash": "abc123..."
}
```

**注意**: 如果 `oldVersionHash` 与服务器端当前版本的哈希不匹配，将返回 409 冲突错误。

### 获取 Schema
```http
GET /api/schema/{source_path}
```

响应示例:
```json
{
  "schema": {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "properties": {
      "database": {
        "type": "object",
        "properties": {
          "host": {"type": "string"},
          "port": {"type": "number"}
        },
        "required": ["host", "port"]
      }
    }
  }
}
```

## 测试覆盖

测试套件包含以下覆盖:

1. **正常读写流程**: 初始化、读取、写入、更新
2. **嵌套层级测试**: 支持 5 层以上深度嵌套
3. **并发冲突模拟**: 多线程竞争条件下的异常拦截
4. **错误处理**: 格式错误、编码错误、类型不匹配
5. **Schema 推导**: 复杂类型的自动推导
6. **边缘情况**: Unicode、大型结构、递归深度限制

运行测试:
```bash
pytest tests/test_adapter.py -v --tb=short
```

## 异常类型

- `ConfigException`: 基础配置异常
- `ConfigNotFoundException`: 配置文件不存在
- `ConfigFormatException`: 配置文件格式损坏
- `ConcurrencyConflictException`: 并发冲突（versionHash 不匹配）

## 技术栈

- **语言**: Python 3.8+
- **Web 框架**: FastAPI
- **数据验证**: Pydantic
- **测试框架**: pytest

## 许可证
License: GPL-2.0
