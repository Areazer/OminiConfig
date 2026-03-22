# 🖥️ OminiConfig V2.0 (Native Desktop)

> 一款通用编辑配置文件的**原生桌面应用**。采用 Rust + Tauri 构建，轻量化设计，专注于本地配置文件管理。

OminiConfig V2.0 是从 Web 服务到原生应用的迁移版本，采用 **Rust + Tauri** 构建。

---

## ✨ 核心特性

- **原生性能**: Rust 二进制，毫秒级启动，相比 Python 版本更低的运行时负担，基于 notify 的文件监听。
- **基础安全**: 基于 `Path::components()` 的路径校验，拦截绝对路径和路径穿越。
- **实时更新**: Tauri IPC 事件推送，500ms 防抖聚合，UI 冲突提示。
- **表单渲染**: 基于示例数据推导简化表单结构，支持深色模式树形编辑。

---

## 🚀 快速开始

### 环境要求

- **Rust**: 1.70+ (Edition 2021)

### 安装与启动

```bash
# 克隆仓库
git clone https://github.com/Areazer/OminiConfig.git
cd OminiConfig

# 进入 Tauri 项目目录
cd src-tauri

# 编译并运行（开发模式）
cargo tauri dev

# 或编译生产版本
cargo tauri build
```

生产版本将打包到 `src-tauri/target/release/bundle/`。

---

## 🏗️ 架构说明

### 从 V1.1 (Python/FastAPI) 到 V2.0 (Rust/Tauri)

| 特性 | V1.1 (Python) | V2.0 (Rust) | 说明 |
|------|---------------|-------------|------|
| **启动速度** | 2-3 秒 | 更快 | 原生二进制，无运行时负担 |
| **内存占用** | 较高 | 更低 | 无 Python 运行时 |
| **打包体积** | ~50MB (含 Python) | 更小 | 精简依赖，单一二进制 |
| **通信协议** | HTTP + SSE | Tauri IPC | 原生进程通信 |
| **文件监听** | Python watchdog | Rust notify | 跨平台监听 |

### 核心技术栈

- **Backend**: Rust 1.70+, Tokio, Notify
- **Frontend**: Vue 3 (CDN), Tailwind CSS (CDN), Tauri API
- **IPC**: Tauri Native IPC

---

## 🛡️ 安全说明

### 路径校验

基于 Rust `Path::components()` 的路径组件解析：

```rust
// 校验策略：
// 1. 拒绝 Prefix（Windows 盘符）
// 2. 拒绝 RootDir（绝对路径）
// 3. 拒绝 ParentDir（路径穿越 ..）
// 4. 忽略 CurDir（当前目录 .）
// 5. 只允许 Normal（普通路径组件）
// 6. 边界检查：确保在 workspace 范围内
```

### 写入策略

基于临时文件和原子重命名的写入：

```rust
// 1. 写入临时文件
// 2. 强制刷盘 (sync_all)
// 3. 原子重命名覆盖
```

### 版本控制

SHA256 哈希校验，检测到冲突时返回错误码 `CONCURRENCY_CONFLICT`。

### 错误码边界

- **`INVALID_CONFIG_FORMAT`**: 用户配置文件的 JSON 解析失败（如语法错误、无效格式）
- **`SERIALIZATION_ERROR`**: 内部序列化/反序列化失败（通常是系统层面的数据转换错误）

---

## 📂 项目结构

```
src-tauri/
├── Cargo.toml           # Rust 依赖配置
├── tauri.conf.json      # Tauri 打包配置
└── src/
    ├── main.rs          # 应用入口
    ├── commands.rs      # IPC 命令
    ├── utils.rs         # 路径校验、原子写入、SHA256
    └── watcher.rs       # 文件监听、事件分类

static/
└── index.html           # Vue 3 GUI
```

---

## 🎯 IPC 接口

### `read_config(path: String) -> Result<ConfigData, CommandError>`

读取配置文件。

**成功返回**:
```json
{
  "data": { ... },
  "meta": {
    "version_hash": "sha256...",
    "last_modified": 1711000000.0
  }
}
```

**错误码**:
- `PATH_SECURITY_VIOLATION`: 路径不安全
- `CONFIG_NOT_FOUND`: 文件不存在
- `INVALID_CONFIG_FORMAT`: JSON 格式错误（用户配置文件的解析失败）
- `IO_ERROR`: 文件操作失败
- `SERIALIZATION_ERROR`: 内部序列化错误

### `write_config(path, data, old_hash) -> Result<ConfigData, CommandError>`

写入配置，携带 version_hash 进行乐观锁校验。

**错误码**:
- `CONCURRENCY_CONFLICT`: 版本哈希不匹配
  - `details.expected_hash`: 客户端提供的哈希
  - `details.actual_hash`: 服务器当前哈希
- `PATH_SECURITY_VIOLATION`: 路径不安全
- `SERIALIZATION_ERROR`: 数据序列化失败（内部错误）
- `IO_ERROR`: 文件写入失败

### `get_schema(path) -> Result<Value, CommandError>`

基于示例数据推导表单结构（简化版，非完整 JSON Schema）。

### `config_changed` (Event)

监听配置变更事件：

```javascript
listen('config_changed', (event) => {
  const { kind, path, version_hash, data } = event.payload;
  // kind: 'created' | 'modified' | 'removed' | 'renamed'
});
```

---

## ⚠️ 已知限制

1. **路径校验**: 使用 `std::env::current_dir()` 作为 workspace，生产环境建议使用 app data 目录。

2. **表单推导**: 
   - 数组类型只取第一个元素推导 items（简化策略）
   - 不自动推导 required 字段
   - 这是启发式行为，不是严谨的类型约束

3. **文件监听**: 
   - rename 事件（编辑器 temp->target 模式）归类为 `renamed`
   - remove 事件会明确推送，不会静默忽略

---

## 📦 打包发布

### macOS

```bash
cargo tauri build --target universal-apple-darwin
```

### Windows

```bash
cargo tauri build --target x86_64-pc-windows-msvc
```

### Linux

```bash
cargo tauri build --target x86_64-unknown-linux-gnu
```

---

## 📄 许可证

GPL-2.0 © 2026 OminiConfig Team