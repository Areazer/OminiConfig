# 🖥️ OminiConfig V2.0 (Native Desktop)

> 一款通用编辑配置文件的**原生桌面应用**。采用 Rust + Tauri 构建，轻量化设计，专注于本地配置文件管理。

OminiConfig V2.0 是从 Web 服务到原生应用的迁移版本，采用 **Rust + Tauri** 构建。

---

## 📖 目录

- [首次使用完全指南](#首次使用完全指南) - **新手必读！**
- [核心特性](#-核心特性)
- [安装与启动](#安装与启动)
- [架构说明](#-架构说明)
- [安全说明](#-安全说明)
- [IPC 接口](#-ipc-接口)
- [已知限制](#-已知限制)
- [打包发布](#-打包发布)

---

## 🆕 首次使用完全指南（新手必读）

### 第一步：下载程序

**方式 A：使用预编译版本（推荐）**

1. 下载对应平台的可执行文件：
   - **macOS**: `src-tauri/target/release/omini-config`
   - **Windows**: `src-tauri/target/release/omini-config.exe`
   - **Linux**: `src-tauri/target/release/omini-config`

2. **macOS/Linux 用户**需要先赋予执行权限：
   ```bash
   chmod +x omini-config
   ```

**方式 B：自己编译**
```bash
# 需要安装 Rust
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# 克隆并编译
git clone https://github.com/Areazer/OminiConfig.git
cd OminiConfig/src-tauri
cargo tauri build
```

---

### 第二步：运行程序

**macOS/Linux:**
```bash
# 在终端中运行
./omini-config
```

**Windows:**
双击 `omini-config.exe` 文件

💡 **提示**：首次运行时，系统可能会询问是否允许打开未知来源的应用，请点击"允许"。

---

### 第三步：界面介绍

程序启动后会显示一个窗口，界面分为三个区域：

```
┌─────────────────────────────────────────────────────┐
│  [配置文件路径输入框]  [加载按钮]  [保存按钮]        │  ← 顶部工具栏
├─────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────────────────────┐ │
│  │ 配置路径     │  │ 配置内容编辑区               │ │
│  │              │  │                              │ │
│  │ app/         │  │ • 名称: [__________]        │ │
│  │   config.json│  │ • 端口: [__________]        │ │  ← 主编辑区
│  │              │  │ • 启用: [☑]                 │ │
│  │ [选择文件...]│  │                              │ │
│  └──────────────┘  └──────────────────────────────┘ │
└─────────────────────────────────────────────────────┘
        ↑                       ↑
    左侧导航栏              右侧表单区
```

---

### 第四步：创建第一个配置文件

#### 方法 A：直接输入路径（推荐）

1. **在顶部输入框输入配置文件路径**，例如：
   ```
   app/settings.json
   ```
   或
   ```
   database/config.json
   ```

2. **点击"加载"按钮**或按回车键

3. **如果是新文件**，系统会自动创建一个空的 JSON 对象 `{}`

4. **在右侧表单中编辑**：
   - 点击"添加字段"按钮添加新配置项
   - 或直接编辑现有字段

5. **点击"保存"按钮**保存更改

#### 方法 B：使用文件夹

1. 程序会在**当前目录**自动创建 `configs/` 文件夹

2. 你可以手动在 `configs/` 文件夹中创建 JSON 文件：
   ```bash
   mkdir -p configs/app
   echo '{}' > configs/app/settings.json
   ```

3. 然后在输入框中输入：`app/settings.json`

---

### 第五步：配置示例

让我们创建一个实际可用的配置：

**步骤 1：输入路径**
```
app/config.json
```

**步骤 2：添加以下配置内容**
```json
{
  "app_name": "My Application",
  "version": "1.0.0",
  "debug_mode": false,
  "port": 8080,
  "database": {
    "host": "localhost",
    "port": 5432,
    "name": "mydb"
  }
}
```

**步骤 3：点击保存**

界面会自动将 JSON 渲染为表单：
- `app_name` → 文本输入框
- `debug_mode` → 复选框
- `port` → 数字输入框
- `database` → 可展开的对象

---

### 第六步：实时同步功能

OminiConfig 支持实时监听文件变化：

1. **打开配置文件后**，程序会自动监听该文件
2. **如果用其他编辑器修改了文件**，OminiConfig 会弹出提示：
   ```
   ⚠️ 配置文件已被外部程序修改
   [刷新] [忽略]
   ```
3. **点击"刷新"**加载最新内容
4. **如果你正在编辑时发生冲突**，会显示冲突提示，需要手动解决

---

### 常见问题解答

#### Q1: 首次启动报错"配置文件已被删除"或卡住转圈？

**正常现象**！这是 OminiConfig 的首次启动流程：

1. **程序启动** → 自动创建 `configs/` 目录
2. **加载配置** → 发现配置文件不存在 → 自动创建空配置 `{}`
3. **界面显示** → 显示提示"这是新配置文件，点击保存按钮创建默认配置"

**正确操作流程**：
```
1. 运行 ./omini-config
2. 看到界面显示空配置（{}）
3. 在右侧表单中添加配置项
4. 点击"保存"按钮
5. 完成！配置文件已创建
```

**如果卡住转圈**：
- 等待 3-5 秒，程序正在初始化
- 如果超过 10 秒仍卡住，尝试重启程序
- 确保有写入当前目录的权限

**界面空白或卡死其他原因**：
```bash
# 确保在正确的目录运行
cd OminiConfig/src-tauri/target/release
./omini-config

# 检查权限
chmod +x omini-config
ls -la configs/  # 确认目录创建成功
```

#### Q2: 提示"路径不安全"？

**原因**：使用了绝对路径或包含 `..` 的路径穿越

**正确写法**：
```
✅ app/config.json          ← 相对路径
✅ project/settings.json    ← 子目录
❌ /etc/passwd              ← 绝对路径（被拒绝）
❌ ../config.json           ← 路径穿越（被拒绝）
```

#### Q3: 保存时提示"并发冲突"？

**原因**：文件在你编辑期间被其他程序修改了

**解决方法**：
1. 点击"刷新"查看最新内容
2. 合并你的更改
3. 重新保存

#### Q4: 如何删除配置项？

目前需要直接编辑 JSON：
1. 点击"查看原始 JSON"按钮（如果有）
2. 删除对应字段
3. 保存

#### Q5: 配置文件存放在哪里？

所有配置文件都存放在程序启动目录下的 `configs/` 文件夹中：
```
你的程序目录/
├── omini-config          ← 可执行文件
└── configs/              ← 配置文件目录
    ├── app/
    │   └── settings.json
    └── database/
        └── config.json
```

---

### 故障排除

**问题：程序无法启动**

1. 检查是否有权限：
   ```bash
   chmod +x omini-config
   ```

2. 检查依赖：
   ```bash
   # macOS
   xcode-select --install
   
   # Linux
   sudo apt-get install libwebkit2gtk-4.0-dev
   ```

**问题：保存失败**

1. 检查磁盘空间
2. 检查文件权限
3. 查看错误提示的具体错误码

**问题：界面显示异常**

1. 尝试刷新页面（Cmd/Ctrl + R）
2. 重启程序
3. 清除缓存：`rm -rf configs/.cache`

---

## 🔌 集成到其他项目（开发者指南）

> 想把 OminiConfig 当作配置管理工具集成到你的项目中？这份指南教你一步步操作。

### 适用场景

- **桌面应用**：需要让用户可视化编辑配置文件
- **开发工具**：管理项目配置、环境变量、数据库连接等
- **游戏/工具配置**：让用户自定义参数而不用手动改 JSON
- **团队协作**：统一配置文件格式，降低编辑出错概率

---

### 第一步：确定工作目录

OminiConfig 需要一个**工作目录**来存放所有配置文件。

**推荐方案**：在你的项目根目录创建 `configs/` 文件夹

```
你的项目/
├── src/                    ← 你的源代码
├── package.json           ← 你的项目配置
├── configs/               ← ✅ OminiConfig 工作目录
│   ├── app/
│   │   └── settings.json
│   └── database/
│       └── connection.json
└── omini-config           ← OminiConfig 可执行文件（可以放在这里）
```

---

### 第二步：启动 OminiConfig 指向你的项目

**方式 A：快捷启动脚本（推荐）**

在你的项目根目录创建启动脚本：

**macOS/Linux (`start-config.sh`)：**
```bash
#!/bin/bash
# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 启动 OminiConfig，工作目录设为当前目录
cd "$SCRIPT_DIR" && ./omini-config
```

**Windows (`start-config.bat`)：**
```batch
@echo off
:: 切换到脚本所在目录
cd /d "%~dp0"

:: 启动 OminiConfig
start omini-config.exe
```

**使用：**
```bash
# macOS/Linux
chmod +x start-config.sh
./start-config.sh

# Windows
双击 start-config.bat
```

**方式 B：Makefile 集成**

```makefile
.PHONY: config config-build

# 启动配置编辑器
config:
	./omini-config

# 构建并启动（如果源码有更新）
config-build:
	cd src-tauri && cargo build --release
	cp src-tauri/target/release/omini-config ./omini-config
	./omini-config
```

**使用：**
```bash
make config        # 直接启动
make config-build  # 重新构建后启动
```

**方式 C：Node.js 项目集成**

在你的 `package.json` 中添加：

```json
{
  "scripts": {
    "config": "./omini-config",
    "config:dev": "cd src-tauri && cargo tauri dev",
    "postinstall": "node scripts/download-omini-config.js"
  }
}
```

然后创建 `scripts/download-omini-config.js`：

```javascript
// 自动下载对应平台的 OminiConfig 二进制文件
const fs = require('fs');
const https = require('https');
const path = require('path');

const platform = process.platform;
const binaryName = platform === 'win32' ? 'omini-config.exe' : 'omini-config';
const downloadUrl = `https://github.com/Areazer/OminiConfig/releases/latest/download/${binaryName}`;

if (!fs.existsSync(binaryName)) {
  console.log(`Downloading OminiConfig for ${platform}...`);
  const file = fs.createWriteStream(binaryName);
  https.get(downloadUrl, (response) => {
    response.pipe(file);
    file.on('finish', () => {
      file.close();
      fs.chmodSync(binaryName, 0o755); // 赋予执行权限
      console.log('Download complete!');
    });
  });
}
```

**使用：**
```bash
npm run config      # 启动配置编辑器
npm install         # 自动下载 OminiConfig
```

---

### 第三步：在代码中读取配置

OminiConfig 只是帮你编辑配置文件，**读取配置还是需要你的代码自己实现**。

**Python 项目示例：**

```python
import json
import os

CONFIG_DIR = os.path.join(os.path.dirname(__file__), '..', 'configs')

def load_config(path):
    """加载配置文件"""
    full_path = os.path.join(CONFIG_DIR, path)
    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        # 如果文件不存在，返回默认配置
        return get_default_config(path)
    except json.JSONDecodeError as e:
        print(f"配置格式错误: {e}")
        return None

def get_default_config(path):
    """获取默认配置"""
    defaults = {
        'app/settings.json': {
            'app_name': 'My App',
            'debug': False,
            'port': 8080
        },
        'database/config.json': {
            'host': 'localhost',
            'port': 5432,
            'database': 'myapp'
        }
    }
    return defaults.get(path, {})

# 使用示例
settings = load_config('app/settings.json')
print(f"App name: {settings['app_name']}")
print(f"Port: {settings['port']}")
```

**Node.js 项目示例：**

```javascript
const fs = require('fs');
const path = require('path');

const CONFIG_DIR = path.join(__dirname, '..', 'configs');

function loadConfig(configPath) {
    const fullPath = path.join(CONFIG_DIR, configPath);
    try {
        const data = fs.readFileSync(fullPath, 'utf8');
        return JSON.parse(data);
    } catch (err) {
        if (err.code === 'ENOENT') {
            // 文件不存在，返回默认配置
            return getDefaultConfig(configPath);
        }
        console.error('配置加载失败:', err);
        return null;
    }
}

function getDefaultConfig(configPath) {
    const defaults = {
        'app/settings.json': {
            app_name: 'My App',
            debug: false,
            port: 8080
        }
    };
    return defaults[configPath] || {};
}

// 使用示例
const settings = loadConfig('app/settings.json');
console.log(`App name: ${settings.app_name}`);
```

**Rust 项目示例：**

```rust
use serde::{Deserialize, Serialize};
use std::fs;
use std::path::PathBuf;

#[derive(Debug, Serialize, Deserialize)]
struct AppConfig {
    app_name: String,
    debug: bool,
    port: u16,
}

fn load_config(config_dir: &str, path: &str) -> Result<AppConfig, Box<dyn std::error::Error>> {
    let full_path = PathBuf::from(config_dir).join(path);
    let content = fs::read_to_string(full_path)?;
    let config: AppConfig = serde_json::from_str(&content)?;
    Ok(config)
}

// 使用示例
fn main() {
    let config = load_config("./configs", "app/settings.json")
        .expect("Failed to load config");
    println!("App name: {}", config.app_name);
}
```

---

### 第四步：配置文件约定

为了让 OminiConfig 的表单渲染效果更好，建议遵循以下约定：

**✅ 推荐写法：**

```json
{
  "app_name": "My Application",
  "version": "1.0.0",
  "debug_mode": false,
  "port": 8080,
  "features": {
    "enable_auth": true,
    "max_connections": 100
  },
  "database": {
    "host": "localhost",
    "port": 5432,
    "ssl": false
  }
}
```

**表单渲染效果：**
- ✅ 基础类型（string/boolean/number）会渲染为对应的表单控件
- ✅ 嵌套对象可展开折叠
- ✅ 数组会显示为列表（但只支持简单编辑）

**⚠️ 注意事项：**

1. **避免过深的嵌套**：建议不超过 3 层
2. **数组限制**：数组只取第一个元素推导类型，复杂数组结构可能显示不完美
3. **注释**：JSON 不支持注释，如需说明请使用 `_description` 字段：
   ```json
   {
     "_description": "这是应用主配置",
     "app_name": "My App"
   }
   ```

---

### 第五步：多环境配置管理

**场景**：开发环境、测试环境、生产环境使用不同配置

**推荐方案：**

```
configs/
├── common/
│   └── base.json          ← 通用配置
├── development/
│   └── overrides.json     ← 开发环境覆盖
├── production/
│   └── overrides.json     ← 生产环境覆盖
└── local/
    └── overrides.json     ← 本地覆盖（不提交到 Git）
```

**配置合并逻辑（以 Node.js 为例）：**

```javascript
function loadEnvConfig(environment) {
    const base = loadConfig('common/base.json');
    const override = loadConfig(`${environment}/overrides.json`);
    
    // 深度合并
    return deepMerge(base, override);
}

// 使用
const env = process.env.NODE_ENV || 'development';
const config = loadEnvConfig(env);
```

---

### 完整示例项目结构

```
my-awesome-app/
├── src/                          ← 源代码
│   ├── main.py                  ← 主程序
│   └── config_loader.py         ← 配置加载器
├── configs/                      ← ✅ OminiConfig 工作目录
│   ├── app/
│   │   └── settings.json        ← 应用配置
│   ├── database/
│   │   └── connection.json      ← 数据库配置
│   └── logging/
│       └── config.json          ← 日志配置
├── omini-config                  ← OminiConfig 可执行文件
├── start-config.sh              ← 启动脚本
├── package.json                 ← Node.js 项目配置
├── requirements.txt             ← Python 依赖
└── README.md                    ← 你的项目说明
```

**使用流程：**

1. **开发时**：
   ```bash
   ./start-config.sh              # 启动 OminiConfig 编辑配置
   # 编辑 configs/app/settings.json
   # 保存后关闭
   
   python src/main.py             # 运行你的程序，自动读取最新配置
   ```

2. **部署时**：
   ```bash
   # 配置已保存在 configs/ 目录，随项目一起部署
   # 生产环境可以通过环境变量指定覆盖配置
   NODE_ENV=production npm start
   ```

---

### 文件分发指南（重要！）

**问题**：`target` 目录有 2GB+，难道要全部复制？

**答案**：**不需要！** 你只需要一个 2.3MB 的文件。

#### target 目录结构解析

```
src-tauri/target/
├── release/
│   ├── omini-config          ← ✅ 只需要这个（2.3MB）
│   ├── deps/                 ← ❌ 编译依赖（653MB，不需要）
│   ├── build/                ← ❌ 构建产物（59MB，不需要）
│   ├── bundle/               ← ❌ 安装包（如需要可保留）
│   └── ...                   ← ❌ 其他都是中间文件
└── debug/                    ← ❌ 调试版本（不需要）
```

#### 应该复制哪些文件？

**场景 A：集成到其他项目（推荐）**

复制这 **1 个文件** 即可：
```bash
# 从 OminiConfig 项目
src-tauri/target/release/omini-config       # macOS/Linux（2.3MB）
src-tauri/target/release/omini-config.exe   # Windows（约 2.5MB）
```

**集成步骤**：
```bash
# 1. 复制可执行文件到你的项目
cp /path/to/omini-config ./my-project/omini-config

# 2. 在你的项目创建 configs 目录
mkdir -p ./my-project/configs

# 3. 完成！现在可以运行了
cd ./my-project && ./omini-config
```

**场景 B：创建发布包**

如果需要分发给最终用户，可以打包：
```
my-app-config-tool.zip
├── omini-config              ← 可执行文件
├── configs/                  ← 默认配置目录（可选）
│   └── app/
│       └── default.json      ← 默认配置
├── start-config.sh           ← 启动脚本（macOS/Linux）
├── start-config.bat          ← 启动脚本（Windows）
└── README.txt                ← 使用说明
```

**文件大小对比**：
| 方案 | 大小 | 说明 |
|------|------|------|
| 完整 target 目录 | 2.1 GB | ❌ 包含所有编译中间文件 |
| release 目录 | 720 MB | ❌ 仍包含 deps、build 等 |
| 仅 omini-config | 2.3 MB | ✅ 推荐，单文件即可运行 |
| 完整安装包 | 3-5 MB | ✅ 包含脚本和默认配置 |

#### 常见问题

**Q: 删除 target 目录后还能运行吗？**
```bash
# 可以！omini-config 是独立可执行文件
rm -rf src-tauri/target/      # 删除整个 target 目录
./omini-config                # 仍然可以正常运行
```

**Q: 如何获取其他平台的二进制文件？**
```bash
# 方法 1：从 GitHub Releases 下载
curl -L -o omini-config https://github.com/Areazer/OminiConfig/releases/latest/download/omini-config
chmod +x omini-config

# 方法 2：交叉编译（需要 Rust）
rustup target add x86_64-pc-windows-msvc
cargo build --release --target x86_64-pc-windows-msvc
```

**Q: 可以将 omini-config 放入 PATH 吗？**
```bash
# 可以！这样可以在任何地方使用
sudo cp omini-config /usr/local/bin/
omini-config --help
```

---

### 集成检查清单

在你的项目中集成 OminiConfig 时，确认以下事项：

- [ ] 已创建 `configs/` 工作目录
- [ ] 已将 `omini-config` 可执行文件放入项目目录（**只需这一个 2.3MB 文件**）
- [ ] **已删除或忽略 `target/` 目录**（不需要 2GB+ 的编译文件）
- [ ] 已编写配置加载代码（参考上面的示例）
- [ ] 已添加启动脚本（.sh/.bat/Makefile）
- [ ] 已在 README 中说明如何使用 OminiConfig 编辑配置
- [ ] 已将 `configs/` 添加到 `.gitignore`（如果是本地配置）或纳入版本控制（如果是默认配置）

---

## ✨ 核心特性

- **原生性能**: Rust 二进制，毫秒级启动，相比 Python 版本更低的运行时负担，基于 notify 的文件监听。
- **基础安全**: 基于 `Path::components()` 的路径校验，拦截绝对路径和路径穿越。
- **实时更新**: Tauri IPC 事件推送，500ms 防抖聚合，UI 冲突提示。
- **表单渲染**: 基于示例数据推导简化表单结构，支持深色模式树形编辑。

---

## 安装与启动

### 环境要求

- **Rust**: 1.70+ (Edition 2021) - 仅编译时需要

### 从源码编译

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

### 直接使用（无需编译）

如果不想自己编译，可以直接使用已构建的二进制文件：

**macOS/Linux:**
```bash
# 进入项目目录
cd src-tauri/target/release

# 运行（赋予执行权限后）
chmod +x omini-config
./omini-config
```

**Windows:**
双击运行 `src-tauri\target\release\omini-config.exe`

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