# 快速开始指南

**文档类型**: 开发指南  
**适用范围**: v2.0+ (Rust + Tauri)  
**最后更新**: 2026-03-21  
**维护者**: OminiConfig Team

## 文档用途

本文档帮助新用户在 5 分钟内快速上手 OminiConfig **V2.0 Native Desktop** 版本。

⚠️ **注意**: 本文档适用于 **V2.0 Rust + Tauri** 版本。如果你在使用旧的 V1.x Python 版本，请参考历史文档。

---

## 🎯 5 分钟快速开始

### 第 1 步：安装 Rust 环境（1 分钟）

如果你还没有 Rust 环境：

```bash
# 安装 Rust (使用 rustup)
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source $HOME/.cargo/env

# 验证安装
rustc --version  # 应显示 1.70+
cargo --version
```

**环境要求**:
- Rust 1.70+ (Edition 2021)
- 支持平台: macOS 10.13+, Windows 10+, Linux (glibc 2.31+)

### 第 2 步：克隆并运行（2 分钟）

```bash
# 克隆仓库
git clone https://github.com/Areazer/OminiConfig.git
cd OminiConfig

# 进入 Tauri 项目目录
cd src-tauri

# 编译并运行（开发模式）
cargo tauri dev
```

首次编译可能需要 2-5 分钟（依赖下载和编译）。

启动成功后你会看到：

```
    Running `target/debug/omini-config`
============================================================
🚀 OminiConfig V2.0 Native Desktop 启动中...
============================================================
📁 工作目录: /path/to/OminiConfig/configs
🖥️  GUI 界面: 桌面窗口已打开
📦 应用体积: <5MB
============================================================
```

### 第 3 步：使用 GUI 管理配置（2 分钟）

应用启动后会自动打开桌面窗口：

```
┌─────────────────────────────────────────────────────┐
│  🔧 OminiConfig V2.0        🟢 监听中      [保存]   │
├─────────────────────────────────────────────────────┤
│  版本哈希: abc123...    最后修改: 2026-03-21 10:30   │
├─────────────────────────────────────────────────────┤
│  配置编辑                                            │
│  ├─ 🔵 debug: [true ▼]                             │
│  ├─ 🟢 port: [8080    ]                            │
│  └─ 🟣 database: [object]                          │
│       ├─ 🔵 host: [localhost    ]                  │
│       └─ 🟢 port: [5432    ]                       │
└─────────────────────────────────────────────────────┘
```

#### 基础操作

1. **编辑配置**
   - 点击任意字段即可编辑
   - 支持类型：字符串、数字、布尔值、对象、数组
   - 对象和数组会自动展开显示子字段

2. **保存配置**
   - 点击右上角绿色"保存"按钮
   - 系统自动携带 versionHash 防止冲突
   - 保存成功后会显示绿色提示

3. **实时监听**
   - 顶部状态栏显示"监听中"
   - 外部程序修改配置时会弹出 Toast 提示
   - 点击"刷新"加载最新配置

---

## 📦 打包生产版本

### 打包命令

```bash
cd src-tauri

# 编译生产版本（优化体积）
cargo tauri build
```

输出位置：
- **macOS**: `target/release/bundle/macos/OminiConfig.app`
  - 双击运行，或拖入 Applications
- **Windows**: `target/release/bundle/msi/OminiConfig_2.0.0_x64.msi`
  - 双击安装
- **Linux**: `target/release/bundle/deb/omini-config_2.0.0_amd64.deb`
  - `sudo dpkg -i *.deb`

### 验证打包结果

```bash
# macOS
ls -lh target/release/bundle/macos/OminiConfig.app/Contents/MacOS/omini-config
# 应显示 < 5MB

# Windows
dir target\release\bundle\msi\
# OminiConfig_2.0.0_x64.msi 约 3-4MB
```

---

## 🔧 开发模式说明

### 热重载 (Hot Reload)

开发模式下支持热重载：

- **Rust 代码**: 修改后自动重新编译
- **前端代码**: 修改 `static/index.html` 后自动刷新

### 调试工具

**Rust 调试**:
```bash
# 添加日志
cargo tauri dev --features debug

# 运行测试
cargo test
```

**前端调试**:
- 右键 -> 检查元素（Chrome DevTools）
- 控制台查看 `window.__TAURI__` 对象

---

## 📂 配置工作目录

默认工作目录是 `./configs`，所有配置文件都存储在这里。

### 自定义工作目录

```bash
# 启动前设置环境变量
export OMINI_WORKSPACE=/path/to/your/configs
cargo tauri dev
```

或在代码中修改 `src-tauri/src/utils.rs`:

```rust
pub fn workspace_dir() -> PathBuf {
    std::env::current_dir()
        .unwrap_or_else(|_| PathBuf::from("."))
        .join("your-workspace-name")  // 修改这里
}
```

---

## 🐛 常见问题

### Q: 编译时间太长？

**A**: 首次编译需要下载依赖，通常 2-5 分钟。后续编译会使用缓存，几秒钟完成。

```bash
# 使用 release 模式编译（更快运行，但编译稍慢）
cargo tauri build
```

### Q: 如何更新 Rust 版本？

```bash
rustup update
```

### Q: 打包后的应用如何分发？

**A**: 直接分发打包后的文件：
- macOS: `.app` 文件（可压缩为 zip）
- Windows: `.msi` 安装包
- Linux: `.deb` 包

用户无需安装 Rust 或任何依赖，**双击即用**！

### Q: V1.x Python 版本还能用吗？

**A**: 可以，查看 Git 历史标签：

```bash
# 检出 V1.x 版本
git checkout v1.0.0
pip install -r requirements.txt
python main.py
```

---

## 📚 下一步

- 阅读 [架构设计文档](../architecture/v2_enterprise.md) 了解 Rust 实现细节
- 查看 [API 文档](../api/README.md) 了解 IPC 接口
- 参考 [Agent 集成指南](./agent_integration.md) 了解 Tauri IPC 协议

---

## 💡 提示

- **无需 Node.js**: V2.0 使用 Vue 3 CDN 版本，零 Node 依赖
- **无需 Python**: 完全抛弃 Python 运行时
- **原生性能**: Rust + Tauri = 极致轻量和速度

---

**遇到问题？** 查看 [FAQ](./faq.md) 或在 [GitHub Issues](https://github.com/Areazer/OminiConfig/issues) 提问。
